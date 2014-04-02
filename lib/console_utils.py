#!/usr/bin/env python
"""Utils for use from the console.

Includes functions that are used by interactive console utilities such as
approval or token handling.
"""

import getpass
import os
import time

import logging

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import search
from grr.lib import utils
from grr.lib.flows.general import memory


def FormatISOTime(t):
  """Format a time in epoch notation to ISO UTC."""
  return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(t / 1e6))


def SetLabels(urn, labels, token=None):
  """Set the labels on an object."""
  fd = aff4.FACTORY.Open(urn, mode="rw", token=token)
  current_labels = fd.Get(fd.Schema.LABEL, fd.Schema.LABEL())
  for l in labels:
    current_labels.Append(l)
  fd.Set(current_labels)
  fd.Close()


def SearchClients(query_str, token=None, limit=1000):
  """Search indexes for clients. Returns list (client, hostname, os version)."""
  client_schema = aff4.AFF4Object.classes["VFSGRRClient"].SchemaCls
  results = []
  result_urns = search.SearchClients(query_str, max_results=limit, token=token)
  result_set = aff4.FACTORY.MultiOpen(result_urns, token=token)
  for result in result_set:
    results.append((result,
                    str(result.Get(client_schema.HOSTNAME)),
                    str(result.Get(client_schema.OS_VERSION)),
                    str(result.Get(client_schema.PING)),
                   ))
  return results


def DownloadDir(aff4_path, output_dir, bufsize=8192, preserve_path=True):
  """Take an aff4 path and download all files in it to output_dir.

  Args:
    aff4_path: Any aff4 path as a string
    output_dir: A local directory to write to, will be created if not there.
    bufsize: Buffer size to use.
    preserve_path: If set all paths will be created.

  Note that this works for collections as well. It will download all
  files in the collection.

  This only downloads files that are already in the datastore, it doesn't
  queue anything on the client.
  """
  if not os.path.isdir(output_dir):
    os.makedirs(output_dir)
  fd = aff4.FACTORY.Open(aff4_path)
  for child in fd.OpenChildren():
    if preserve_path:
      # Get a full path without the aff4:
      full_dir = utils.JoinPath(output_dir, child.urn.Path())
      full_dir = os.path.dirname(full_dir)
      if not os.path.isdir(full_dir):
        os.makedirs(full_dir)
      outfile = os.path.join(full_dir, child.urn.Basename())
    else:
      outfile = os.path.join(output_dir, child.urn.Basename())
    logging.info("Downloading %s to %s", child.urn, outfile)
    with open(outfile, "wb") as out_fd:
      try:
        buf = child.Read(bufsize)
        while buf:
          out_fd.write(buf)
          buf = child.Read(bufsize)
      except IOError as e:
        logging.error("Failed to read %s. Err: %s", child.urn, e)


def ListDrivers():
  urn = aff4.ROOT_URN.Add(memory.DRIVER_BASE)
  token = access_control.ACLToken(username="test")
  fd = aff4.FACTORY.Open(urn, mode="r", token=token)

  return list(fd.Query())


def OpenClient(client_id=None):
  """Opens the client, getting potential approval tokens.

  Args:
    client_id: The client id the approval should be revoked for.

  Returns:
    tuple containing (client, token) objects or (None, None) on if
    no appropriate aproval tokens were found.
  """
  token = access_control.ACLToken(username="test")
  try:
    token = ApprovalFind(client_id, token=token)
  except access_control.UnauthorizedAccess as e:
    logging.warn("No authorization found for access to client: %s", e)

  try:
    # Try and open with the token we managed to retrieve or the default.
    client = aff4.FACTORY.Open(rdfvalue.RDFURN(client_id), mode="r",
                               token=token)
    return client, token
  except access_control.UnauthorizedAccess:
    logging.warning("Unable to find a valid reason for client %s. You may need "
                    "to request approval.", client_id)
    return None, None


def GetNotifications(user=None, token=None):
  """Show pending notifications for a user."""
  if not user:
    user = getpass.getuser()
  user_obj = aff4.FACTORY.Open(aff4.ROOT_URN.Add("users").Add(user),
                               token=token)
  return list(user_obj.Get(user_obj.Schema.PENDING_NOTIFICATIONS))


def ApprovalRequest(client_id, reason, approvers, token=None):
  """Request approval to access a host."""
  return flow.GRRFlow.StartFlow(client_id=client_id,
                                flow_name="RequestClientApprovalFlow",
                                reason=reason, approver=approvers, token=token)


def ApprovalGrant(token=None):
  """Iterate through requested access approving or not."""
  user = getpass.getuser()
  notifications = GetNotifications(user=user, token=token)
  requests = [n for n in notifications if n.type == "GrantAccess"]
  for request in requests:
    _, client_id, user, reason = rdfvalue.RDFURN(request.subject).Split()
    reason = utils.DecodeReasonString(reason)
    print request
    print "Reason: %s" % reason
    if raw_input("Do you approve this request? [y/N] ").lower() == "y":
      flow_id = flow.GRRFlow.StartFlow(client_id=client_id,
                                       flow_name="GrantClientApprovalFlow",
                                       reason=reason, delegate=user,
                                       token=token)
      # TODO(user): Remove the notification.
    else:
      print "skipping request"
    print "Approval sent: %s" % flow_id


def ApprovalFind(object_id, token=None):
  """Find approvals issued for a specific client."""
  user = getpass.getuser()
  object_id = rdfvalue.RDFURN(object_id)
  try:
    approved_token = aff4.Approval.GetApprovalForObject(
        object_id, token=token, username=user)
    print "Found token %s" % str(approved_token)
    return approved_token
  except access_control.UnauthorizedAccess:
    print "No token available for access to %s" % object_id


def ApprovalCreateRaw(client_id, reason="", expire_in=60*60*24*7,
                      token=None, approval_type="ClientApproval"):
  """Creates an approval with raw access.

  This method doesn't work through the Gatekeeper for obvious reasons. To use
  it, the console has to use raw datastore access.

  Args:
    client_id: The client id the approval should be created for.
    reason: The reason to put in the token.
    expire_in: Expiry in seconds to use in the token.
    token: The token that will be used. If this is specified reason and expiry
        are ignored.
    approval_type: The type of the approval to create.

  Returns:
    The token.

  Raises:
    RuntimeError: On bad token.
  """
  client_id = rdfvalue.ClientURN(client_id)

  if not token:
    expiry = time.time() + expire_in
    token = rdfvalue.ACLToken(reason=reason, expiry=expiry)

  if not token.reason:
    raise RuntimeError("Cannot create approval with empty reason")
  if not token.username:
    token.username = getpass.getuser()
  approval_urn = flow.GRRFlow.RequestApprovalWithReasonFlow.ApprovalUrnBuilder(
      client_id.Path(), token.username, token.reason)
  super_token = access_control.ACLToken(username="test")
  super_token.supervisor = True

  approval_request = aff4.FACTORY.Create(approval_urn, approval_type,
                                         mode="rw", token=super_token)

  # Add approvals indicating they were approved by fake "raw" mode users.
  approval_request.AddAttribute(
      approval_request.Schema.APPROVER("%s1-raw" % token.username))
  approval_request.AddAttribute(
      approval_request.Schema.APPROVER("%s-raw2" % token.username))
  approval_request.Close(sync=True)


def ApprovalRevokeRaw(client_id, token, remove_from_cache=False):
  """Revokes an approval for a given token.

  This method doesn't work through the Gatekeeper for obvious reasons. To use
  it, the console has to use raw datastore access.

  Args:
    client_id: The client id the approval should be revoked for.
    token: The token that should be revoked.
    remove_from_cache: If True, also remove the approval from the
                       security_manager cache.
  """
  client_id = rdfvalue.ClientURN(client_id)
  approval_urn = aff4.ROOT_URN.Add("ACL").Add(client_id.Path()).Add(
      token.username).Add(utils.EncodeReasonString(token.reason))

  super_token = access_control.ACLToken(username="test")
  super_token.supervisor = True

  approval_request = aff4.FACTORY.Open(approval_urn, mode="rw",
                                       token=super_token)
  approval_request.DeleteAttribute(approval_request.Schema.APPROVER)
  approval_request.Close()

  if remove_from_cache:
    data_store.DB.security_manager.acl_cache.ExpireObject(
        utils.SmartUnicode(approval_urn))
