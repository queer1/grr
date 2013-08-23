#!/usr/bin/env python
"""This file sets up the django environment."""

import os


import django
from django.conf import settings

import logging
from grr.lib import config_lib
from grr.lib import registry

config_lib.DEFINE_string(
    "AdminUI.webauth_manager", "NullWebAuthManager",
    "The web auth manager for controlling access to the UI.")

config_lib.DEFINE_bool("AdminUI.django_debug", True,
                       "Turn on to add django debugging")

config_lib.DEFINE_list(
    "AdminUI.django_allowed_hosts", ["*"],
    "Set the django ALLOWED_HOSTS parameter. "
    "See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts")


config_lib.DEFINE_string(
    "AdminUI.django_secret_key", "CHANGE_ME",
    "This is a secret key that should be set in the server "
    "config. It is used in XSRF and session protection.")


class DjangoInit(registry.InitHook):
  """Initialize the Django environment."""

  def RunOnce(self):
    """Configure the Django environment."""
    if django.VERSION[0] == 1 and django.VERSION[1] < 4:
      msg = ("The installed Django version is too old. We need 1.4+. You can "
             "install a new version with 'sudo easy_install Django'.")
      logging.error(msg)
      raise RuntimeError(msg)

    base_app_path = os.path.normpath(os.path.dirname(__file__))
    # Note that Django settings are immutable once set.
    django_settings = {
        "DEBUG": config_lib.CONFIG["AdminUI.django_debug"],
        "TEMPLATE_DEBUG": config_lib.CONFIG["AdminUI.django_debug"],
        "SECRET_KEY": config_lib.CONFIG["AdminUI.django_secret_key"],

        # Set to default as we don't supply an HTTPS server.
        # "CSRF_COOKIE_SECURE": not FLAGS.django_debug,  # Only send over HTTPS.
        # Where to find url mappings.
        "ROOT_URLCONF": "grr.gui.urls",
        "TEMPLATE_DIRS": ("%s/templates" % base_app_path,),
        # Don't use the database for sessions, use a file.
        "SESSION_ENGINE": "django.contrib.sessions.backends.file",
        "ALLOWED_HOSTS": config_lib.CONFIG["AdminUI.django_allowed_hosts"],
    }

    # The below will use conf/global_settings/py from Django, we need to
    # override every variable we need to set.
    settings.configure(**django_settings)

    if settings.SECRET_KEY == "CHANGE_ME":
      msg = "Please change the secret key in the settings module."
      logging.error(msg)


class GuiPluginsInit(registry.InitHook):
  """Initialize the GUI plugins once Django is initialized."""

  pre = ["DjangoInit"]

  def RunOnce(self):
    """Import the plugins once only."""
    # pylint: disable=unused-variable,C6204
    from grr.gui import gui_plugins
    # pylint: enable=unused-variable,C6204
