#!/usr/bin/env python

# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""This module loads all the selenium tests for the GUI."""



from grr.gui.plugins import acl_manager_test
from grr.gui.plugins import container_viewer_test
from grr.gui.plugins import cron_view_test
from grr.gui.plugins import fileview_test
from grr.gui.plugins import flow_management_test
from grr.gui.plugins import hunt_view_test
from grr.gui.plugins import inspect_test
from grr.gui.plugins import notifications_test
from grr.gui.plugins import statistics_test
from grr.gui.plugins import timeline_view_test