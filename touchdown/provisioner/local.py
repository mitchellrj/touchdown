# Copyright 2015 Isotoma Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import errno
import os
import tempfile
import subprocess
import sys

from touchdown.core import argument
from touchdown.core import errors
from touchdown.core import plan
from touchdown.core import workspace

from .provisioner import Target


class Local(Target):

    resource_name = "local"

    user = argument.String()
    state = argument.String(default=os.path.abspath('.fuselage'))

    root = argument.Resource(workspace.Workspace)


class Connection(object):

    def __init__(self, plan):
        self.plan = plan
        self.resource = plan.resource

    def run_script(self, script, stdout=None, stderr=None):
        fd, script_name = tempfile.mkstemp()
        try:
            with os.fdopen(fd, 'wb') as fh:
                fh.write(script.read())
            os.chmod(script_name, 0o755)

            command = [sys.executable]
            if self.resource.user:
                command = ['sudo', '-u', self.resource.user]

            command.extend([script_name, '--no-changes-ok'])

            if self.resource.state:
                command.extend(['--state', os.path.abspath('.fuselage')])

            proc = subprocess.Popen(
                command, stdout=stdout, stderr=stderr)
            output, error_output = proc.communicate()
            exit_code = proc.returncode
            if exit_code != 0:
                raise errors.CommandFailed(exit_code, output, error_output)
        finally:
            try:
                os.close(fd)
            except OSError as e:
                if e.errno != errno.EBADF:
                    raise
            if os.path.exists(script_name):
                os.unlink(script_name)


class LocalPlan(plan.Plan):

    name = "describe"
    resource = Local

    def get_client(self):
        return Connection(self)

    def get_actions(self):
        return []
