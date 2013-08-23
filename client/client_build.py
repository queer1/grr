#!/usr/bin/env python
"""This tool builds or repacks the client binaries.

This handles invocations for the build across the supported platforms including
handling Visual Studio, pyinstaller and other packaging mechanisms.
"""

import os
import platform
import sys
import time


# pylint: disable=unused-import
from grr.client import client_plugins
# pylint: enable=unused-import

from grr.lib import build
from grr.lib import builders
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import startup
from grr.lib import type_info

parser = flags.PARSER

if "32 bit" in sys.version:
  default_arch = "i386"
else:
  default_arch = "amd64"

parser.add_argument(
    "--platform", choices=["darwin", "linux", "windows"],
    default=platform.system().lower(),
    help="The platform to build or repack for. This will default to "
    "the current platform: %s." % platform.system())

parser.add_argument(
    "--arch", choices=["amd64", "i386"],
    default=default_arch,
    help="The architecture to build or repack for.")

config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.source", must_exist=False,
    default=os.path.normpath(__file__ + "/../../.."),
    help="The location of the source files."))

config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.executables_dir",
    default="%(ClientBuilder.source)/grr/executables",
    help="The directory that contains the executables."))

# Initialize sub parsers and their arguments.
subparsers = parser.add_subparsers(
    title="subcommands", dest="subparser_name", description="valid subcommands")

# Build arguments.
parser_build = subparsers.add_parser(
    "build", help="Build a client from source.")

parser_repack = subparsers.add_parser(
    "repack", help="Repack a zip file into an installer (Only useful when "
    "signing).")

parser_repack.add_argument("--package", default=None,
                           help="The package zip file to repack.")

parser_repack.add_argument("--output", default=None,
                           help="The path to write the output installer.")

parser_deploy = subparsers.add_parser(
    "deploy", help="Build a deployable self installer from a package.")

parser_deploy.add_argument("--template", default=None,
                           help="The template file to deploy.")

parser_deploy.add_argument("--output", default=None,
                           help="The path to write the output installer.")


config_lib.DEFINE_string(
    name="ClientBuilder.build_time",
    default=time.ctime(),
    help="Time of build to embed into binary.")

config_lib.DEFINE_string(
    "ClientBuilder.packagemaker",
    default=("/Developer/Applications/Utilities/PackageMaker.app/Contents"
             "/MacOS/PackageMaker"),
    help="Location of the PackageMaker executable.")

args = parser.parse_args()


def main(_):
  """Launch the appropriate builder."""
  config_lib.CONFIG.AddContext(
      "ClientBuilder Context",
      "Context applied when we run the client builder script.")

  startup.Init()

  # The following is used to change the identity of the builder based on the
  # target platform.
  context = flags.FLAGS.context
  if args.arch == "amd64":
    context.append("Arch:amd64")
  else:
    context.append("Arch:i386")

  if args.subparser_name == "build":
    if args.platform == "darwin":
      context.append("Platform:Darwin")
      builder_obj = builders.DarwinClientBuilder(context=context)
    elif args.platform == "windows":
      context.append("Platform:Windows")
      builder_obj = builders.WindowsClientBuilder(context=context)
    elif args.platform == "linux":
      context.append("Platform:Linux")
      builder_obj = builders.LinuxClientBuilder(context=context)
    else:
      parser.error("Unsupported build platform: %s" % args.platform)

    builder_obj.MakeExecutableTemplate()

  elif args.subparser_name == "repack":
    if args.platform == "darwin":
      context.append("Platform:Darwin")
      deployer = build.DarwinClientDeployer(context=context)
    elif args.platform == "windows":
      context.append("Platform:Windows")
      deployer = build.WindowsClientDeployer(context=context)
    elif args.platform == "linux":
      context.append("Platform:Linux")
      deployer = build.LinuxClientDeployer(context=context)
    else:
      parser.error("Unsupported build platform: %s" % args.platform)

    deployer.RepackInstaller(open(args.package, "rb").read(), args.output)

  elif args.subparser_name == "deploy":
    if args.platform == "darwin":
      context.append("Platform:Darwin")
      deployer = build.DarwinClientDeployer(context=context)

    elif args.platform == "windows":
      context.append("Platform:Windows")
      deployer = build.WindowsClientDeployer(context=context)

    elif args.platform == "linux":
      context.append("Platform:Linux")
      deployer = build.LinuxClientDeployer(context=context)

    else:
      parser.error("Unsupported build platform: %s" % args.platform)

    template_path = args.template or config_lib.CONFIG.Get(
        "ClientBuilder.template_path", context=deployer.context)

    deployer.MakeDeployableBinary(template_path, args.output)


if __name__ == "__main__":
  flags.StartMain(main)
