#!/usr/bin/env python
"""End to end tests for lib.flows.general.administrative."""

import os


import logging
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import maintenance_utils
from grr.lib.flows.console.client_tests import base


class TestGetClientStats(base.ClientTestBase):
  """GetClientStats test."""
  platforms = ["linux", "windows", "darwin"]

  flow = "GetClientStats"

  def setUp(self):
    super(TestGetClientStats, self).setUp()
    self.stats_urn = self.client_id.Add("stats")
    self.DeleteUrn(self.stats_urn)

    self.assertRaises(AssertionError, self.CheckFlow)

  def CheckFlow(self):
    aff4.FACTORY.Flush()
    client_stats = aff4.FACTORY.Open(self.stats_urn, token=self.token)
    self.assertIsInstance(client_stats, aff4.ClientStats)

    stats = list(client_stats.Get(client_stats.Schema.STATS))
    self.assertGreater(len(stats), 0)
    entry = stats[0]
    self.assertGreater(entry.RSS_size, 0)
    self.assertGreater(entry.VMS_size, 0)
    self.assertGreater(entry.boot_time, 0)
    self.assertGreater(entry.bytes_received, 0)
    self.assertGreater(entry.bytes_sent, 0)
    self.assertGreater(entry.memory_percent, 0)

    self.assertGreater(len(list(entry.cpu_samples)), 0)
    if not list(entry.io_samples):
      logging.warning("No IO samples received. This is ok if the tested"
                      " client is a mac.")


class TestLaunchBinaries(base.ClientTestBase):
  """Test that we can launch a binary.

  The following program is used and will be signed and uploaded before
  executing the test if it hasn't been uploaded already.

  #include <stdio.h>
  int main(int argc, char** argv) {
    printf("Hello world!!!");
    return 0;
  };
  """
  platforms = ["windows", "linux"]
  flow = "LaunchBinary"
  filenames = {"windows": "hello.exe",
               "linux": "hello"}

  def __init__(self, **kwargs):
    super(TestLaunchBinaries, self).__init__(**kwargs)
    self.context = ["Platform:%s" % self.platform.title()]
    self.binary = config_lib.CONFIG.Get(
        "Executables.aff4_path", context=self.context).Add(
            "test/%s" % self.filenames[self.platform])

    self.args = dict(binary=self.binary)

    try:
      aff4.FACTORY.Open(self.binary, aff4_type="GRRSignedBlob",
                        token=self.token)
    except IOError:
      print "Uploading the test binary to the Executables area."
      source = os.path.join(config_lib.CONFIG["Test.data_dir"],
                            self.filenames[self.platform])

      maintenance_utils.UploadSignedConfigBlob(
          open(source, "rb").read(), aff4_path=self.binary,
          client_context=self.context, token=self.token)

  def CheckFlow(self):
    # Check that the test binary returned the correct stdout:
    fd = aff4.FACTORY.Open(self.session_id, age=aff4.ALL_TIMES,
                           token=self.token)
    logs = "\n".join(
        [str(x) for x in fd.GetValuesForAttribute(fd.Schema.LOG)])

    self.assertTrue("Hello world" in logs)



