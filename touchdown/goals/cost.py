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

from touchdown.core.goals import Goal, register


class Cost(Goal):

    """ Estimate the cost of running this environment """

    name = "cost"

    def get_plan_class(self, resource):
        plan_class = resource.meta.get_plan("cost")
        if not plan_class:
            plan_class = resource.meta.get_plan("null")
        return plan_class

    def execute(self):
        for coster in self.collect_as_iterable("cost"):
            print (coster.resource, coster.cost())

register(Cost)
