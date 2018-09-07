# -*- coding=utf-8 -*-

from .types import ATTRIBUTES_NODE_NAME, COMMENTS_NODE_NAME


def to_txt_type(value):
    return value if value is None else str(value).lower() if type(value) == bool else str(value)


def get_attribute(key, data):
    if ATTRIBUTES_NODE_NAME in data and key in data[ATTRIBUTES_NODE_NAME]:
        return data[ATTRIBUTES_NODE_NAME][key]
    else:
        return None


def get_comment(key, data):
    if COMMENTS_NODE_NAME in data and key in data[COMMENTS_NODE_NAME]:
        return data[COMMENTS_NODE_NAME][key]
    else:
        return None


def to_camel(snake_str):
    parts = snake_str.split('_')
    return ''.join(map(str.title, parts))


def to_lower_camel(snake_str):
    first, *others = snake_str.split('_')
    return ''.join([first.lower(), *map(str.title, others)])
