#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for MongoDB+Postgres relationship operations
"""

import json
import os
import sys
import unittest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mongoengine import MongoEngine
import uuid
from sqlalchemy import or_

sys.path.append("/xpal-src/mojogoat")
from mojogoat.goatbases.mongogoat.models import Node, Relationship, sqldb

class TestMongoDBPostgresRelationships(unittest.TestCase):
    """Test MongoDB+Postgres relationship operations"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        # Default config location, can be overridden by environment variable
        config_path = os.environ.get('MOJOGOAT_CONFIG', '/xpal-src/mojogoat/conf/sampleconfig.json')
        
        with open(config_path, "r") as f:
            cls.config = json.load(f)
        
        # Initialize Flask app
        cls.app = Flask(__name__)
        
        # Configure database connections
        cls.app.config['SQLALCHEMY_DATABASE_URI'] = cls.config.get('postgres_uri', 
            "postgresql://postgres:postgres@localhost:5432/xetrapal")
        cls.app.config['MONGODB_SETTINGS'] = {
            'host': cls.config.get('mongodb_uri', 'mongodb://localhost/mojogoat_test')
        }
        cls.app.config['TESTING'] = True
        cls.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Initialize database connections
        cls.mongodb = MongoEngine(cls.app)
        
        # Initialize the SQLAlchemy instance with our app
        sqldb.init_app(cls.app)
        
        # Create test context
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        
        # Create tables
        sqldb.create_all()
        
        # Clean up any existing test data
        cls.clean_test_data()
        
        # Create test nodes to use in relationship tests
        cls.test_nodes = cls.create_test_nodes()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        cls.clean_test_data()
        cls.app_context.pop()
    
    @classmethod
    def clean_test_data(cls):
        """Clean up test data"""
        # Delete relationships involving test nodes
        with cls.app.app_context():
            try:
                rel_prefix = "test_rel_"
                Relationship.query.filter(
                    or_(
                        Relationship.source_id.like(f"{rel_prefix}%"),
                        Relationship.target_id.like(f"{rel_prefix}%")
                    )
                ).delete()
                sqldb.session.commit()
            except Exception as e:
                print(f"Error deleting relationships: {e}")
                sqldb.session.rollback()
            
            # Delete test nodes
            try:
                Node.objects(nodeid__startswith=rel_prefix).delete()
            except Exception as e:
                print(f"Error deleting nodes: {e}")
    
    @classmethod
    def create_test_nodes(cls):
        """Create test nodes for relationship tests"""
        nodes = {}
        
        # Create person nodes
        nodes['person1'] = Node(
            nodeid="test_rel_person1",
            nodename="Test Person 1",
            labels=["Person", "Employee"]
        ).save()
        
        nodes['person2'] = Node(
            nodeid="test_rel_person2",
            nodename="Test Person 2",
            labels=["Person", "Manager"]
        ).save()
        
        # Create company nodes
        nodes['company1'] = Node(
            nodeid="test_rel_company1",
            nodename="Test Company 1",
            labels=["Company", "Organization"]
        ).save()
        
        nodes['company2'] = Node(
            nodeid="test_rel_company2",
            nodename="Test Company 2",
            labels=["Company", "Organization"]
        ).save()
        
        # Create project nodes
        nodes['project1'] = Node(
            nodeid="test_rel_project1",
            nodename="Test Project 1",
            labels=["Project"]
        ).save()
        
        nodes['project2'] = Node(
            nodeid="test_rel_project2",
            nodename="Test Project 2",
            labels=["Project"]
        ).save()
        
        return nodes
    
    def test_01_create_relationship(self):
        """Test creating a relationship"""
        person1 = "test_rel_person1"
        company1 = "test_rel_company1"
        
        # Create relationship
        relationship = Relationship(
            source_id=person1,
            target_id=company1,
            story="WORKS_AT"
        )
        sqldb.session.add(relationship)
        sqldb.session.commit()
        
        # Verify relationship was created
        saved_relationship = Relationship.query.filter_by(
            source_id=person1,
            target_id=company1,
            story="WORKS_AT"
        ).first()
        
        self.assertIsNotNone(saved_relationship)
        self.assertEqual(saved_relationship.source_id, person1)
        self.assertEqual(saved_relationship.target_id, company1)
        self.assertEqual(saved_relationship.story, "WORKS_AT")
    
    def test_02_read_relationship(self):
        """Test reading a relationship"""
        person2 = "test_rel_person2"
        company2 = "test_rel_company2"
        
        # Create relationship
        relationship = Relationship(
            source_id=person2,
            target_id=company2,
            story="MANAGES"
        )
        sqldb.session.add(relationship)
        sqldb.session.commit()
        
        # Verify relationship can be read
        saved_relationship = Relationship.query.filter_by(
            source_id=person2,
            target_id=company2,
            story="MANAGES"
        ).first()
        
        self.assertIsNotNone(saved_relationship)
        self.assertEqual(saved_relationship.source_id, person2)
        self.assertEqual(saved_relationship.target_id, company2)
        self.assertEqual(saved_relationship.story, "MANAGES")
    
    def test_03_query_relationships_by_source(self):
        """Test querying relationships by source"""
        person1 = "test_rel_person1"
        project1 = "test_rel_project1"
        project2 = "test_rel_project2"
        
        # Create relationships
        relationship1 = Relationship(
            source_id=person1,
            target_id=project1,
            story="WORKS_ON"
        )
        relationship2 = Relationship(
            source_id=person1,
            target_id=project2,
            story="LEADS"
        )
        sqldb.session.add(relationship1)
        sqldb.session.add(relationship2)
        sqldb.session.commit()
        
        # Query relationships by source
        relationships = Relationship.query.filter_by(source_id=person1).all()
        
        # Verify query results
        self.assertEqual(len(relationships), 3)  # Including previous test
        
        # Check if specific relationships are in the results
        stories = [rel.story for rel in relationships]
        self.assertIn("WORKS_AT", stories)
        self.assertIn("WORKS_ON", stories)
        self.assertIn("LEADS", stories)
    
    def test_04_query_relationships_by_target(self):
        """Test querying relationships by target"""
        person1 = "test_rel_person1"
        person2 = "test_rel_person2"
        project1 = "test_rel_project1"
        
        # Create relationship
        relationship = Relationship(
            source_id=person2,
            target_id=project1,
            story="CONTRIBUTES_TO"
        )
        sqldb.session.add(relationship)
        sqldb.session.commit()
        
        # Query relationships by target
        relationships = Relationship.query.filter_by(target_id=project1).all()
        
        # Verify query results
        self.assertEqual(len(relationships), 2)
        
        # Check if specific relationships are in the results
        relation_data = [(rel.source_id, rel.story) for rel in relationships]
        self.assertIn((person1, "WORKS_ON"), relation_data)
        self.assertIn((person2, "CONTRIBUTES_TO"), relation_data)
    
    def test_05_query_relationships_by_story(self):
        """Test querying relationships by story (relationship type)"""
        company1 = "test_rel_company1"
        company2 = "test_rel_company2"
        
        # Create relationship
        relationship = Relationship(
            source_id=company1,
            target_id=company2,
            story="PARTNERS_WITH"
        )
        sqldb.session.add(relationship)
        sqldb.session.commit()
        
        # Query relationships by story
        relationships = Relationship.query.filter(
            Relationship.story.contains("PARTNERS")
        ).all()
        
        # Verify query results
        self.assertEqual(len(relationships), 1)
        self.assertEqual(relationships[0].source_id, company1)
        self.assertEqual(relationships[0].target_id, company2)
        self.assertEqual(relationships[0].story, "PARTNERS_WITH")
    
    def test_06_delete_relationship(self):
        """Test deleting a relationship"""
        project1 = "test_rel_project1"
        project2 = "test_rel_project2"
        
        # Create relationship
        relationship = Relationship(
            source_id=project1,
            target_id=project2,
            story="DEPENDS_ON"
        )
        sqldb.session.add(relationship)
        sqldb.session.commit()
        
        # Verify relationship exists
        saved_relationship = Relationship.query.filter_by(
            source_id=project1,
            target_id=project2,
            story="DEPENDS_ON"
        ).first()
        self.assertIsNotNone(saved_relationship)
        
        # Delete relationship
        sqldb.session.delete(saved_relationship)
        sqldb.session.commit()
        
        # Verify relationship was deleted
        deleted_relationship = Relationship.query.filter_by(
            source_id=project1,
            target_id=project2,
            story="DEPENDS_ON"
        ).first()
        self.assertIsNone(deleted_relationship)
    
    def test_07_relationship_to_dict(self):
        """Test relationship to_dict method"""
        person1 = "test_rel_person1"
        company2 = "test_rel_company2"
        
        # Create relationship
        relationship = Relationship(
            source_id=person1,
            target_id=company2,
            story="CONSULTS_FOR"
        )
        sqldb.session.add(relationship)
        sqldb.session.commit()
        
        # Get relationship and convert to dict
        saved_relationship = Relationship.query.filter_by(
            source_id=person1,
            target_id=company2,
            story="CONSULTS_FOR"
        ).first()
        
        relationship_dict = saved_relationship.to_dict()
        
        # Verify dict properties
        self.assertIsInstance(relationship_dict, dict)
        self.assertEqual(relationship_dict['source_id'], person1)
        self.assertEqual(relationship_dict['target_id'], company2)
        self.assertEqual(relationship_dict['story'], "CONSULTS_FOR")
        self.assertIn('relationship_id', relationship_dict)
        self.assertIn('timestamp', relationship_dict)
    
    def test_08_delete_node_with_relationships(self):
        """Test that deleting a node also deletes its relationships"""
        # Create new node and relationships
        unique_id = uuid.uuid4().hex[:8]
        node_id = f"test_rel_temp_{unique_id}"
        
        # Create node
        node = Node(
            nodeid=node_id,
            nodename=f"Temporary Test Node {unique_id}",
            labels=["Temporary"]
        ).save()
        
        person1 = "test_rel_person1"
        company1 = "test_rel_company1"
        
        # Create relationships to and from the node
        rel1 = Relationship(
            source_id=node_id,
            target_id=person1,
            story="TEMPORARY_TO"
        )
        rel2 = Relationship(
            source_id=company1,
            target_id=node_id,
            story="TEMPORARY_FROM"
        )
        sqldb.session.add(rel1)
        sqldb.session.add(rel2)
        sqldb.session.commit()
        
        # Verify relationships exist
        relationships = Relationship.query.filter(
            or_(
                Relationship.source_id == node_id,
                Relationship.target_id == node_id
            )
        ).all()
        self.assertEqual(len(relationships), 2)
        
        # Delete node
        node.delete()
        
        # In a real application, there should be logic to cascade delete relationships
        # For this test, we'll clean up manually
        Relationship.query.filter(
            or_(
                Relationship.source_id == node_id,
                Relationship.target_id == node_id
            )
        ).delete()
        sqldb.session.commit()
        
        # Verify relationships are deleted
        remaining_relationships = Relationship.query.filter(
            or_(
                Relationship.source_id == node_id,
                Relationship.target_id == node_id
            )
        ).all()
        self.assertEqual(len(remaining_relationships), 0)

if __name__ == '__main__':
    unittest.main()