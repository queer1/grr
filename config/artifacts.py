#!/usr/bin/env python
"""Configuration parameters for the artifact subsystem."""

import os

from grr.lib import config_lib


config_lib.DEFINE_list(
    "Artifacts.artifact_dirs",
    [os.path.normpath(os.path.dirname(__file__) + "/../../grr/artifacts"),
     os.path.normpath(os.path.dirname(__file__) + "/../../grr/artifacts/local")
    ], "A list directories to load artifacts from.")

config_lib.DEFINE_list("Artifacts.knowledge_base",
                       ["AllUsersAppDataEnvironmentVariable",
                        "AllUsersProfileEnvironmentVariable",
                        "CurrentControlSet",
                        "ProgramFiles",
                        "ProgramFilesx86",
                        "SystemDriveEnvironmentVariable",
                        "SystemRoot",
                        "TempEnvironmentVariable",
                        "UserShellFolders",
                        "WinCodePage",
                        "WinDirEnvironmentVariable",
                        "WinDomainName",
                        "WinPathEnvironmentVariable",
                        "WinTimeZone",
                        "WindowsRegistryProfiles",
                        "WindowsWMIProfileUsersHomeDir",
                        "WindowsWMIAccountUsersDomain",
                        "OSXUsers",
                        "LinuxUserProfiles"],
                       "List of artifacts that are collected regularly by"
                       " interrogate and used for interpolation of client-side"
                       " variables. Includes artifacts for all supported OSes. "
                       "Anything not in this list won't be downloaded by"
                       " interrogate so be sure to include any necessary"
                       " dependencies.")

config_lib.DEFINE_list("Artifacts.knowledge_base_additions", [],
                       "Extra artifacts to add to the knowledge_base list. This"
                       " allows per-site tweaks without having to redefine the"
                       " whole list.")

config_lib.DEFINE_list("Artifacts.knowledge_base_skip", [],
                       "Artifacts to remove from the knowledge_base list. This"
                       " allows per-site tweaks without having to redefine the"
                       " whole list.")

config_lib.DEFINE_list("Artifacts.knowledge_base_heavyweight",
                       ["WindowsWMIAccountUsersDomain"],
                       "Artifacts to skip when the 'lightweight' option is"
                       " set on interrogate. These artifacts are too expensive"
                       " or slow to collect regularly from all machines.")

config_lib.DEFINE_list("Artifacts.netgroup_filter_regexes", [],
                       help="Only parse groups that match one of these regexes"
                       " from /etc/netgroup files.")

config_lib.DEFINE_list("Artifacts.netgroup_user_blacklist", [],
                       help="Exclude these users when parsing /etc/netgroup "
                       "files.")

