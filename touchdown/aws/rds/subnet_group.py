# Copyright 2014 Isotoma Limited
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

from touchdown.core.resource import Resource
from touchdown.core.target import Target
from touchdown.core.action import Action
from touchdown.core import argument, errors

from touchdown.aws.vpc import Subnet

from ..account import AWS
from ..common import SimpleApply


class SubnetGroup(Resource):

    resource_name = "db_subnet_group"

    name = argument.String()
    description = argument.String()
    subnets = argument.ResourceList(Subnet)
    tags = argument.Dict()

    account = argument.Resource(AWS)


class AddSubnetGroup(Action):

    @property
    def description(self):
        yield "Add DB subnet group '{}'".format(self.resource.name)

    def run(self):
        result = self.target.client.create_db_subnet_group(
            DBSubnetGroupName=self.resource.name,
            DBSubnetGroupDescription=self.resource.description,
            SubnetIds=subnets,
        )


class Apply(SimpleApply, Target):

    resource = SubnetGroup
    add_action = AddSubnetGroup
    key = 'DBSubnetGroupId'

    def get_object(self, runner):
        self.client = runner.get_target(self.resource.account).get_client('rds')

        try:
            subnets = self.client.describe_db_subnet_groups(
                DBSubnetGroupName = self.resource.name,
                )
        except Exception as e:
            if e.response['Error']['Code'] == 'DBSubnetGroupNotFoundFault':
                return

        if len(subnets['DBSubnetGroups']) > 1:
            raise error.Error("Multiple matches for DBSubnetGroups named {}".format(self.resource.name))
        if subnets['DBSubnetGroups']:
            return subnets['DBSubnetGroup'][0]
