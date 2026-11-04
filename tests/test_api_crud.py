#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the MojoGOAT API CRUD operations (goat-scoped routes, API v2 / ADR-016)
"""

import unittest
import json
import os

from api_support import ApiEnv

GOAT = "test_text_goat"
BASE = f"/api/goats/{GOAT}"


class MojoGoatAPICRUDTestCase(unittest.TestCase):
    """Test case for the MojoGOAT API CRUD operations (goat-scoped, ADR-016)"""
    
    def setUp(self):
        """Set up test environment: temp registry/ops/data dirs and one text goat"""
        self.env = ApiEnv().start()
        self.client = self.env.client
        self.test_dir = self.env.root
        
        # Create a text goat for testing
        goat_dir = os.path.join(self.test_dir, GOAT)
        os.makedirs(goat_dir, exist_ok=True)
        os.makedirs(os.path.join(goat_dir, "nodes"), exist_ok=True)
        os.makedirs(os.path.join(goat_dir, "snapshots"), exist_ok=True)
        
        with open(os.path.join(goat_dir, "newgrass.gq"), 'w') as f:
            f.write("")
        
        with open(os.path.join(goat_dir, "goatrels.gq"), 'w') as f:
            f.write("")
        
        data = {
            "name": GOAT,
            "type": "text",
            "goat_path": goat_dir
        }
        
        response = self.client.post('/api/goats', json=data)
        self.assertEqual(response.status_code, 201)
    
    def tearDown(self):
        """Clean up test environment"""
        self.env.stop()
    
    def test_node_crud(self):
        """Test CRUD operations for nodes"""
        # Create a node
        node_data = {
            "nodeid": "test_node1",
            "nodename": "Test Node 1",
            "labels": ["Test", "Node"],
            "description": "This is a test node"
        }
        
        response = self.client.post(f'{BASE}/nodes', json=node_data)
        self.assertEqual(response.status_code, 201)
        
        data = json.loads(response.data)
        self.assertEqual(data.get('nodeid'), "test_node1")
        self.assertEqual(data.get('nodename'), "Test Node 1")
        self.assertEqual(data.get('labels'), ["Test", "Node"])
        self.assertEqual(data.get('description'), "This is a test node")
        
        # Get the node
        response = self.client.get(f'{BASE}/nodes/test_node1')
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
        
        response = self.client.put(f'{BASE}/nodes/test_node1', json=update_data)
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data.get('nodeid'), "test_node1")
        self.assertEqual(data.get('nodename'), "Updated Node 1")
        self.assertEqual(data.get('labels'), ["Test", "Node"])
        self.assertEqual(data.get('description'), "This is an updated test node")
        
        # Get all nodes
        response = self.client.get(f'{BASE}/nodes')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get('nodeid'), "test_node1")
        
        # Get nodes by label
        response = self.client.get(f'{BASE}/nodes/label/Test')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get('nodeid'), "test_node1")
        
        # Delete the node
        response = self.client.delete(f'{BASE}/nodes/test_node1')
        self.assertEqual(response.status_code, 200)
        
        # Verify the node is deleted
        response = self.client.get(f'{BASE}/nodes/test_node1')
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
        
        self.client.post(f'{BASE}/nodes', json=node1_data)
        self.client.post(f'{BASE}/nodes', json=node2_data)
        
        # Create a relationship
        rel_data = {
            "source": "test_node1",
            "target": "test_node2",
            "story": "RELATES_TO"
        }
        
        response = self.client.post(f'{BASE}/relationships', json=rel_data)
        self.assertEqual(response.status_code, 201)
        
        data = json.loads(response.data)
        self.assertEqual(data.get('source_id'), "test_node1")
        self.assertEqual(data.get('target_id'), "test_node2")
        self.assertEqual(data.get('story'), "RELATES_TO")
        
        # Get all relationships
        response = self.client.get(f'{BASE}/relationships')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get('source_id'), "test_node1")
        self.assertEqual(data[0].get('target_id'), "test_node2")
        self.assertEqual(data[0].get('story'), "RELATES_TO")
        
        # Get relationship by ID
        rel_id = data[0].get('relationship_id')
        
        response = self.client.get(f'{BASE}/relationships/{rel_id}')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data.get('source_id'), "test_node1")
        self.assertEqual(data.get('target_id'), "test_node2")
        self.assertEqual(data.get('story'), "RELATES_TO")
        
        # Get relationships by source
        response = self.client.get(f'{BASE}/relationships?source=test_node1')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get('source_id'), "test_node1")
        
        # Get relationships by target
        response = self.client.get(f'{BASE}/relationships?target=test_node2')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get('target_id'), "test_node2")
        
        # Get relationships by story
        response = self.client.get(f'{BASE}/relationships?story=RELATES_TO')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get('story'), "RELATES_TO")
        
        # Delete the relationship
        response = self.client.delete(f'{BASE}/relationships/{rel_id}')
        self.assertEqual(response.status_code, 200)
        
        # Verify the relationship is deleted
        response = self.client.get(f'{BASE}/relationships')
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
        
        self.client.post(f'{BASE}/nodes', json=node1_data)
        self.client.post(f'{BASE}/nodes', json=node2_data)
        
        rel_data = {
            "source": "test_node1",
            "target": "test_node2",
            "story": "WORKS_AT"
        }
        
        self.client.post(f'{BASE}/relationships', json=rel_data)
        
        # Get composition
        response = self.client.get(f'{BASE}/composition')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data.get('Person'), 1)
        self.assertEqual(data.get('Employee'), 1)
        self.assertEqual(data.get('Company'), 1)
        self.assertEqual(data.get('Organization'), 1)
        
        # Get taxonomy
        response = self.client.get(f'{BASE}/taxonomy')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data.get('WORKS_AT'), 1)
        
        # Dump relationships
        dump_file = os.path.join(self.test_dir, "relationships_dump.txt")
        
        response = self.client.post(f'{BASE}/dump-relationships', json={"filename": dump_file})
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue("Successfully dumped" in data.get('message'))
        self.assertTrue(os.path.exists(dump_file))

if __name__ == '__main__':
    unittest.main()