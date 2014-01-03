#!/usr/bin/env python
"""Tests for export converters."""



import os
import socket

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import export
from grr.lib import flags
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib


class DummyRDFValue(rdfvalue.RDFString):
  pass


class DummyRDFValue2(rdfvalue.RDFString):
  pass


class DummyRDFValue3(rdfvalue.RDFString):
  pass


class DummyRDFValue4(rdfvalue.RDFString):
  pass


class DummyRDFValueConverter(export.ExportConverter):
  input_rdf_type = "DummyRDFValue"

  def Convert(self, metadata, value, token=None):
    _ = metadata
    _ = token
    return [rdfvalue.RDFString(str(value))]


class DummyRDFValue3ConverterA(export.ExportConverter):
  input_rdf_type = "DummyRDFValue3"

  def Convert(self, metadata, value, token=None):
    _ = metadata
    _ = token
    return [rdfvalue.DummyRDFValue(str(value) + "A")]


class DummyRDFValue3ConverterB(export.ExportConverter):
  input_rdf_type = "DummyRDFValue3"

  def Convert(self, metadata, value, token=None):
    _ = metadata
    _ = token
    return [rdfvalue.DummyRDFValue2(str(value) + "B")]


class DummyRDFValue4ToMetadataConverter(export.ExportConverter):
  input_rdf_type = "DummyRDFValue4"

  def Convert(self, metadata, value, token=None):
    _ = value
    _ = token
    return [metadata]


class ExportTest(test_lib.GRRBaseTest):
  """Tests export converters."""

  def testConverterIsCorrectlyFound(self):
    dummy_value = DummyRDFValue("result")
    result = list(export.ConvertValues(rdfvalue.ExportedMetadata(),
                                       [dummy_value]))
    self.assertEqual(len(result), 1)
    self.assertTrue(isinstance(result[0], rdfvalue.RDFString))
    self.assertEqual(result[0], "result")

  def testRaisesWhenNoConverterFound(self):
    dummy_value = DummyRDFValue2("some")
    result_gen = export.ConvertValues(rdfvalue.ExportedMetadata(),
                                      [dummy_value])
    self.assertRaises(export.NoConverterFound, list, result_gen)

  def testConvertsSingleValueWithMultipleAssociatedConverters(self):
    dummy_value = DummyRDFValue3("some")
    result = list(export.ConvertValues(rdfvalue.ExportedMetadata(),
                                       [dummy_value]))
    self.assertEqual(len(result), 2)
    self.assertTrue((isinstance(result[0], rdfvalue.DummyRDFValue) and
                     isinstance(result[1], rdfvalue.DummyRDFValue2)) or
                    (isinstance(result[0], rdfvalue.DummyRDFValue2) and
                     isinstance(result[1], rdfvalue.DummyRDFValue)))
    self.assertTrue((result[0] == rdfvalue.DummyRDFValue("someA") and
                     result[1] == rdfvalue.DummyRDFValue2("someB")) or
                    (result[0] == rdfvalue.DummyRDFValue2("someB") and
                     result[1] == rdfvalue.DummyRDFValue("someA")))

  def testConvertsHuntCollectionWithValuesWithSingleConverter(self):
    fd = aff4.FACTORY.Create("aff4:/testcoll", "RDFValueCollection",
                             token=self.token)

    msg = rdfvalue.GrrMessage(payload=DummyRDFValue("some"))
    msg.source = rdfvalue.ClientURN("C.0000000000000000")
    fd.Add(msg)
    test_lib.ClientFixture(msg.source, token=self.token)

    msg = rdfvalue.GrrMessage(payload=DummyRDFValue("some2"))
    msg.source = rdfvalue.ClientURN("C.0000000000000001")
    fd.Add(msg)
    test_lib.ClientFixture(msg.source, token=self.token)

    fd.Close()

    fd = aff4.FACTORY.Open("aff4:/testcoll", aff4_type="RDFValueCollection",
                           token=self.token)

    results = export.ConvertValues(rdfvalue.ExportedMetadata(), [fd],
                                   token=self.token)
    results = sorted(str(v) for v in results)

    self.assertEqual(len(results), 2)
    self.assertEqual(results[0], "some")
    self.assertEqual(results[1], "some2")

  def testConvertsHuntCollectionWithValuesWithMultipleConverters(self):
    fd = aff4.FACTORY.Create("aff4:/testcoll", "RDFValueCollection",
                             token=self.token)

    msg = rdfvalue.GrrMessage(payload=DummyRDFValue3("some1"))
    msg.source = rdfvalue.ClientURN("C.0000000000000000")
    fd.Add(msg)
    test_lib.ClientFixture(msg.source, token=self.token)

    msg = rdfvalue.GrrMessage(payload=DummyRDFValue3("some2"))
    msg.source = rdfvalue.ClientURN("C.0000000000000001")
    fd.Add(msg)
    test_lib.ClientFixture(msg.source, token=self.token)

    fd.Close()

    fd = aff4.FACTORY.Open("aff4:/testcoll", aff4_type="RDFValueCollection",
                           token=self.token)

    results = export.ConvertValues(rdfvalue.ExportedMetadata(), [fd],
                                   token=self.token)
    results = sorted(results, key=str)

    self.assertEqual(len(results), 4)
    self.assertEqual([str(v) for v in results
                      if isinstance(v, rdfvalue.DummyRDFValue)],
                     ["some1A", "some2A"])
    self.assertEqual([str(v) for v in results
                      if isinstance(v, rdfvalue.DummyRDFValue2)],
                     ["some1B", "some2B"])

  def testStatEntryToExportedFileConverterWithMissingAFF4File(self):
    stat = rdfvalue.StatEntry(
        aff4path=rdfvalue.RDFURN("aff4:/C.00000000000000/fs/os/some/path"),
        pathspec=rdfvalue.PathSpec(path="/some/path",
                                   pathtype=rdfvalue.PathSpec.PathType.OS),
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892)

    converter = export.StatEntryToExportedFileConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), stat,
                                     token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].basename, "path")
    self.assertEqual(results[0].urn,
                     rdfvalue.RDFURN("aff4:/C.00000000000000/fs/os/some/path"))
    self.assertEqual(results[0].st_mode, 33184)
    self.assertEqual(results[0].st_ino, 1063090)
    self.assertEqual(results[0].st_atime, 1336469177)
    self.assertEqual(results[0].st_mtime, 1336129892)
    self.assertEqual(results[0].st_ctime, 1336129892)

    self.assertFalse(results[0].HasField("content"))
    self.assertFalse(results[0].HasField("content_sha256"))
    self.assertFalse(results[0].HasField("hash_md5"))
    self.assertFalse(results[0].HasField("hash_sha1"))
    self.assertFalse(results[0].HasField("hash_sha256"))

  def testStatEntryToExportedFileConverterWithFetchedAFF4File(self):
    client_ids = self.SetupClients(1)
    client_id = client_ids[0]

    pathspec = rdfvalue.PathSpec(
        pathtype=rdfvalue.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "winexec_img.dd"))
    pathspec.Append(path="/Ext2IFS_1_10b.exe",
                    pathtype=rdfvalue.PathSpec.PathType.TSK)

    client_mock = test_lib.ActionMock("TransferBuffer", "StatFile",
                                      "HashBuffer")
    for _ in test_lib.TestFlowHelper(
        "GetFile", client_mock, token=self.token,
        client_id=client_id, pathspec=pathspec):
      pass

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec, client_id)
    fd = aff4.FACTORY.Open(urn, token=self.token)

    stat = fd.Get(fd.Schema.STAT)
    self.assertTrue(stat)

    converter = export.StatEntryToExportedFileConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), stat,
                                     token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].basename, "Ext2IFS_1_10b.exe")
    self.assertEqual(results[0].urn, urn)

    # Check that by default file contents are not exported
    self.assertFalse(results[0].content)
    self.assertFalse(results[0].content_sha256)

    # Convert again, now specifying export_files_contents=True in options.
    converter = export.StatEntryToExportedFileConverter(
        options=rdfvalue.ExportOptions(
            export_files_contents=True))
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), stat,
                                     token=self.token))
    self.assertTrue(results[0].content)
    self.assertEqual(
        results[0].content_sha256,
        "69264282ca1a3d4e7f9b1f43720f719a4ea47964f0bfd1b2ba88424f1c61395d")

  def testStatEntryToExportedFileConverterWithHashedAFF4File(self):
    client_ids = self.SetupClients(1)
    client_id = client_ids[0]

    pathspec = rdfvalue.PathSpec(
        pathtype=rdfvalue.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "winexec_img.dd"))
    pathspec.Append(path="/Ext2IFS_1_10b.exe",
                    pathtype=rdfvalue.PathSpec.PathType.TSK)
    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec, client_id)

    client_mock = test_lib.ActionMock("TransferBuffer", "StatFile",
                                      "HashBuffer")
    for _ in test_lib.TestFlowHelper(
        "GetFile", client_mock, token=self.token,
        client_id=client_id, pathspec=pathspec):
      pass

    auth_state = rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED
    flow.Events.PublishEvent(
        "FileStore.AddFileToStore",
        rdfvalue.GrrMessage(payload=urn, auth_state=auth_state),
        token=self.token)
    worker = test_lib.MockWorker(token=self.token)
    worker.Simulate()

    fd = aff4.FACTORY.Open(urn, token=self.token)
    hash_value = fd.Get(fd.Schema.HASH)
    self.assertTrue(hash_value)

    converter = export.StatEntryToExportedFileConverter(
        options=rdfvalue.ExportOptions(export_files_hashes=True))
    results = list(converter.Convert(rdfvalue.ExportedMetadata(),
                                     rdfvalue.StatEntry(aff4path=urn,
                                                        pathspec=pathspec),
                                     token=self.token))

    self.assertEqual(results[0].hash_md5,
                     "bb0a15eefe63fd41f8dc9dee01c5cf9a")
    self.assertEqual(results[0].hash_sha1,
                     "7dd6bee591dfcb6d75eb705405302c3eab65e21a")
    self.assertEqual(
        results[0].hash_sha256,
        "0e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4f06017acdb5")

  def testStatEntryToExportedRegistryKeyConverter(self):
    stat = rdfvalue.StatEntry(
        aff4path=rdfvalue.RDFURN(
            "aff4:/C.0000000000000000/registry/HKEY_USERS/S-1-5-20/Software/"
            "Microsoft/Windows/CurrentVersion/Run/Sidebar"),
        st_mode=32768,
        st_size=51,
        st_mtime=1247546054,
        registry_type=rdfvalue.StatEntry.RegistryType.REG_EXPAND_SZ,
        pathspec=rdfvalue.PathSpec(
            path="/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
            "CurrentVersion/Run/Sidebar",
            pathtype=rdfvalue.PathSpec.PathType.REGISTRY),
        registry_data=rdfvalue.DataBlob(string="Sidebar.exe"))

    converter = export.StatEntryToExportedRegistryKeyConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), stat,
                                     token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].urn, rdfvalue.RDFURN(
        "aff4:/C.0000000000000000/registry/HKEY_USERS/S-1-5-20/Software/"
        "Microsoft/Windows/CurrentVersion/Run/Sidebar"))
    self.assertEqual(results[0].last_modified,
                     rdfvalue.RDFDatetimeSeconds(1247546054))
    self.assertEqual(results[0].type,
                     rdfvalue.StatEntry.RegistryType.REG_EXPAND_SZ)
    self.assertEqual(results[0].data, "Sidebar.exe")

  def testProcessToExportedProcessConverter(self):
    process = rdfvalue.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=long(1333718907.167083 * 1e6))

    converter = export.ProcessToExportedProcessConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), process,
                                     token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].pid, 2)
    self.assertEqual(results[0].ppid, 1)
    self.assertEqual(results[0].cmdline, "cmd.exe")
    self.assertEqual(results[0].exe, "c:\\windows\\cmd.exe")
    self.assertEqual(results[0].ctime, long(1333718907.167083 * 1e6))

  def testProcessToExportedOpenFileConverter(self):
    process = rdfvalue.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=long(1333718907.167083 * 1e6),
        open_files=["/some/a", "/some/b"])

    converter = export.ProcessToExportedOpenFileConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), process,
                                     token=self.token))

    self.assertEqual(len(results), 2)
    self.assertEqual(results[0].pid, 2)
    self.assertEqual(results[0].path, "/some/a")
    self.assertEqual(results[1].pid, 2)
    self.assertEqual(results[1].path, "/some/b")

  def testProcessToExportedNetworkConnection(self):
    conn1 = rdfvalue.NetworkConnection(
        state=rdfvalue.NetworkConnection.State.LISTEN,
        type=rdfvalue.NetworkConnection.Type.SOCK_STREAM,
        local_address=rdfvalue.NetworkEndpoint(
            ip="0.0.0.0",
            port=22),
        remote_address=rdfvalue.NetworkEndpoint(
            ip="0.0.0.0",
            port=0),
        pid=2136,
        ctime=0)
    conn2 = rdfvalue.NetworkConnection(
        state=rdfvalue.NetworkConnection.State.LISTEN,
        type=rdfvalue.NetworkConnection.Type.SOCK_STREAM,
        local_address=rdfvalue.NetworkEndpoint(
            ip="192.168.1.1",
            port=31337),
        remote_address=rdfvalue.NetworkEndpoint(
            ip="1.2.3.4",
            port=6667),
        pid=1,
        ctime=0)

    process = rdfvalue.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=long(1333718907.167083 * 1e6),
        connections=[conn1, conn2])

    converter = export.ProcessToExportedNetworkConnectionConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), process,
                                     token=self.token))

    self.assertEqual(len(results), 2)
    self.assertEqual(results[0].state, rdfvalue.NetworkConnection.State.LISTEN)
    self.assertEqual(results[0].type,
                     rdfvalue.NetworkConnection.Type.SOCK_STREAM)
    self.assertEqual(results[0].local_address.ip, "0.0.0.0")
    self.assertEqual(results[0].local_address.port, 22)
    self.assertEqual(results[0].remote_address.ip, "0.0.0.0")
    self.assertEqual(results[0].remote_address.port, 0)
    self.assertEqual(results[0].pid, 2136)
    self.assertEqual(results[0].ctime, 0)

    self.assertEqual(results[1].state, rdfvalue.NetworkConnection.State.LISTEN)
    self.assertEqual(results[1].type,
                     rdfvalue.NetworkConnection.Type.SOCK_STREAM)
    self.assertEqual(results[1].local_address.ip, "192.168.1.1")
    self.assertEqual(results[1].local_address.port, 31337)
    self.assertEqual(results[1].remote_address.ip, "1.2.3.4")
    self.assertEqual(results[1].remote_address.port, 6667)
    self.assertEqual(results[1].pid, 1)
    self.assertEqual(results[1].ctime, 0)

  def testVolatilityResultToExportedVolatilityHandleConverter(self):
    volatility_values_1 = rdfvalue.VolatilityValues(values=[
        rdfvalue.VolatilityValue(value=275427776305632),
        rdfvalue.VolatilityValue(value=4),
        rdfvalue.VolatilityValue(value=4),
        rdfvalue.VolatilityValue(value=2097151),
        rdfvalue.VolatilityValue(svalue="Process"),
        rdfvalue.VolatilityValue(svalue="System(4)"),
        rdfvalue.VolatilityValue()])
    volatility_values_2 = rdfvalue.VolatilityValues(values=[
        rdfvalue.VolatilityValue(value=273366078738336),
        rdfvalue.VolatilityValue(value=4),
        rdfvalue.VolatilityValue(value=8),
        rdfvalue.VolatilityValue(value=131103),
        rdfvalue.VolatilityValue(svalue="Key"),
        rdfvalue.VolatilityValue(
            svalue="MACHINE\\SYSTEM\\CONTROLSET001\\CONTROL\\HIVELIST")])

    volatility_table = rdfvalue.VolatilityTable(
        headers=[rdfvalue.VolatilityHeader(name="offset_v"),
                 rdfvalue.VolatilityHeader(name="pid"),
                 rdfvalue.VolatilityHeader(name="handle"),
                 rdfvalue.VolatilityHeader(name="access"),
                 rdfvalue.VolatilityHeader(name="obj_type"),
                 rdfvalue.VolatilityHeader(name="details")],
        rows=[volatility_values_1,
              volatility_values_2])
    volatility_result = rdfvalue.VolatilityResult(
        plugin="mutantscan",
        sections=[rdfvalue.VolatilitySection(table=volatility_table)])

    converter = export.VolatilityResultToExportedVolatilityHandleConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(),
                                     volatility_result,
                                     token=self.token))

    self.assertEqual(len(results), 2)
    self.assertEqual(results[0].offset, 275427776305632)
    self.assertEqual(results[0].pid, 4)
    self.assertEqual(results[0].handle, 4)
    self.assertEqual(results[0].access, 2097151)
    self.assertEqual(results[0].type, "Process")
    self.assertEqual(results[0].path, "System(4)")

    self.assertEqual(results[1].offset, 273366078738336)
    self.assertEqual(results[1].pid, 4)
    self.assertEqual(results[1].handle, 8)
    self.assertEqual(results[1].access, 131103)
    self.assertEqual(results[1].type, "Key")
    self.assertEqual(results[1].path,
                     "MACHINE\\SYSTEM\\CONTROLSET001\\CONTROL\\HIVELIST")

  def testVolatilityResultToExportedVolatilityMutantConverter(self):
    volatility_values_1 = rdfvalue.VolatilityValues(values=[
        rdfvalue.VolatilityValue(value=50211728),
        rdfvalue.VolatilityValue(value=1),
        rdfvalue.VolatilityValue(value=1),
        rdfvalue.VolatilityValue(value=1),
        rdfvalue.VolatilityValue(value=0),
        rdfvalue.VolatilityValue(svalue=""),
        rdfvalue.VolatilityValue()])
    volatility_values_2 = rdfvalue.VolatilityValues(values=[
        rdfvalue.VolatilityValue(value=50740512),
        rdfvalue.VolatilityValue(value=2),
        rdfvalue.VolatilityValue(value=2),
        rdfvalue.VolatilityValue(value=0),
        rdfvalue.VolatilityValue(value=275427826012256),
        rdfvalue.VolatilityValue(svalue="163255304:2168"),
        rdfvalue.VolatilityValue(svalue="XYZLock")])

    volatility_table = rdfvalue.VolatilityTable(
        headers=[rdfvalue.VolatilityHeader(name="offset_p"),
                 rdfvalue.VolatilityHeader(name="ptr_count"),
                 rdfvalue.VolatilityHeader(name="hnd_count"),
                 rdfvalue.VolatilityHeader(name="mutant_signal"),
                 rdfvalue.VolatilityHeader(name="mutant_thread"),
                 rdfvalue.VolatilityHeader(name="cid"),
                 rdfvalue.VolatilityHeader(name="mutant_name")],
        rows=[volatility_values_1,
              volatility_values_2])
    volatility_result = rdfvalue.VolatilityResult(
        plugin="mutantscan",
        sections=[rdfvalue.VolatilitySection(table=volatility_table)])

    converter = export.VolatilityResultToExportedVolatilityMutantConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(),
                                     volatility_result,
                                     token=self.token))

    self.assertEqual(len(results), 2)
    self.assertEqual(results[0].offset, 50211728)
    self.assertEqual(results[0].ptr_count, 1)
    self.assertEqual(results[0].handle_count, 1)
    self.assertEqual(results[0].signal, 1)
    self.assertEqual(results[0].thread, 0)
    self.assertEqual(results[0].cid, "")
    self.assertEqual(results[0].name, "")

    self.assertEqual(results[1].offset, 50740512)
    self.assertEqual(results[1].ptr_count, 2)
    self.assertEqual(results[1].handle_count, 2)
    self.assertEqual(results[1].signal, 0)
    self.assertEqual(results[1].thread, 275427826012256)
    self.assertEqual(results[1].cid, "163255304:2168")
    self.assertEqual(results[1].name, "XYZLock")

  def testRDFURNConverterWithURNPointingToFile(self):
    urn = rdfvalue.RDFURN("aff4:/C.00000000000000/some/path")

    fd = aff4.FACTORY.Create(urn, "VFSFile", token=self.token)
    fd.Set(fd.Schema.STAT(rdfvalue.StatEntry(
        aff4path=urn,
        pathspec=rdfvalue.PathSpec(path="/some/path",
                                   pathtype=rdfvalue.PathSpec.PathType.OS),
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892)))
    fd.Close()

    converter = export.RDFURNConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), urn,
                                     token=self.token))

    self.assertTrue(len(results))

    exported_files = [r for r in results
                      if r.__class__.__name__ == "ExportedFile"]
    self.assertEqual(len(exported_files), 1)
    exported_file = exported_files[0]

    self.assertTrue(exported_file)
    self.assertEqual(exported_file.urn, urn)

  def testClientSummaryToExportedNetworkInterfaceConverter(self):
    client_summary = rdfvalue.ClientSummary(
        interfaces=[rdfvalue.Interface(
            mac_address="123456",
            ifname="eth0",
            addresses=[
                rdfvalue.NetworkAddress(
                    address_type=rdfvalue.NetworkAddress.Family.INET,
                    packed_bytes=socket.inet_aton("127.0.0.1"),
                ),
                rdfvalue.NetworkAddress(
                    address_type=rdfvalue.NetworkAddress.Family.INET,
                    packed_bytes=socket.inet_aton("10.0.0.1"),
                    ),
                rdfvalue.NetworkAddress(
                    address_type=rdfvalue.NetworkAddress.Family.INET6,
                    packed_bytes=socket.inet_pton(socket.AF_INET6,
                                                  "2001:720:1500:1::a100"),
                    )
                ]
            )]
        )

    converter = export.ClientSummaryToExportedNetworkInterfaceConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(),
                                     client_summary,
                                     token=self.token))
    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].mac_address, "123456".encode("hex"))
    self.assertEqual(results[0].ifname, "eth0")
    self.assertEqual(results[0].ip4_addresses, "127.0.0.1 10.0.0.1")
    self.assertEqual(results[0].ip6_addresses, "2001:720:1500:1::a100")

  def testGetMetadata(self):
    client_urn = rdfvalue.ClientURN("C.0000000000000000")
    test_lib.ClientFixture(client_urn, token=self.token)
    metadata = export.GetMetadata(client_urn, token=self.token)
    self.assertEqual(metadata.os, u"Windows")
    self.assertEqual(metadata.labels, u"")

    # Now set CLIENT_INFO with labels
    client_info = rdfvalue.ClientInformation(client_name="grr",
                                             labels=["a", "b"])
    client = aff4.FACTORY.Open(client_urn, mode="rw", token=self.token)
    client.Set(client.Schema.CLIENT_INFO(client_info))
    client.Flush()
    metadata = export.GetMetadata(client_urn, token=self.token)
    self.assertEqual(metadata.os, u"Windows")
    self.assertEqual(metadata.labels, u"a,b")

  def testClientSummaryToExportedClientConverter(self):
    client_summary = rdfvalue.ClientSummary()
    metadata = rdfvalue.ExportedMetadata(hostname="ahostname")

    converter = export.ClientSummaryToExportedClientConverter()
    results = list(converter.Convert(metadata, client_summary,
                                     token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].metadata.hostname, "ahostname")

  def testRDFURNConverterWithURNPointingToCollection(self):
    urn = rdfvalue.RDFURN("aff4:/C.00000000000000/some/collection")

    fd = aff4.FACTORY.Create(urn, "RDFValueCollection", token=self.token)
    fd.Add(rdfvalue.StatEntry(
        aff4path=rdfvalue.RDFURN("aff4:/C.00000000000000/some/path"),
        pathspec=rdfvalue.PathSpec(path="/some/path",
                                   pathtype=rdfvalue.PathSpec.PathType.OS),
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892))
    fd.Close()

    converter = export.RDFURNConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), urn,
                                     token=self.token))

    self.assertTrue(len(results))

    exported_files = [r for r in results
                      if r.__class__.__name__ == "ExportedFile"]
    self.assertEqual(len(exported_files), 1)
    exported_file = exported_files[0]

    self.assertTrue(exported_file)
    self.assertEqual(exported_file.urn,
                     rdfvalue.RDFURN("aff4:/C.00000000000000/some/path"))

  def testGrrMessageConverter(self):
    msg = rdfvalue.GrrMessage(payload=DummyRDFValue4("some"))
    msg.source = rdfvalue.ClientURN("C.0000000000000000")
    test_lib.ClientFixture(msg.source, token=self.token)

    metadata = rdfvalue.ExportedMetadata(
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(1),
        source_urn=rdfvalue.RDFURN("aff4:/hunts/W:000000/Results"))

    converter = export.GrrMessageConverter()
    results = list(converter.Convert(metadata, msg, token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].timestamp,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(1))
    self.assertEqual(results[0].source_urn, "aff4:/hunts/W:000000/Results")

  def testGrrMessageConverterWithOneMissingClient(self):
    msg1 = rdfvalue.GrrMessage(payload=DummyRDFValue4("some"))
    msg1.source = rdfvalue.ClientURN("C.0000000000000000")
    test_lib.ClientFixture(msg1.source, token=self.token)

    msg2 = rdfvalue.GrrMessage(payload=DummyRDFValue4("some2"))
    msg2.source = rdfvalue.ClientURN("C.0000000000000001")

    metadata1 = rdfvalue.ExportedMetadata(
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(1),
        source_urn=rdfvalue.RDFURN("aff4:/hunts/W:000000/Results"))
    metadata2 = rdfvalue.ExportedMetadata(
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(2),
        source_urn=rdfvalue.RDFURN("aff4:/hunts/W:000001/Results"))

    converter = export.GrrMessageConverter()
    results = list(converter.BatchConvert(
        [(metadata1, msg1), (metadata2, msg2)], token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].timestamp,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(1))
    self.assertEqual(results[0].source_urn, "aff4:/hunts/W:000000/Results")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
