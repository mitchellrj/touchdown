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
from touchdown.core.plan import Plan
from touchdown.core import argument, serializers, diff

from ..account import BaseAccount
from ..common import SimpleDescribe, SimpleApply, SimpleDestroy

from ..sns import Topic
from ..s3 import Bucket
from ..iam import Role


class Pipeline(Resource):

    resource_name = "pipeline"

    name = argument.String(field="Name")
    input_bucket = argument.Resource(Bucket, field="InputBucket")
    output_bucket = argument.Resource(Bucket, field="OutputBucket")
    # key = argument.Resource(KmsKey, field="AwsKmsKeyArn")

    role = argument.Resource(
        Role,
        field="Role",
        serializer=serializers.Property("Arn")
    )

    progressing = argument.Resource(
        Topic,
        field="Progressing",
        serializer=serializers.Property("TopicArn"),
        group="notifications"
    )

    completed = argument.Resource(
        Topic,
        field="Completed",
        serializer=serializers.Property("TopicArn"),
        group="notifications"
    )

    warning = argument.Resource(
        Topic,
        field="Warning",
        serializer=serializers.Property("TopicArn"),
        group="notifications"
    )

    error = argument.Resource(
        Topic,
        field="Error",
        serializer=serializers.Property("TopicArn"),
        group="notifications"
    )

    # content_config = argument.Dict(field="ContentConfig", default=None)
    # thumbnail_config = argument.Dict(field="ThumbnailConfig", default=None)

    account = argument.Resource(BaseAccount)


class Describe(SimpleDescribe, Plan):

    resource = Pipeline
    service_name = 'elastictranscoder'
    describe_action = "list_pipelines"
    describe_envelope = "Pipelines"
    describe_filters = {}
    key = 'Id'

    def describe_object_matches(self, pipeline):
        return pipeline['Name'] == self.resource.name


class Apply(SimpleApply, Describe):

    create_action = "create_pipeline"

    def update_object(self):
        d = diff.DiffSet(self.runner, self.resource, self.object.get('Notifications', {}), group="notifications")
        if not d.matches():
            yield self.generic_action(
                ["Update pipline notification topics"] + list(d.get_descriptions()),
                self.client.update_pipeline_notifications,
                Id=serializers.Identifier(),
                Notifications=serializers.Resource(group="notifications"),
            )


class Destroy(SimpleDestroy, Describe):

    destroy_action = "delete_pipeline"
