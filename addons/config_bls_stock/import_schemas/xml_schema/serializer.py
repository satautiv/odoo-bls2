# -*- coding=utf-8 -*-

from lxml import etree

from .types import ATTRIBUTES_NODE_NAME, COMMENTS_NODE_NAME, INLINE_NODE_NAME
from .utils import get_attribute, get_comment, to_txt_type


comment_type = getattr(etree, '_Comment')
element_type = getattr(etree, '_Element')


class XML(object):
    ROOT_NODE = etree.Element('Objects')

    def __init__(self, root_node=None, clean_func=to_txt_type):
        if isinstance(root_node, element_type):
            self.ROOT_NODE = root_node
        self.clean_func = clean_func

    def load(self, obj, *args, **kwargs):
        return self.xml2dict(obj)

    def loads(self, sobj, *args, **kwargs):
        obj = etree.fromstring(sobj.encode('utf8'))
        return self.load(obj)

    def dump(self, obj, *args, **kwargs):
        self.ROOT_NODE.clear()
        if isinstance(obj, (list, tuple)):
            map(lambda payload: self.ROOT_NODE.append(
                self.dict2xml(self.ROOT_NODE, payload)), obj)
        elif isinstance(obj, dict):
            self.dict2xml(self.ROOT_NODE, obj)
        return self.ROOT_NODE

    def dumps(self, obj, *args, **kwargs):
        dumped_data = self.dump(obj, *args, **kwargs)
        if not isinstance(dumped_data, element_type):
            dumped_data = self.ROOT_NODE
        return etree.tostring(dumped_data, *args, **kwargs)

    def dict2xml(self, element, d):
        for k, v in d.items():
            if k in (ATTRIBUTES_NODE_NAME, COMMENTS_NODE_NAME, INLINE_NODE_NAME) or v is None:
                continue

            if isinstance(v, dict):
                # Serialize the child dictionary
                child = etree.Element(k, attrib=get_attribute(k, d))
                comment = get_comment(k, d)
                if comment:
                    child.append(etree.Comment(comment))
                self.dict2xml(child, v)
                element.append(child)
            elif isinstance(v, list):
                # Serialize the child list
                inlines = d.get(INLINE_NODE_NAME, []) or []
                for item in v:
                    child = etree.Element(k, attrib=get_attribute(k, d))
                    comment = get_comment(k, d)
                    if comment:
                        child.append(etree.Comment(comment))

                    if isinstance(item, (bytes, str)):
                        child.text = self.clean_func(item)
                    else:
                        self.dict2xml(element if k in inlines else child, item)

                    if k not in inlines:
                        element.append(child)
            else:
                child = etree.Element(k, attrib=get_attribute(k, d))
                child.text = self.clean_func(v)

                comment = get_comment(k, d)
                if comment:
                    child.append(etree.Comment(comment))

                element.append(child)

    def xml2dict(self, element):
        d = {}
        for e in element.iterchildren():
            if not isinstance(e, comment_type):
                # Strip namespaces
                key = e.tag.split('}')[1] if '}' in e.tag else e.tag
                if len(e) > 0:
                    value = self.xml2dict(e)
                else:
                    value = e.text if e.text else self.xml2dict(e)

                # Get attributes
                if e.attrib:
                    if ATTRIBUTES_NODE_NAME not in d:
                        d[ATTRIBUTES_NODE_NAME] = {}
                    d[ATTRIBUTES_NODE_NAME][key] = e.attrib

                if value is not {}:
                    if key in d:
                        if not isinstance(d[key], list):
                            d[key] = [d[key]]
                        d[key].append(value)
                    else:
                        d[key] = value
        return d
