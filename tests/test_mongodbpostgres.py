#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for MongoDB+Postgres implementation
"""

import argparse
import json
import os
import sys
import unittest
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mongoengine import MongoEngine

sys.path.append("/xpal-src/mojogoat")
from mojogoat.goatbases.mongogoat.models import Node, Relationship, sqldb

class MongoDBPostgresGoat:
    """
    A wrapper class for MongoDB+Postgres operations, similar to Neo4jGoat
    Provides compatible interface for testing
    """
    
    def __init__(self, config_path):
        """Initialize with configuration from JSON file"""
        with open(config_path, "r") as f:
            self.config = json.load(f)
            
        # Initialize Flask app
        self.app = Flask(__name__)
        
        # Configure database connections
        self.app.config['SQLALCHEMY_DATABASE_URI'] = self.config.get('postgres_uri', 
            "postgresql://postgres:postgres@localhost:5432/xetrapal")
        self.app.config['MONGODB_SETTINGS'] = {
            'host': self.config.get('mongodb_uri', 'mongodb://localhost/mojogoat')
        }
        
        # Initialize database connections
        self.mongodb = MongoEngine(self.app)
        
        # Initialize the SQLAlchemy instance with our app
        sqldb.init_app(self.app)
        
        # Create tables if they don't exist
        with self.app.app_context():
            # Create database tables
            try:
                sqldb.create_all()
            except Exception as e:
                print(f"Error creating tables: {e}")
    
    def add_node(self, nodeid, **properties):
        """Add a node to MongoDB"""
        with self.app.app_context():
            properties['nodeid'] = nodeid
            if 'name' in properties and 'nodename' not in properties:
                properties['nodename'] = properties['name']
                
            # Create node directly
            node = Node.objects(nodeid=nodeid).first()
            if node is None:
                node = Node(nodeid=nodeid)
            
            # Update node with properties
            for key, value in properties.items():
                setattr(node, key, value)
            
            node.save()
            return node
    
    def link(self, source_id, target_id, relationship_type, date=None):
        """Create a relationship between two nodes"""
        with self.app.app_context():
            # Check if nodes exist
            source_node = Node.objects(nodeid=source_id).first()
            target_node = Node.objects(nodeid=target_id).first()
            
            if not source_node:
                print(f"Source node {source_id} not found")
                return None
                
            if not target_node:
                print(f"Target node {target_id} not found")
                return None
            
            # Check if relationship already exists
            existing_rel = Relationship.query.filter_by(
                source_id=source_id,
                target_id=target_id,
                story=relationship_type
            ).first()
            
            if existing_rel:
                return existing_rel
            
            # Create relationship
            relationship = Relationship(
                source_id=source_id,
                target_id=target_id,
                story=relationship_type,
                timestamp=datetime.now()
            )
            
            sqldb.session.add(relationship)
            sqldb.session.commit()
            return relationship
    
    def get_nodes(self):
        """Get all nodes"""
        with self.app.app_context():
            nodes = Node.objects().all()
            return [node.to_dict() for node in nodes]
    
    def get_node_by_id(self, nodeid):
        """Get a node by ID"""
        with self.app.app_context():
            node = Node.objects(nodeid=nodeid).first()
            if node:
                return node.to_dict()
            return None
    
    def get_relationships(self, source=None, target=None, relationship_type=None):
        """Get relationships with optional filtering"""
        with self.app.app_context():
            query = Relationship.query
            
            if source:
                query = query.filter_by(source_id=source)
            
            if target:
                query = query.filter_by(target_id=target)
            
            if relationship_type:
                query = query.filter_by(story=relationship_type)
            
            relationships = query.all()
            return [rel.to_dict() for rel in relationships]
    
    def get_composition(self):
        """Get the composition of nodes by label"""
        with self.app.app_context():
            # Get all nodes and count by label
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
        with self.app.app_context():
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
        with self.app.app_context():
            relationships = self.get_relationships()
            
            with open(filename, "w") as f:
                for rel in relationships:
                    f.write(f"{rel['source_id']}|{rel['story']}|{rel['target_id']}|{rel['timestamp']}\n")
            
            return len(relationships)

def main():
    """Main function to run tests"""
    parser = argparse.ArgumentParser(description="Test script for MongoDB+Postgres implementation")
    parser.add_argument("configjson", help="Path to the JSON file containing database connection details.")
    args = parser.parse_args()

    # Initialize MongoDBPostgresGoat
    goat = MongoDBPostgresGoat(args.configjson)
    
    # Load test data from testdatarels.gq
    testdata_path = os.path.join(os.path.dirname(__file__), "testdata", "testdatarels.gq")
    with open(testdata_path, "r") as f:
        testdata = f.readlines()

    # Parse and use test data
    for line in testdata:
        subject, predicate, obj, date = line.strip().split('|')
        goat.add_node(nodeid=subject, name=subject, labels=["Person"])
        goat.add_node(nodeid=obj, name=obj, labels=["Entity"])
        goat.link(subject, obj, predicate, date)

    # Test methods
    print("Testing get_composition...")
    print(goat.get_composition())

    print("Testing get_nodes...")
    print(goat.get_nodes())

    print("Testing dump_all_rels...")
    goat.dump_all_rels("mongodb_postgres_relationships_dump.txt")

    print("Testing get_taxonomy...")
    print(goat.get_taxonomy())

if __name__ == "__main__":
    main()

# Help message for JSON file format
# {
#     "mongodb_uri": "mongodb://localhost/mojogoat",
#     "postgres_uri": "postgresql://postgres:postgres@localhost:5432/xetrapal"
# }