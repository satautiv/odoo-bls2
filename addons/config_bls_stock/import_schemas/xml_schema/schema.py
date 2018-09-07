# -*- coding=utf-8 -*-

import simplejson as json
from marshmallow import Schema, post_dump, pre_load, SchemaOpts
from .serializer import XML
from .utils import to_camel, to_lower_camel
from .types import ATTRIBUTES_NODE_NAME, COMMENTS_NODE_NAME, INLINE_NODE_NAME


def translate_field(field, include_ns=True):
    fname, fval = field
    if fval.data_key:
        # Don't change data_key fields
        old_name = fval.data_key
        new_name = old_name
    else:
        old_name = fname
        if 'attribute_for' in fval.metadata:
            new_name = to_lower_camel(fname)
        else:
            new_name = to_camel(fname)
        if new_name.lower().endswith('id'):
            new_name = new_name[:-2] + 'ID'
    if include_ns and 'ns' in fval.metadata:
        new_name = fval.metadata['ns'] + new_name
    return old_name, new_name


class XMLSchemaOpts(SchemaOpts):
    def __init__(self, meta, ordered=True):
        if not hasattr(meta, 'render_module'):
            meta.render_module = XML()
        super().__init__(meta, ordered)
        self.ordered = True


class XMLSchema(Schema):
    OPTIONS_CLASS = XMLSchemaOpts

    def dump(self, obj, many=None, update_fields=True, content_type=None, **kwargs):
        # Select render_module
        if content_type == 'application/xml':
            self.context['content_type'] = content_type
            root_node = self.Meta.root_node if hasattr(
                self.Meta, 'root_node') else None
            self.opts.render_module = XML(root_node=root_node)
        elif content_type == 'application/json':
            self.context['content_type'] = content_type
            self.opts.render_module = json
        return super().dump(obj, many, update_fields)
        # return self.opts.render_module.dump(obj, many, update_fields)

    def dumps(self, obj, content_type, many=None, update_fields=True, *args, **kwargs):
        # Pass content_type to our dump
        if not content_type:
            raise ValueError(
                'Unspecified content_type. Allowed values: "application/xml", "application/json"')
        serialized = self.dump(
            obj, many=many, update_fields=update_fields, content_type=content_type, **kwargs)
        return self.opts.render_module.dumps(serialized, *args, **kwargs)

    def loads(self, data, many=None, *args, **kwargs):
        # Select render_module
        first_char = data.strip()[0]
        if first_char == '<':
            root_node = self.Meta.root_node if hasattr(
                self.Meta, 'root_node') else None
            self.opts.render_module = XML(root_node=root_node)
        elif first_char == '{':
            self.opts.render_module = json
        else:
            raise ValueError('Could not determine data type')
        return super().loads(data, many, *args, **kwargs)

    @pre_load
    def pre_load_fields(self, data):
        # Translate fields
        translated_fields = [(field, *translate_field(field, include_ns=False))
                             for field in self.fields.items()]

        # Restore field names
        for field, old_name, new_name in translated_fields:
            if new_name in data and old_name != new_name:
                data[old_name] = data.pop(new_name)

            # Change to list if needed
            if hasattr(field[1], 'many') and field[1].many and old_name in data and not isinstance(data[old_name], list):
                data[old_name] = [data[old_name]]

        # Restore attributes
        if ATTRIBUTES_NODE_NAME in data:
            for field, old_name, new_name in translated_fields:
                if 'attribute_for' in field[1].metadata:
                    for_field = field[1].metadata['attribute_for']
                    for_old_name, for_new_name = translate_field(
                        (for_field, self.fields[for_field]), include_ns=False)

                    if for_old_name in data and new_name in data[ATTRIBUTES_NODE_NAME][for_new_name]:
                        data[old_name] = data[ATTRIBUTES_NODE_NAME][for_new_name].pop(
                            new_name)

            del data[ATTRIBUTES_NODE_NAME]

        return data

    @post_dump(pass_original=True)
    def post_dump_fields(self, data, origin):
        attributes = data.get(ATTRIBUTES_NODE_NAME, {}) or {}
        comments = data.get(COMMENTS_NODE_NAME, {}) or {}
        inlines = data.get(INLINE_NODE_NAME, {}) or {}

        # Skip None values
        skip_fields = set(fname for fname, fval in data.items() if fval is None)

        # Skip empty values
        def is_empty(val):
            if isinstance(val, list):
                return all([is_empty(x) for x in val])
            elif isinstance(val, (str, dict)):
                return not val
            else:
                return False
        skip_fields.update(fname for fname, fval in data.items() if is_empty(fval))

        # FIXME: patikrinti ar laukas required, jei taip, tai neskipinti
        for field in skip_fields:
            data.pop(field)

        # FIXME: patikrinti kur nusimusa context, teoriskai visada jame turetu buti content_type reiksme
        # use_namespaces = self.context['content_type'] == 'application/xml'
        use_namespaces = 'content_type' in self.context and self.context[
            'content_type'] == 'application/xml'

        translated_fields = [(field, *translate_field(field, include_ns=use_namespaces))
                             for field in self.fields.items()]

        remove_fields = set()
        for field, old_name, new_name in translated_fields:
            if old_name in data:
                if 'comment' in field[1].metadata:
                    comments[new_name] = field[1].metadata['comment']

                if 'attribute_for' in field[1].metadata:
                    for_field = field[1].metadata['attribute_for']
                    for_old_name, for_new_name = translate_field(
                        (for_field, self.fields[for_field]), include_ns=use_namespaces)

                    if for_new_name not in attributes:
                        attributes[for_new_name] = {}
                    # Here we need to check for various types, because old_name can be the same for multiple values when the same data_key is used
                    # In such cases we must extract the value from the constant or original object
                    if hasattr(field[1], 'constant'):
                        attributes[for_new_name][new_name] = field[1].constant
                    else:
                        if hasattr(origin, field[0]):
                            attributes[for_new_name][new_name] = getattr(origin, field[0])
                        else:
                            attributes[for_new_name][new_name] = data[old_name]
                    remove_fields.add(old_name)

                if 'inline' in field[1].metadata:
                    inlines[new_name] = 1

        if attributes:
            data[ATTRIBUTES_NODE_NAME] = attributes

        if comments:
            data[COMMENTS_NODE_NAME] = comments

        if inlines:
            data[INLINE_NODE_NAME] = inlines

        for old_name in remove_fields:
            if old_name in data:
                data.pop(old_name)

        # Do actual translation
        for field, old_name, new_name in translated_fields:
            if old_name in data:
                data[new_name] = data.pop(old_name)

        return data

    class Meta:
        ordered=True