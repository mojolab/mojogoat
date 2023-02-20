# -*- coding: utf-8 -*-

"""
This is where we define our models.
"""

from mongoengine import Document, fields, DynamicDocument
import datetime
import bson
import json
from flask_mongoengine import BaseQuerySet



class PPrintMixin(object):
    def __str__(self):
        return '<{}: id={!r}>'.format(type(self).__name__, self.id)

    def __repr__(self):
        attrs = []
        for name in self._fields.keys():
            value = getattr(self, name)
            if isinstance(value, (Document, DynamicDocument)):
                attrs.append('\n    {} = {!s},'.format(name, value))
            elif isinstance(value, (datetime.datetime)):
                attrs.append('\n    {} = {},'.format(
                    name, value.strftime("%Y-%m-%d %H:%M:%S")))
            else:
                attrs.append('\n    {} = {!r},'.format(name, value))
        return '<{}: {}\n>'.format(type(self).__name__, ''.join(attrs))


class CustomQuerySet(BaseQuerySet):
    def to_json(self):
        return "[%s]" % (",".join([doc.to_json() for doc in self]))
    def to_dict(self):
        return [doc.to_dict() for doc in self]
    


class Node(PPrintMixin, DynamicDocument):
    meta = {'queryset_class': CustomQuerySet,
            'allow_inheritance': True}
    nodeid = fields.StringField(unique=True, required=True)
    nodename = fields.StringField()
    nodelabels = fields.ListField(fields.StringField())
    created_ts = fields.DateTimeField(default=datetime.datetime.now)
    updated_ts = fields.DateTimeField(default=datetime.datetime.now)
    def save(self, *args, **kwargs):
        if not self.created_ts:
            self.created_ts = datetime.datetime.now()
        self.updated_ts = datetime.datetime.now()
        return super(Node, self).save(*args, **kwargs)

    def __repr__(self):
        return "Node (%r)" % (self.nodeid)


class Person(Node):
    meta = {'queryset_class': CustomQuerySet}
    name = fields.StringField()
    def __repr__(self):
        return "Person (%r)" % (self.nodeid)
