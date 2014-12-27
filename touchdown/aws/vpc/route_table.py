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

from .vpc import VPC
from ..common import SimpleApply


class RouteTable(Resource):

    resource_name = "route_table"

    name = argument.String()
    vpc = argument.Resource(VPC)
    tags = argument.Dict()


class AddRouteTable(Action):

    @property
    def description(self):
        yield "Add route table"

    def run(self):
        vpc = self.get_target(self.resource.vpc)

        result = vpc.client.create_route_table(
            VpcId=vpc.object['VpcId'],
        )
        self.target.object = result['RouteTable']


class Apply(SimpleApply, Target):

    resource = RouteTable
    add_action = AddRouteTable
    key = "RouteTableId"

    def get_object(self, runner):
        self.client = runner.get_target(self.resource.vpc).client

        routetables = self.client.describe_route_tables(
            Filters=[
                {'Name': 'tag:name', 'Values': [self.resource.name]},
            ],
        )

        if len(routetables['RouteTables']) > 1:
            raise errors.Error("Too many possible route tables found")

        if routetables['RouteTables']:
            return routetables['RouteTables'][0]
