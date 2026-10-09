#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for MongoDB+Postgres node operations
"""

import json
import os
import sys
import unittest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mongoengine import MongoEngine
import uuid

sys.path.append("/xpal-src/mojogoat")
from mojogoat.goatbases.mongogoat.models import Node, Relationship, sqldb

class TestMongoDBNodes(unittest.TestCase):
    """Test MongoDB node operations"""
    
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
        
        # Initialize database connections
        cls.mongodb = MongoEngine(cls.app)
        
        # Initialize the SQLAlchemy instance with our app
        sqldb.init_app(cls.app)
        
        # Create test context
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        
        # Clean up any existing test data
        cls.clean_test_data()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        cls.clean_test_data()
        cls.app_context.pop()
    
    @classmethod
    def clean_test_data(cls):
        """Clean up test data"""
        # Delete nodes with test prefix
        Node.objects(nodeid__startswith="test_").delete()
    
    def test_01_create_node(self):
        """Test creating a node"""
        # Create a unique node ID for this test
        node_id = f"test_node_{uuid.uuid4().hex[:8]}"
        
        # Create test node
        node = Node(
            nodeid=node_id,
            nodename="Test Node",
            labels=["TestLabel", "Person"]
        )
        node.save()
        
        # Verify node was created
        saved_node = Node.objects(nodeid=node_id).first()
        self.assertIsNotNone(saved_node)
        self.assertEqual(saved_node.nodeid, node_id)
        self.assertEqual(saved_node.nodename, "Test Node")
        self.assertIn("TestLabel", saved_node.labels)
        self.assertIn("Person", saved_node.labels)
    
    def test_02_read_node(self):
        """Test reading a node"""
        # Create a unique node ID for this test
        node_id = f"test_node_{uuid.uuid4().hex[:8]}"
        
        # Create test node
        node = Node(
            nodeid=node_id,
            nodename="Read Test Node",
            labels=["ReadTest"]
        )
        node.save()
        
        # Verify node can be read
        saved_node = Node.objects(nodeid=node_id).first()
        self.assertIsNotNone(saved_node)
        self.assertEqual(saved_node.nodeid, node_id)
        self.assertEqual(saved_node.nodename, "Read Test Node")
        self.assertIn("ReadTest", saved_node.labels)
    
    def test_03_update_node(self):
        """Test updating a node"""
        # Create a unique node ID for this test
        node_id = f"test_node_{uuid.uuid4().hex[:8]}"
        
        # Create test node
        node = Node(
            nodeid=node_id,
            nodename="Original Name",
            labels=["OriginalLabel"]
        )
        node.save()
        
        # Update node
        node = Node.objects(nodeid=node_id).first()
        node.nodename = "Updated Name"
        node.labels = ["UpdatedLabel", "Person"]
        node.custom_field = "Custom Value"
        node.save()
        
        # Verify node was updated
        updated_node = Node.objects(nodeid=node_id).first()
        self.assertIsNotNone(updated_node)
        self.assertEqual(updated_node.nodeid, node_id)
        self.assertEqual(updated_node.nodename, "Updated Name")
        self.assertIn("UpdatedLabel", updated_node.labels)
        self.assertIn("Person", updated_node.labels)
        self.assertEqual(updated_node.custom_field, "Custom Value")
    
    def test_04_delete_node(self):
        """Test deleting a node"""
        # Create a unique node ID for this test
        node_id = f"test_node_{uuid.uuid4().hex[:8]}"
        
        # Create test node
        node = Node(
            nodeid=node_id,
            nodename="Delete Test Node",
            labels=["DeleteTest"]
        )
        node.save()
        
        # Verify node exists
        saved_node = Node.objects(nodeid=node_id).first()
        self.assertIsNotNone(saved_node)
        
        # Delete node
        saved_node.delete()
        
        # Verify node was deleted
        deleted_node = Node.objects(nodeid=node_id).first()
        self.assertIsNone(deleted_node)
    
    def test_05_node_to_dict(self):
        """Test node to_dict method"""
        # Create a unique node ID for this test
        node_id = f"test_node_{uuid.uuid4().hex[:8]}"
        
        # Create test node
        node = Node(
            nodeid=node_id,
            nodename="Dict Test Node",
            labels=["DictTest"]
        )
        node.save()
        
        # Get node and convert to dict
        saved_node = Node.objects(nodeid=node_id).first()
        node_dict = saved_node.to_dict()
        
        # Verify dict properties
        self.assertIsInstance(node_dict, dict)
        self.assertEqual(node_dict['nodeid'], node_id)
        self.assertEqual(node_dict['nodename'], "Dict Test Node")
        self.assertIn("DictTest", node_dict['labels'])
        
        # Verify MongoDB fields are removed
        self.assertNotIn('_id', node_dict)
        self.assertNotIn('_cls', node_dict)
    
    def test_06_node_to_json(self):
        """Test node to_json method"""
        # Create a unique node ID for this test
        node_id = f"test_node_{uuid.uuid4().hex[:8]}"
        
        # Create test node
        node = Node(
            nodeid=node_id,
            nodename="JSON Test Node",
            labels=["JSONTest"]
        )
        node.save()
        
        # Get node and convert to JSON
        saved_node = Node.objects(nodeid=node_id).first()
        node_json = saved_node.to_json()
        
        # Verify JSON can be parsed back to dict
        node_dict = json.loads(node_json)
        self.assertIsInstance(node_dict, dict)
        self.assertEqual(node_dict['nodeid'], node_id)
        self.assertEqual(node_dict['nodename'], "JSON Test Node")
        self.assertIn("JSONTest", node_dict['labels'])
        
        # Verify MongoDB fields are removed
        self.assertNotIn('_id', node_dict)
        self.assertNotIn('_cls', node_dict)
    
    def test_07_query_nodes_by_label(self):
        """Test querying nodes by label"""
        # Clean up previous test nodes first
        Node.objects().delete()
        
        # Create unique node IDs for this test
        node1_id = f"test_node_{uuid.uuid4().hex[:8]}"
        node2_id = f"test_node_{uuid.uuid4().hex[:8]}"
        node3_id = f"test_node_{uuid.uuid4().hex[:8]}"
        
        # Create test nodes with different labels
        node1 = Node(nodeid=node1_id, nodename="Label Test 1", labels=["Person", "Employee"])
        node2 = Node(nodeid=node2_id, nodename="Label Test 2", labels=["Person", "Manager"])
        node3 = Node(nodeid=node3_id, nodename="Label Test 3", labels=["Company"])
        
        node1.save()
        node2.save()
        node3.save()
        
        # Query nodes by label
        person_nodes = Node.objects(labels__contains="Person").all()
        employee_nodes = Node.objects(labels__contains="Employee").all()
        company_nodes = Node.objects(labels__contains="Company").all()
        
        # Get total count of nodes for debugging
        total_nodes = Node.objects().count()
        
        # Verify query results
        self.assertEqual(len(person_nodes), 2, f"Expected 2 Person nodes, got {len(person_nodes)}. Total nodes: {total_nodes}")
        self.assertEqual(len(employee_nodes), 1, f"Expected 1 Employee node, got {len(employee_nodes)}")
        self.assertEqual(len(company_nodes), 1, f"Expected 1 Company node, got {len(company_nodes)}")
        
        # Verify specific nodes are in the correct results
        person_node_ids = [node.nodeid for node in person_nodes]
        self.assertIn(node1_id, person_node_ids)
        self.assertIn(node2_id, person_node_ids)
        self.assertNotIn(node3_id, person_node_ids)
        
        company_node_ids = [node.nodeid for node in company_nodes]
        self.assertIn(node3_id, company_node_ids)
        self.assertNotIn(node1_id, company_node_ids)
        self.assertNotIn(node2_id, company_node_ids)

if __name__ == '__main__':
    unittest.main()