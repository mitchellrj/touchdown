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

from __future__ import absolute_import

import re

import six

from touchdown.core import argument, errors, resource, serializers
from touchdown.local.local import Step

try:
    import fuselage
    from fuselage import argument as _arg, bundle, builder, resources
except ImportError:
    raise errors.Error("You need the fuselage package to use the fuselage_bundle resource")


def underscore(title):
    return re.sub(r'(?<=[a-z])(?=[A-Z])', u'_', title).lower()


class FuselageArgument(argument.Argument):

    inner_arg = None

    def __init__(self, attr, default=None, help=None, **kwargs):
        self.arg_id = self.field = attr
        argument.Argument.__init__(self, default=default, help=help, **kwargs)

    def get_default(self, instance):
        if callable(self.inner_arg.default):
            return self.inner_arg.default(instance)
        return self.inner_arg.default

    def clean(self, instance, value):
        return self.inner_arg.clean(instance, value)

    def save(self, instance, value):
        return setattr(instance, self.arg_id, value)

    def present(self, instance):
        return self.arg_id in instance._values

    def serialize(self, instance, builder=None, runner=None):
        if self.present(instance):
            value = serializers.Argument(self.arg_id).render(runner, instance)
        else:
            value = self.get_default(instance)
        return value


class FuselageResourceType(resource.ResourceType, fuselage.resource.ResourceType):

    resources = {}

    def __new__(meta_cls, class_name, bases, attrs):
        attrs.setdefault("__resource_name__", class_name)
        attrs.setdefault("resource_name", underscore(class_name))
        tmp_cls = fuselage.resource.ResourceType.__new__(meta_cls, class_name, bases, attrs)
        args = tmp_cls.__args__
        new_attrs = {'__args__': args, 'policies': tmp_cls.policies}
        for attr, value in args.items():
            new_attrs[attr] = FuselageArgument(attr)
            new_attrs[attr].inner_arg = value
            args[attr] = new_attrs[attr]
        for attr, value in attrs.items():
            if isinstance(value, fuselage.argument.Argument):
                new_attrs[attr] = FuselageArgument(attr)
                new_attrs[attr].inner_arg = value
                args[attr] = new_attrs[attr]
            else:
                new_attrs[attr] = value

        cls = resource.ResourceType.__new__(meta_cls, class_name, bases, new_attrs)
        return cls


class FuselageResource(six.with_metaclass(FuselageResourceType, resource.Resource)):

    fuselage_resource_class = None
    serializer = serializers.Resource()

    def __init__(self, parent, *args, **kwargs):
        self._values = {}
        self.parent = parent
        self.dependencies = set()
        self.fuselage_resource_class.__init__(self, **kwargs)

    def clean(self, value):
        return value

    def serialize(self, builder=None, runner=None):
        retval = {}
        for name, arg in self.__args__.items():
            if arg.present(self):
                retval[name] = arg.serialize(self, builder=builder, runner=runner)
        return {self.__resource_name__: retval}


class ResourceBundle(fuselage.bundle.ResourceBundle):

    def __init__(self, runner, *args, **kwargs):
        fuselage.bundle.ResourceBundle.__init__(self, *args, **kwargs)
        self.runner = runner

    def _serialize_bundle(self, builder):
        obj = {"version": self.BUNDLE_VERSION}
        resources = obj['resources'] = []
        for r in self.resources:
            if not getattr(r, "_implicit", False):
                resources.append(r.serialize(builder, self.runner))
        return obj


class Bundle(Step):

    resource_name = "fuselage_bundle"

    resources = argument.ResourceList(FuselageResource, field='script')
    sudo = argument.Boolean(field='sudo', default=True)

    def serialize_resources(self, runner, value):
        b = ResourceBundle(runner)

        for item in value:
            # We call this to render any subobjects
            _kwargs = item.serializer.render(runner, item)
            b.add(item)
        return builder.build(b)


def make_fuselage_resource_serializer_compatible(resource_type):
    args = {'fuselage_resource_class': resource_type}
    cls = type(resource_type.__name__, (FuselageResource, resource_type,), args)

    def _(self, **kwargs):
        arguments = {'parent': self}
        arguments.update(kwargs)
        resource = cls(**arguments)
        if self.resources:
            self.resources.append(resource)
        else:
            self.resources = [resource]
        self.add_dependency(resource)
        return resource
    setattr(Bundle, 'add_%s' % cls.resource_name, _)
    return cls


for attr, value in vars(resources).items():
    if type(value) != fuselage.resource.ResourceType:
        continue
    locals()[attr] = make_fuselage_resource_serializer_compatible(value)