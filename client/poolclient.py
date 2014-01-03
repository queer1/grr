#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.

"""This is the GRR client for thread pools."""


import pickle
import threading
import time


import logging

from grr.client import client

# pylint: disable=unused-import
# Make sure we load the client plugins
from grr.client import client_plugins
# pylint: enable=unused-import

from grr.client import comms
from grr.client import vfs
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import startup

flags.DEFINE_integer("nrclients", 1,
                     "Number of clients to start")

flags.DEFINE_string("cert_file", "",
                    "Path to a file that stores all certificates for"
                    "the client pool.")

flags.DEFINE_bool("enroll_only", False,
                  "If specified, the script will enroll all clients and exit.")


class PoolGRRClient(client.GRRClient, threading.Thread):
  """A GRR client for running in pool mode."""

  def __init__(self, *args, **kw):
    """Constructor."""
    super(PoolGRRClient, self).__init__(*args, **kw)
    self.daemon = True
    self.stop = False

    # Is this client already enrolled?
    self.enrolled = False

    self.common_name = self.client.communicator.common_name
    self.private_key = self.client.communicator.private_key

  def Run(self):
    for status in self.client.Run():
      # if the status is 200 we assume we have successfully enrolled.
      if status.code == 200:
        self.enrolled = True

      # Thread should stop now.
      if self.stop:
        break

  def Stop(self):
    self.stop = True

  def run(self):
    self.Run()


def CreateClientPool(n):
  """Create n clients to run in a pool."""
  clients = []

  # Load previously stored clients.
  try:
    fd = open(flags.FLAGS.cert_file, "rb")
    certificates = pickle.load(fd)
    fd.close()

    for certificate in certificates:
      clients.append(PoolGRRClient(private_key=certificate))

  except (IOError, EOFError):
    pass

  while len(clients) < n:
    # Generate a new RSA key pair for each client.
    key = rdfvalue.PEMPrivateKey.GenKey(bits=comms.ClientCommunicator.BITS)
    clients.append(PoolGRRClient(private_key=key))

  # Start all the clients now.
  for c in clients:
    c.start()

  start_time = time.time()
  try:
    if flags.FLAGS.enroll_only:
      while True:
        time.sleep(1)
        enrolled = len([x for x in clients if x.enrolled])

        if enrolled == n:
          logging.info("All clients enrolled, exiting.")
          break

        else:
          logging.info("%s: Enrolled %d/%d clients.", int(time.time()),
                       enrolled, n)
    else:
      try:
        while True:
          time.sleep(100)
      except KeyboardInterrupt:
        pass

  finally:
    # Stop all pool clients.
    for cl in clients:
      cl.Stop()

  logging.info("Pool done in %s seconds, saving certs.",
               time.time() - start_time)
  try:
    fd = open(flags.FLAGS.cert_file, "wb")
    pickle.dump([x.private_key for x in clients], fd)
    fd.close()
  except IOError:
    pass


def CheckLocation():
  """Checks that the poolclient is not accidentally ran against production."""
  for url in config_lib.CONFIG["Client.control_urls"]:
    if "staging" in url or "localhost" in url:
      # This is ok.
      return
  logging.error("Poolclient should only be run against test or staging.")
  exit()


def main(unused_argv):
  config_lib.CONFIG.AddContext(
      "PoolClient Context",
      "Context applied when we run the pool client.")

  startup.ClientInit()

  config_lib.CONFIG.SetWriteBack("/dev/null")

  CheckLocation()

  # Let the OS handler also handle sleuthkit requests since sleuthkit is not
  # thread safe.
  tsk = rdfvalue.PathSpec.PathType.TSK
  os = rdfvalue.PathSpec.PathType.OS
  vfs.VFS_HANDLERS[tsk] = vfs.VFS_HANDLERS[os]

  CreateClientPool(flags.FLAGS.nrclients)

if __name__ == "__main__":
  flags.StartMain(main)
