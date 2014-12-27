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

from ..account import AWS
from ..common import SimpleApply


class VPC(Resource):

    resource_name = "vpc"

    name = argument.String()
    cidr_block = argument.IPNetwork()
    account = argument.Resource(AWS)
    tags = argument.Dict()


class AddVPC(Action):

    @property
    def description(self):
        yield "Add virtual private cloud '{}'".format(self.resource.name)

    def run(self):
        obj = self.target.object = self.target.client.create_vpc(
            CidrBlock=str(self.resource.cidr_block),
        )

        waiter = self.target.client.get_waiter("vpc_available")
        waiter.wait(VpcIds=[obj['VpcId']])


class Apply(SimpleApply, Target):

    resource = VPC
    add_action = AddVPC
    key = 'VpcId'

    def get_object(self, runner):
        self.client = runner.get_target(self.resource.account).get_client('ec2')
        for vpc in self.client.describe_vpcs()['Vpcs']:
            if vpc['CidrBlock'] == str(self.resource.cidr_block):
                return vpc