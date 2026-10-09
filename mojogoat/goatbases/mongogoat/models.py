# -*- coding: utf-8 -*-

"""
This is where we define our models.
"""

from mongoengine import Document, fields, DynamicDocument
import datetime
import json
from flask_mongoengine import BaseQuerySet
from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy without an app (will be set later)
sqldb = SQLAlchemy()

# Mongo Models
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
        """Convert queryset to JSON string array
        
        Returns:
            JSON string array
        """
        docs_json = []
        for doc in self:
            docs_json.append(doc.to_json())
        
        return "[%s]" % (",".join(docs_json))
        
    def to_dict(self):
        """Convert queryset to list of dictionaries
        
        Returns:
            List of dictionaries
        """
        result = []
        for doc in self:
            result.append(doc.to_dict())
        
        return result


class Node(PPrintMixin, DynamicDocument):
    meta = {'queryset_class': CustomQuerySet,
            'allow_inheritance': True}
    nodeid = fields.StringField(unique=True, required=True)
    nodename = fields.StringField()
    labels = fields.ListField(fields.StringField(), default=list)
    created_ts = fields.DateTimeField(default=datetime.datetime.now)
    updated_ts = fields.DateTimeField(default=datetime.datetime.now)
    
    def save(self, *args, **kwargs):
        if not self.created_ts:
            self.created_ts = datetime.datetime.now()
        self.updated_ts = datetime.datetime.now()
        return super(Node, self).save(*args, **kwargs)

    def __repr__(self):
        return "Node (%r)" % (self.nodeid)
        
    def to_dict(self):
        """Convert Node to dictionary, excluding MongoDB specific fields"""
        # Use mongoengine's built-in to_mongo method and convert to dict
        data = self.to_mongo().to_dict()
        
        # Remove MongoDB specific fields
        for field in ['_id', '_cls']:
            if field in data:
                data.pop(field)
        return data
        
    def to_json(self):
        """Convert Node to JSON string"""
        def json_serial(obj):
            """JSON serializer for objects not serializable by default json code"""
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
            
        return json.dumps(self.to_dict(), default=json_serial)


class Contact(Node):
    email = fields.ListField()
    phone = fields.ListField()
    first_name = fields.StringField()
    additional_name = fields.StringField()
    last_name = fields.StringField()
    
    def __repr__(self):
        return "Person (%r)" % (self.nodeid)
    
class Person(Node):
    gender = fields.StringField()
    photos = fields.ListField()
    birthdate = fields.DateTimeField()
    locations = fields.ListField()

    def __repr__(self):
        return "Person (%r)" % (self.nodeid)

# SQl Models
class Relationship(sqldb.Model):
    __tablename__="relationship"
    relationship_id  = sqldb.Column(sqldb.Integer, primary_key=True, autoincrement=True)
    source_id = sqldb.Column(sqldb.String, nullable=False)
    target_id = sqldb.Column(sqldb.String, nullable=False)
    story = sqldb.Column(sqldb.String, nullable=False)
    timestamp = sqldb.Column(sqldb.DateTime, nullable=False, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"Relationship('{self.relationship_id}', '{self.source_id}', '{self.target_id}', '{self.story}', '{self.timestamp}')"
    
    def to_dict(self):
        return {
        "relationship_id": self.relationship_id,
        "source_id": self.source_id,
        "target_id": self.target_id,
        "story": self.story,
        "timestamp": self.timestamp
    }

# MongoDB+PostgreSQL goat handler
class MongoDBPostgresGoat:
    """
    A wrapper class for MongoDB+Postgres operations
    """
    
    def __init__(self, config):
        """Initialize with configuration"""
        self.config = config
        self.goatname = config.get("name", "default_goat")
    
    def add_node(self, nodeid, **properties):
        """Add a node to MongoDB"""
        properties['nodeid'] = nodeid
        if 'name' in properties and 'nodename' not in properties:
            properties['nodename'] = properties['name']
            
        # Create node or update if exists
        node = Node.objects(nodeid=nodeid).first()
        if node is None:
            node = Node(nodeid=nodeid)
        
        # Update node with properties
        for key, value in properties.items():
            setattr(node, key, value)
        
        node.save()
        return node.to_dict()
    
    def get_node(self, nodeid):
        """Get a node by ID"""
        node = Node.objects(nodeid=nodeid).first()
        if node:
            return node.to_dict()
        return None
    
    def get_nodes(self):
        """Get all nodes"""
        nodes = Node.objects().all()
        return nodes.to_dict()
    
    def get_nodes_by_label(self, label):
        """Get nodes by label"""
        nodes = Node.objects(labels__contains=label).all()
        return nodes.to_dict()
    
    def delete_node(self, nodeid):
        """Delete a node and its relationships"""
        node = Node.objects(nodeid=nodeid).first()
        if not node:
            return False
        
        # Delete relationships
        relationships = Relationship.query.filter(
            sqldb.or_(
                Relationship.source_id == nodeid,
                Relationship.target_id == nodeid
            )
        ).all()
        
        for rel in relationships:
            sqldb.session.delete(rel)
        
        sqldb.session.commit()
        
        # Delete node
        node.delete()
        return True
    
    def create_relationship(self, source_id, target_id, story):
        """Create a relationship between two nodes"""
        # Check if nodes exist
        source_node = Node.objects(nodeid=source_id).first()
        target_node = Node.objects(nodeid=target_id).first()
        
        if not source_node or not target_node:
            return None
        
        # Check if relationship already exists
        existing_rel = Relationship.query.filter_by(
            source_id=source_id,
            target_id=target_id,
            story=story
        ).first()
        
        if existing_rel:
            return existing_rel.to_dict()
        
        # Create relationship
        rel = Relationship(
            source_id=source_id,
            target_id=target_id,
            story=story,
            timestamp=datetime.datetime.now()
        )
        
        sqldb.session.add(rel)
        sqldb.session.commit()
        
        return rel.to_dict()
    
    def get_relationships(self, source=None, target=None, story=None):
        """Get relationships with optional filtering"""
        query = Relationship.query
        
        if source:
            query = query.filter_by(source_id=source)
        
        if target:
            query = query.filter_by(target_id=target)
        
        if story:
            query = query.filter(Relationship.story.contains(story))
        
        relationships = query.all()
        return [rel.to_dict() for rel in relationships]
    
    def delete_relationship(self, relationship_id):
        """Delete a relationship by ID"""
        rel = Relationship.query.get(relationship_id)
        if not rel:
            return False
        
        sqldb.session.delete(rel)
        sqldb.session.commit()
        return True
    
    def get_composition(self):
        """Get the composition of nodes by label"""
        nodes = Node.objects().all()
        composition = {}
        
        for node in nodes:
            if hasattr(node, 'labels') and node.labels:
                for label in node.labels:
                    if label not in composition:
                        composition[label] = 0
                    composition[label] += 1
        
        return composition
    
    def get_taxonomy(self):
        """Get the taxonomy of relationship types"""
        # Get all relationships and count by story (relationship type)
        rels = Relationship.query.all()
        taxonomy = {}
        
        for rel in rels:
            if rel.story not in taxonomy:
                taxonomy[rel.story] = 0
            taxonomy[rel.story] += 1
        
        return taxonomy
    
    def dump_all_rels(self, filename):
        """Dump all relationships to a file"""
        relationships = self.get_relationships()
        
        with open(filename, "w") as f:
            for rel in relationships:
                f.write(f"{rel['source_id']}|{rel['story']}|{rel['target_id']}|{rel['timestamp']}\n")
        
        return len(relationships)