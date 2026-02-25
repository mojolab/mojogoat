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

    def test_health_endpoint(self):
        """Test GET /health liveness check"""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data.get('status'), 'ok')
        self.assertIn('goat_count', data)
        self.assertIn('active_goat', data)

    def test_health_reflects_goat_count(self):
        """Test that /health goat_count updates when goats are added"""
        r1 = self.client.get('/health')
        count_before = json.loads(r1.data)['goat_count']

        self.client.post('/api/goats', json={"name": "hgoat", "type": "text"})

        r2 = self.client.get('/health')
        self.assertEqual(json.loads(r2.data)['goat_count'], count_before + 1)

    def test_post_node_with_slash_returns_400(self):
        """Test that nodeids containing '/' return 400 with a useful message"""
        import asyncio
        import mojogoatapi
        from mojogoat.goatbases.memorygoat import MemoryGoat

        mojogoatapi.active_goat = MemoryGoat()
        mojogoatapi.active_goat_name = "test_mem"

        r = self.client.post('/api/nodes', json={"nodeid": "val:/some/path"})
        self.assertEqual(r.status_code, 400)
        data = json.loads(r.data)
        self.assertIn("nodeid", data["error"])
        self.assertIn("/", data["error"])

    def test_get_relationships_props_filter(self):
        """Test GET /api/relationships filters by arbitrary props and limit"""
        import asyncio
        import mojogoatapi
        from mojogoat.goatbases.memorygoat import MemoryGoat

        g = MemoryGoat()
        asyncio.run(g.add_node("a"))
        asyncio.run(g.add_node("b"))
        asyncio.run(g.add_node("c"))
        asyncio.run(g.create_relationship("a", "b", "KNOWS", state="pending"))
        asyncio.run(g.create_relationship("a", "c", "KNOWS", state="confirmed"))

        mojogoatapi.active_goat = g
        mojogoatapi.active_goat_name = "test_mem"

        # Filter by props (state=pending)
        r = self.client.get('/api/relationships?state=pending')
        self.assertEqual(r.status_code, 200)
        rels = json.loads(r.data)
        self.assertEqual(len(rels), 1)
        self.assertEqual(rels[0]['target_id'], 'b')

        # Filter by target
        r = self.client.get('/api/relationships?target=c')
        self.assertEqual(r.status_code, 200)
        rels = json.loads(r.data)
        self.assertEqual(len(rels), 1)
        self.assertEqual(rels[0]['state'], 'confirmed')

        # Limit
        r = self.client.get('/api/relationships?limit=1')
        self.assertEqual(r.status_code, 200)
        rels = json.loads(r.data)
        self.assertEqual(len(rels), 1)

        # Combined: story + props + target
        r = self.client.get('/api/relationships?story=KNOWS&state=confirmed&target=c')
        self.assertEqual(r.status_code, 200)
        rels = json.loads(r.data)
        self.assertEqual(len(rels), 1)
        self.assertEqual(rels[0]['source_id'], 'a')

    def test_get_relationships_offset(self):
        """Test GET /api/relationships?offset=N paginates correctly"""
        import asyncio
        import mojogoatapi
        from mojogoat.goatbases.memorygoat import MemoryGoat

        g = MemoryGoat()
        asyncio.run(g.add_node("src"))
        for i in range(5):
            asyncio.run(g.add_node(f"tgt{i}"))
            asyncio.run(g.create_relationship("src", f"tgt{i}", "LINKED"))

        mojogoatapi.active_goat = g
        mojogoatapi.active_goat_name = "test_mem"

        all_r = self.client.get('/api/relationships')
        all_rels = json.loads(all_r.data)
        self.assertEqual(len(all_rels), 5)

        r = self.client.get('/api/relationships?offset=2')
        paged = json.loads(r.data)
        self.assertEqual(len(paged), 3)
        self.assertEqual(paged[0]['relationship_id'], all_rels[2]['relationship_id'])

        r2 = self.client.get('/api/relationships?offset=2&limit=2')
        paged2 = json.loads(r2.data)
        self.assertEqual(len(paged2), 2)


if __name__ == '__main__':
    unittest.main()