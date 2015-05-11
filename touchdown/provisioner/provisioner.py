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

from touchdown.core import argument, action, resource, plan, serializers, workspace


class Step(resource.Resource):
    resource_name = "step"


class Target(resource.Resource):
    resource_name = "target"


class Provisioner(resource.Resource):

    resource_name = "provisioner"

    target = argument.Resource(Target)
    steps = argument.List(argument.Resource(Step))
    root = argument.Resource(workspace.Workspace)


class ApplyStep(action.Action):

    def __init__(self, plan, step):
        super(ApplyStep, self).__init__(plan)
        self.step = step

    @property
    def description(self):
        yield "Applying step {} to {}".format(self.step, self.resource.target)

    def run(self):
        kwargs = serializers.Resource().render(self.runner, self.step)
        client = self.get_plan(self.resource.target).get_client()
        client.run_script(kwargs['script'])


class Apply(plan.Plan):

    name = "apply"
    resource = Provisioner

    def get_actions(self):
        for step in self.resource.steps:
            yield ApplyStep(self, step)
