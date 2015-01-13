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

import itertools
import json

from touchdown.core.utils import force_str


class hd(dict):

    def __hash__(self):
        return hash(frozenset(self.items()))


class FieldNotPresent(Exception):
    pass


class RequiredFieldNotPresent(Exception):
    pass


class Serializer(object):

    def render(self, runner, object):
        raise NotImplementedError(self.render)

    def dependencies(self, object):
        return frozenset()


class Identity(Serializer):

    def render(self, runner, object):
        return object

    def dependencies(self, object):
        return frozenset()


class Chain(Serializer):

    def __init__(self, *children, **kwargs):
        self.skip_empty = kwargs.get('skip_empty', False)
        self.children = children

    def render(self, runner, object):
        result = []
        for child in self.children:
            try:
                result.extend(child.render(runner, object))
            except FieldNotPresent:
                pass
        if not len(result) and self.skip_empty:
            raise FieldNotPresent()
        return tuple(result)

    def dependencies(self, object):
        return frozenset(itertools.chain(*(c.dependencies(object) for c in self.children)))


class Const(Serializer):

    def __init__(self, const):
        self.const = const

    def render(self, runner, object):
        return self.const

    def dependencies(self, object):
        if hasattr(self.const, "add_dependency"):
            return frozenset((self.const, ))
        return frozenset()


class Identifier(Serializer):

    def __init__(self, inner=Identity()):
        self.inner = inner

    def render(self, runner, object):
        resource = self.inner.render(runner, object)
        if not resource:
            raise FieldNotPresent()
        result = runner.get_target(resource).resource_id
        if not result:
            return "pending ({})".format(object)
        return result

    def dependencies(self, object):
        return self.inner.dependencies(object)


class Property(Serializer):

    def __init__(self, property, inner=Identity()):
        self.property = property
        self.inner = inner

    def render(self, runner, object):
        return runner.get_target(self.inner.render(runner, object)).object.get(self.property, "dummy")

    def dependencies(self, object):
        return self.inner.dependencies(object)


class Argument(Serializer):

    def __init__(self, attribute):
        self.attribute = attribute

    def render(self, runner, object):
        result = getattr(object, self.attribute)
        if not object.__args__[self.attribute].present(object):
            if result is None:
                raise FieldNotPresent(self.attribute)
            pass
        return result


class Expression(Serializer):

    def __init__(self, callback):
        self.callback = callback

    def render(self, runner, object):
        return self.callback(runner, object)


class Annotation(Serializer):

    """ An annotation node does not change the output, but records some metadata about it """

    def __init__(self, inner):
        self.inner = inner

    def dependencies(self, object):
        return self.inner.dependencies(object)


class Required(Annotation):

    def render(self, runner, object):
        try:
            return self.inner.render(runner, object)
        except FieldNotPresent:
            raise RequiredFieldNotPresent()


class Default(Annotation):

    def __init__(self, inner=Identity(), default=None):
        super(Default, self).__init__(inner)
        self.default = default

    def render(self, runner, object):
        try:
            return self.inner.render(runner, object)
        except FieldNotPresent:
            return self.default


class Formatter(Serializer):

    def __init__(self, inner=Identity()):
        self.inner = inner

    def dependencies(self, object):
        return self.inner.dependencies(object)


class Boolean(Formatter):

    def render(self, runner, object):
        return True if self.inner.render(runner, object) else False


class String(Formatter):
    def render(self, runner, object):
        try:
            return force_str(self.inner.render(runner, object))
        except ValueError:
            return str(self.inner.render(runner, object))


class Integer(Formatter):
    def render(self, runner, object):
        return int(self.inner.render(runner, object))


class ListOfOne(Formatter):
    def render(self, runner, object):
        return [self.inner.render(runner, object)]


class CommaSeperatedList(Formatter):
    def render(self, runner, object):
        return ",".join(self.inner.render(runner, object))


class Json(Formatter):
    def render(self, runner, object):
        return json.dumps(self.inner.render(runner, object))


class Format(Formatter):
    def __init__(self, format_string, inner=Identity()):
        super(Format, self).__init__(inner)
        self.format_string = format_string

    def render(self, runner, object):
        return self.format_string.format(self.inner.render(runner, object))


class Dict(Serializer):

    def __init__(self, **kwargs):
        self.kwargs = {}
        for k, v in kwargs.items():
            if not isinstance(v, Serializer):
                v = Const(v)
            self.kwargs[k] = v

    def render(self, runner, object):
        result = hd()
        for key, value in self.kwargs.items():
            try:
                result[key] = value.render(runner, object)
            except FieldNotPresent:
                continue
        if not len(result):
            raise FieldNotPresent()
        return result

    def dependencies(self, object):
        return frozenset(itertools.chain(*tuple(c.dependencies(object) for c in self.kwargs.values())))


class Resource(Dict):

    """ Automatically generate a Dict definition by inspect the 'field'
    paramters of a resource """

    def __init__(self, mode="create"):
        self.mode = mode
        self.kwargs = {}

    def render(self, runner, object):
        for name, serializer in getattr(object, "extra_serializers", {}).items():
            self.kwargs[name] = serializer

        for argument_name, arg in object.arguments:
            if not (arg.present(object) or arg.default is not None):
                continue
            if not hasattr(arg, "field"):
                continue
            if self.mode == "create" and not getattr(arg, "aws_create", True):
                continue
            if self.mode == "update" and not getattr(arg, "aws_update", True):
                continue

            self.kwargs[arg.field] = Context(
                Argument(argument_name),
                arg.serializer
            )

        return super(Resource, self).render(runner, object)

    def dependencies(self, object):
        raise NotImplementedError(self.dependencies, object)


class List(Serializer):

    def __init__(self, child=Identity(), skip_empty=False):
        self.child = child
        self.skip_empty = skip_empty

    def render(self, runner, object):
        result = []
        for row in object:
            result.append(self.child.render(runner, row))
        if not result and self.skip_empty:
            raise FieldNotPresent()
        return tuple(result)

    def dependencies(self, object):
        return frozenset((self.child.dependencies(object), ))


class Context(Serializer):

    def __init__(self, serializer, inner):
        self.serializer = serializer
        self.inner = inner

    def render(self, runner, object):
        object = self.serializer.render(runner, object)
        return self.inner.render(runner, object)

    def dependencies(self, object):
        return self.inner.dependencies(object).union(self.serializer.dependencies(object))