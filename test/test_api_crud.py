#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the MojoGOAT API CRUD operations
"""

import unittest
import json
import os
import tempfile
import shutil
from datetime import datetime

import sys
sys.path.append("/xpal-src/mojogoat")

from mojogoatapi import app, initialize_app, registry_path, active_goat

class MojoGoatAPICRUDTestCase(unittest.TestCase):
    """Test case for the MojoGOAT API CRUD operations"""
    
    def setUp(self):
        """Set up test environment"""
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        
        # Create a temporary registry file
        self.registry_file = os.path.join(self.test_dir, "test_registry.json")
        
        # Initialize the app with the test registry and clear any previous state
        app.config['TESTING'] = True  # Important for avoiding Flask errors
        
        # Reset globals in mojogoatapi by reimporting
        from mojogoatapi import active_goat, active_goat_name
        
        # Use direct assignment through mojogoatapi module
        import mojogoatapi
        mojogoatapi.active_goat = None
        mojogoatapi.active_goat_name = None
        
        initialize_app(self.registry_file)
        
        self.client = app.test_client()
        
        # Create a text goat for testing
        goat_dir = os.path.join(self.test_dir, "test_text_goat")
        os.makedirs(goat_dir, exist_ok=True)
        os.makedirs(os.path.join(goat_dir, "nodes"), exist_ok=True)
        os.makedirs(os.path.join(goat_dir, "snapshots"), exist_ok=True)
        
        with open(os.path.join(goat_dir, "newgrass.gq"), 'w') as f:
            f.write("")
        
        with open(os.path.join(goat_dir, "goatrels.gq"), 'w') as f:
            f.write("")
        
        data = {
            "name": "test_text_goat",
            "type": "text",
            "goat_path": goat_dir,
            "make_default": True,
            "make_active": True
        }
        
        response = self.client.post('/api/goats', json=data)
        self.assertEqual(response.status_code, 201)
    
    def tearDown(self):
        """Clean up test environment"""
        # Remove the temporary directory and all its contents
        shutil.rmtree(self.test_dir)
    
    def test_node_crud(self):
        """Test CRUD operations for nodes"""
        # Create a node
        node_data = {
            "nodeid": "test_node1",
            "nodename": "Test Node 1",
            "labels": ["Test", "Node"],
            "description": "This is a test node"
        }
        
        response = self.client.post('/api/nodes', json=node_data)
        self.assertEqual(response.status_code, 201)
        
        data = json.loads(response.data)
        self.assertEqual(data.get('nodeid'), "test_node1")
        self.assertEqual(data.get('nodename'), "Test Node 1")
        self.assertEqual(data.get('labels'), ["Test", "Node"])
        self.assertEqual(data.get('description'), "This is a test node")
        
        # Get the node
        response = self.client.get('/api/nodes/test_node1')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data.get('nodeid'), "test_node1")
        self.assertEqual(data.get('nodename'), "Test Node 1")
        self.assertEqual(data.get('labels'), ["Test", "Node"])
        self.assertEqual(data.get('description'), "This is a test node")
        
        # Update the node
        update_data = {
            "nodename": "Updated Node 1",
            "description": "This is an updated test node"
        }
        
        response = self.client.put('/api/nodes/test_node1', json=update_data)
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data.get('nodeid'), "test_node1")
        self.assertEqual(data.get('nodename'), "Updated Node 1")
        self.assertEqual(data.get('labels'), ["Test", "Node"])
        self.assertEqual(data.get('description'), "This is an updated test node")
        
        # Get all nodes
        response = self.client.get('/api/nodes')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get('nodeid'), "test_node1")
        
        # Get nodes by label
        response = self.client.get('/api/nodes/label/Test')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get('nodeid'), "test_node1")
        
        # Delete the node
        response = self.client.delete('/api/nodes/test_node1')
        self.assertEqual(response.status_code, 200)
        
        # Verify the node is deleted
        response = self.client.get('/api/nodes/test_node1')
        self.assertEqual(response.status_code, 404)
    
    def test_relationship_crud(self):
        """Test CRUD operations for relationships"""
        # Create two nodes
        node1_data = {
            "nodeid": "test_node1",
            "nodename": "Test Node 1",
            "labels": ["Test", "Node"]
        }
        
        node2_data = {
            "nodeid": "test_node2",
            "nodename": "Test Node 2",
            "labels": ["Test", "Node"]
        }
        
        self.client.post('/api/nodes', json=node1_data)
        self.client.post('/api/nodes', json=node2_data)
        
        # Create a relationship
        rel_data = {
            "source": "test_node1",
            "target": "test_node2",
            "story": "RELATES_TO"
        }
        
        response = self.client.post('/api/relationships', json=rel_data)
        self.assertEqual(response.status_code, 201)
        
        data = json.loads(response.data)
        self.assertEqual(data.get('source_id'), "test_node1")
        self.assertEqual(data.get('target_id'), "test_node2")
        self.assertEqual(data.get('story'), "RELATES_TO")
        
        # Get all relationships
        response = self.client.get('/api/relationships')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get('source_id'), "test_node1")
        self.assertEqual(data[0].get('target_id'), "test_node2")
        self.assertEqual(data[0].get('story'), "RELATES_TO")
        
        # Get relationship by ID
        rel_id = data[0].get('relationship_id')
        
        response = self.client.get(f'/api/relationships/{rel_id}')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data.get('source_id'), "test_node1")
        self.assertEqual(data.get('target_id'), "test_node2")
        self.assertEqual(data.get('story'), "RELATES_TO")
        
        # Get relationships by source
        response = self.client.get('/api/relationships?source=test_node1')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get('source_id'), "test_node1")
        
        # Get relationships by target
        response = self.client.get('/api/relationships?target=test_node2')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get('target_id'), "test_node2")
        
        # Get relationships by story
        response = self.client.get('/api/relationships?story=RELATES_TO')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get('story'), "RELATES_TO")
        
        # Delete the relationship
        response = self.client.delete(f'/api/relationships/{rel_id}')
        self.assertEqual(response.status_code, 200)
        
        # Verify the relationship is deleted
        response = self.client.get('/api/relationships')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(len(data), 0)
    
    def test_goat_operations(self):
        """Test goat-specific operations"""
        # Create some nodes and relationships
        node1_data = {
            "nodeid": "test_node1",
            "nodename": "Test Node 1",
            "labels": ["Person", "Employee"]
        }
        
        node2_data = {
            "nodeid": "test_node2",
            "nodename": "Test Node 2",
            "labels": ["Company", "Organization"]
        }
        
        self.client.post('/api/nodes', json=node1_data)
        self.client.post('/api/nodes', json=node2_data)
        
        rel_data = {
            "source": "test_node1",
            "target": "test_node2",
            "story": "WORKS_AT"
        }
        
        self.client.post('/api/relationships', json=rel_data)
        
        # Get composition
        response = self.client.get('/api/active-goat/composition')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data.get('Person'), 1)
        self.assertEqual(data.get('Employee'), 1)
        self.assertEqual(data.get('Company'), 1)
        self.assertEqual(data.get('Organization'), 1)
        
        # Get taxonomy
        response = self.client.get('/api/active-goat/taxonomy')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data.get('WORKS_AT'), 1)
        
        # Dump relationships
        dump_file = os.path.join(self.test_dir, "relationships_dump.txt")
        
        response = self.client.post('/api/active-goat/dump-relationships', json={"filename": dump_file})
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue("Successfully dumped" in data.get('message'))
        self.assertTrue(os.path.exists(dump_file))

if __name__ == '__main__':
    unittest.main()