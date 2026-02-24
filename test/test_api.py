#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the MojoGOAT API
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

class MojoGoatAPITestCase(unittest.TestCase):
    """Test case for the MojoGOAT API"""
    
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

        # Also reset the routes module-level reference so no state leaks between tests
        from mojogoat.routes import set_active_goat_ref
        set_active_goat_ref(None)

        initialize_app(self.registry_file)
        
        self.client = app.test_client()
    
    def tearDown(self):
        """Clean up test environment"""
        # Remove the temporary directory and all its contents
        shutil.rmtree(self.test_dir)
    
    def test_list_goats_empty(self):
        """Test listing goats when the registry is empty"""
        response = self.client.get('/api/goats')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(len(data.get('goats', [])), 0)
        self.assertIsNone(data.get('default'))
        self.assertIsNone(data.get('active'))
    
    def test_create_text_goat(self):
        """Test creating a text goat"""
        goat_dir = os.path.join(self.test_dir, "test_text_goat")
        os.makedirs(goat_dir, exist_ok=True)
        
        data = {
            "name": "test_text_goat",
            "type": "text",
            "goat_path": goat_dir,
            "make_default": True,
            "make_active": True
        }
        
        response = self.client.post('/api/goats', json=data)
        self.assertEqual(response.status_code, 201)
        
        # Check that the goat was added to the registry
        response = self.client.get('/api/goats')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(len(data.get('goats', [])), 1)
        self.assertEqual(data.get('default'), "test_text_goat")
        self.assertEqual(data.get('active'), "test_text_goat")
    
    def test_create_neo4j_goat(self):
        """Test creating a Neo4j goat"""
        # Create a sample Neo4j config file
        config_path = os.path.join(self.test_dir, "neo4j_config.json")
        with open(config_path, 'w') as f:
            json.dump({
                "url": "bolt://localhost:7687",
                "database": "neo4j",
                "password": "password"
            }, f)
        
        data = {
            "name": "test_neo4j_goat",
            "type": "neo4j",
            "config_path": config_path,
            "make_default": True,
            "make_active": True
        }
        
        response = self.client.post('/api/goats', json=data)
        self.assertEqual(response.status_code, 201)
        
        # Check that the goat was added to the registry
        response = self.client.get('/api/goats')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(len(data.get('goats', [])), 1)
        self.assertEqual(data.get('default'), "test_neo4j_goat")
        self.assertEqual(data.get('active'), "test_neo4j_goat")
    
    def test_set_registry_path(self):
        """Test setting the registry path"""
        new_registry_path = os.path.join(self.test_dir, "new_registry.json")
        
        data = {
            "path": new_registry_path
        }
        
        response = self.client.post('/api/registry', json=data)
        self.assertEqual(response.status_code, 201)
        
        # Check that the registry path was updated
        response = self.client.get('/api/registry')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data.get('registry_path'), new_registry_path)
    
    def test_set_active_goat(self):
        """Test setting the active goat"""
        # Create two goats
        data1 = {
            "name": "test_goat1",
            "type": "text",
            "goat_path": os.path.join(self.test_dir, "test_goat1"),
            "make_default": True,
            "make_active": True
        }
        
        data2 = {
            "name": "test_goat2",
            "type": "text",
            "goat_path": os.path.join(self.test_dir, "test_goat2")
        }
        
        # Create goat1
        response = self.client.post('/api/goats', json=data1)
        self.assertEqual(response.status_code, 201)
        
        # Create goat2
        response = self.client.post('/api/goats', json=data2)
        self.assertEqual(response.status_code, 201)
        
        # Set active goat to goat2
        data = {
            "name": "test_goat2",
            "make_default": True
        }
        
        response = self.client.post('/api/active-goat', json=data)
        self.assertEqual(response.status_code, 200)
        
        # Check that goat2 is now the active goat
        response = self.client.get('/api/active-goat')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data.get('active_goat'), "test_goat2")
        
        # Check that goat2 is now the default goat
        response = self.client.get('/api/goats')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data.get('default'), "test_goat2")
    
    def test_error_no_active_goat(self):
        """Test error when no active goat is selected"""
        # Don't set an active goat
        
        # Try to get nodes
        response = self.client.get('/api/nodes')
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertEqual(data.get('error'), "No active goat selected")
        
        # Try to create a node
        response = self.client.post('/api/nodes', json={"nodeid": "test_node"})
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertEqual(data.get('error'), "No active goat selected")
    
    def test_error_missing_fields(self):
        """Test error when required fields are missing"""
        # Test missing name and type
        response = self.client.post('/api/goats', json={})
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertEqual(data.get('error'), "Missing required fields: name and type")
        
        # Text goat with no explicit goat_path is valid — path is auto-derived from name
        response = self.client.post('/api/goats', json={"name": "test_goat_auto", "type": "text"})
        self.assertEqual(response.status_code, 201)

        # Test missing config_path for neo4j goat
        response = self.client.post('/api/goats', json={"name": "test_goat", "type": "neo4j"})
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertEqual(data.get('error'), "Missing required field: config_path for neo4j goat")

if __name__ == '__main__':
    unittest.main()