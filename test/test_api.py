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

import pytest

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

        app.config['TESTING'] = True

        import mojogoatapi
        mojogoatapi.active_goat = None
        mojogoatapi.active_goat_name = None

        from mojogoat.routes import set_active_goat_ref
        set_active_goat_ref(None)

        from mojogoat import operations
        operations.reset_store()

        initialize_app(self.registry_file)

        self.client = app.test_client()

    def tearDown(self):
        """Clean up test environment"""
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

        response = self.client.get('/api/goats')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(len(data.get('goats', [])), 1)
        self.assertEqual(data.get('default'), "test_text_goat")
        self.assertEqual(data.get('active'), "test_text_goat")

    def test_create_neo4j_goat(self):
        """Test creating a Neo4j goat"""
        pytest.importorskip("neo4j")
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

        response = self.client.get('/api/registry')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data.get('registry_path'), new_registry_path)

    def test_set_active_goat(self):
        """Test setting the active goat"""
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

        response = self.client.post('/api/goats', json=data1)
        self.assertEqual(response.status_code, 201)

        response = self.client.post('/api/goats', json=data2)
        self.assertEqual(response.status_code, 201)

        data = {
            "name": "test_goat2",
            "make_default": True
        }

        response = self.client.post('/api/active-goat', json=data)
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/api/active-goat')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data.get('active_goat'), "test_goat2")

        response = self.client.get('/api/goats')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data.get('default'), "test_goat2")

    def test_error_no_active_goat(self):
        """Test error when no active goat is selected"""
        response = self.client.get('/api/nodes')
        self.assertEqual(response.status_code, 404)

        data = json.loads(response.data)
        self.assertEqual(data.get('error'), "No active goat selected")

        response = self.client.post('/api/nodes', json={"nodeid": "test_node"})
        self.assertEqual(response.status_code, 404)

        data = json.loads(response.data)
        self.assertEqual(data.get('error'), "No active goat selected")

    def test_error_missing_fields(self):
        """Test error when required fields are missing"""
        response = self.client.post('/api/goats', json={})
        self.assertEqual(response.status_code, 400)

        data = json.loads(response.data)
        self.assertEqual(data.get('error'), "Missing required fields: name and type")

        # Text goat with no explicit goat_path is valid — path is auto-derived from name
        response = self.client.post('/api/goats', json={"name": "test_goat_auto", "type": "text"})
        self.assertEqual(response.status_code, 201)

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

        r = self.client.get('/api/relationships?state=pending')
        self.assertEqual(r.status_code, 200)
        rels = json.loads(r.data)
        self.assertEqual(len(rels), 1)
        self.assertEqual(rels[0]['target_id'], 'b')

        r = self.client.get('/api/relationships?target=c')
        self.assertEqual(r.status_code, 200)
        rels = json.loads(r.data)
        self.assertEqual(len(rels), 1)
        self.assertEqual(rels[0]['state'], 'confirmed')

        r = self.client.get('/api/relationships?limit=1')
        self.assertEqual(r.status_code, 200)
        rels = json.loads(r.data)
        self.assertEqual(len(rels), 1)

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

    # ------------------------------------------------------------------
    # Item 16 — API coverage gaps
    # ------------------------------------------------------------------

    def test_patch_relationship_updates_props(self):
        """PATCH /api/relationships/<id> merges props and returns 200"""
        import asyncio
        import mojogoatapi
        from mojogoat.goatbases.memorygoat import MemoryGoat

        g = MemoryGoat()
        asyncio.run(g.add_node("a"))
        asyncio.run(g.add_node("b"))
        rel = asyncio.run(g.create_relationship("a", "b", "KNOWS", state="pending"))
        rel_id = rel['relationship_id']

        mojogoatapi.active_goat = g
        mojogoatapi.active_goat_name = "test_mem"

        r = self.client.patch(f'/api/relationships/{rel_id}', json={"state": "confirmed", "note": "verified"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(json.loads(r.data)['relationship_id'], rel_id)

        r2 = self.client.get(f'/api/relationships/{rel_id}')
        self.assertEqual(r2.status_code, 200)
        data = json.loads(r2.data)
        self.assertEqual(data['state'], 'confirmed')
        self.assertEqual(data['note'], 'verified')

    def test_delete_goat_purge_removes_registry_entry(self):
        """DELETE /api/goats/<name>?purge=true removes registry entry and data dir"""
        goat_dir = os.path.join(self.test_dir, "purge_goat")
        os.makedirs(goat_dir, exist_ok=True)

        r = self.client.post('/api/goats', json={"name": "purge_test", "type": "text", "goat_path": goat_dir})
        self.assertEqual(r.status_code, 201)

        r = self.client.delete('/api/goats/purge_test?purge=true')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(json.loads(r.data)['purged'])

        goats = json.loads(self.client.get('/api/goats').data)['goats']
        self.assertFalse(any(g['name'] == 'purge_test' for g in goats))
        self.assertFalse(os.path.exists(goat_dir))

    def test_goat_summary_returns_counts(self):
        """GET /api/goats/<name>/summary returns node_count, rel_count, taxonomy"""
        import asyncio
        from mojogoat.goatbases.textgoat import TextGoat

        goat_dir = os.path.join(self.test_dir, "summary_goat")
        r = self.client.post('/api/goats', json={"name": "summary_test", "type": "text", "goat_path": goat_dir})
        self.assertEqual(r.status_code, 201)

        g = TextGoat({"goatpath": goat_dir, "goatname": "summary_test"})
        asyncio.run(g.add_node("a"))
        asyncio.run(g.add_node("b"))
        asyncio.run(g.create_relationship("a", "b", "KNOWS"))

        r = self.client.get('/api/goats/summary_test/summary')
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertEqual(data['node_count'], 2)
        self.assertEqual(data['rel_count'], 1)
        self.assertIn('KNOWS', data['taxonomy'])

    def test_post_backend_auto_excludes_falkordb_neo4j(self):
        """POST /api/backend with type=auto never probes FalkorDB or Neo4j (ADR-0010)"""
        r = self.client.post('/api/backend', json={
            "type": "auto",
            "goat_path": os.path.join(self.test_dir, "auto_goat"),
            "goat_name": "auto",
        })
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertIn(data['type'], ('text', 'memory'))
        self.assertNotIn(data['type'], ('falkordb', 'neo4j'))

    # ------------------------------------------------------------------
    # Item 12 — GET /api/graph (ADR-0011)
    # ------------------------------------------------------------------

    def test_get_graph_basic(self):
        """GET /api/graph returns nodes referenced by edges; orphan nodes excluded"""
        import asyncio
        import mojogoatapi
        from mojogoat.goatbases.memorygoat import MemoryGoat

        g = MemoryGoat()
        asyncio.run(g.add_node("a", labels=["Person"]))
        asyncio.run(g.add_node("b", labels=["Person"]))
        asyncio.run(g.add_node("c", labels=["Thing"]))  # orphan — no edges
        asyncio.run(g.create_relationship("a", "b", "KNOWS"))

        mojogoatapi.active_goat = g
        mojogoatapi.active_goat_name = "test_mem"

        r = self.client.get('/api/graph')
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)

        self.assertEqual(data['edge_count'], 1)
        self.assertEqual(data['node_count'], 2)
        node_ids = {n['nodeid'] for n in data['nodes']}
        self.assertIn('a', node_ids)
        self.assertIn('b', node_ids)
        self.assertNotIn('c', node_ids)

    def test_get_graph_story_filter(self):
        """GET /api/graph?story= filters edges by story"""
        import asyncio
        import mojogoatapi
        from mojogoat.goatbases.memorygoat import MemoryGoat

        g = MemoryGoat()
        asyncio.run(g.add_node("a"))
        asyncio.run(g.add_node("b"))
        asyncio.run(g.add_node("c"))
        asyncio.run(g.create_relationship("a", "b", "KNOWS"))
        asyncio.run(g.create_relationship("a", "c", "HATES"))

        mojogoatapi.active_goat = g
        mojogoatapi.active_goat_name = "test_mem"

        r = self.client.get('/api/graph?story=KNOWS')
        data = json.loads(r.data)
        self.assertEqual(data['edge_count'], 1)
        self.assertEqual(data['edges'][0]['story'], 'KNOWS')

    def test_get_graph_node_ids_subgraph(self):
        """GET /api/graph?node_ids= restricts to the specified subgraph"""
        import asyncio
        import mojogoatapi
        from mojogoat.goatbases.memorygoat import MemoryGoat

        g = MemoryGoat()
        asyncio.run(g.add_node("a"))
        asyncio.run(g.add_node("b"))
        asyncio.run(g.add_node("c"))
        asyncio.run(g.create_relationship("a", "b", "KNOWS"))
        asyncio.run(g.create_relationship("b", "c", "KNOWS"))

        mojogoatapi.active_goat = g
        mojogoatapi.active_goat_name = "test_mem"

        r = self.client.get('/api/graph?node_ids=a,b')
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertEqual(data['edge_count'], 1)  # only a→b; b→c excluded
        node_ids = {n['nodeid'] for n in data['nodes']}
        self.assertIn('a', node_ids)
        self.assertIn('b', node_ids)
        self.assertNotIn('c', node_ids)

    def test_get_graph_no_active_goat(self):
        """GET /api/graph returns 404 when no active goat"""
        r = self.client.get('/api/graph')
        self.assertEqual(r.status_code, 404)

    # ------------------------------------------------------------------
    # Item 13 — Operations API (ADR-0012)
    # ------------------------------------------------------------------

    def _setup_memory_goat(self):
        import asyncio
        import mojogoatapi
        from mojogoat.goatbases.memorygoat import MemoryGoat
        g = MemoryGoat()
        asyncio.run(g.add_node("x"))
        asyncio.run(g.add_node("y"))
        mojogoatapi.active_goat = g
        mojogoatapi.active_goat_name = "test_mem"
        return g

    def test_operations_create_and_get(self):
        """POST /api/operations creates with pending status; GET returns it"""
        r = self.client.post('/api/operations', json={"name": "label_prop", "node_ids": ["x"], "params": {}})
        self.assertEqual(r.status_code, 201)
        op = json.loads(r.data)
        self.assertEqual(op['status'], 'pending')
        self.assertEqual(op['name'], 'label_prop')
        op_id = op['operation_id']

        r2 = self.client.get(f'/api/operations/{op_id}')
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(json.loads(r2.data)['operation_id'], op_id)

    def test_operations_post_results_transitions_to_awaiting_validation(self):
        """POST /api/operations/<id>/results transitions status to awaiting_validation"""
        op_id = json.loads(
            self.client.post('/api/operations', json={"name": "op1", "node_ids": [], "params": {}}).data
        )['operation_id']

        r = self.client.post(f'/api/operations/{op_id}/results', json={
            "results": [{"type": "add_node", "payload": {"nodeid": "z", "labels": ["New"]}}]
        })
        self.assertEqual(r.status_code, 200)
        op = json.loads(r.data)
        self.assertEqual(op['status'], 'awaiting_validation')
        self.assertEqual(len(op['results']), 1)
        self.assertEqual(op['results'][0]['status'], 'proposed')

    def test_operations_accept_result_writes_to_goat(self):
        """Accepting a result executes the write and transitions op to completed"""
        import asyncio
        g = self._setup_memory_goat()

        op_id = json.loads(
            self.client.post('/api/operations', json={"name": "add_z", "node_ids": [], "params": {}}).data
        )['operation_id']
        result_id = json.loads(
            self.client.post(f'/api/operations/{op_id}/results', json={
                "results": [{"type": "add_node", "payload": {"nodeid": "z", "labels": ["New"]}}]
            }).data
        )['results'][0]['result_id']

        r = self.client.post(f'/api/operations/{op_id}/validate', json={"result_id": result_id, "action": "accept"})
        self.assertEqual(r.status_code, 200)
        op = json.loads(r.data)
        self.assertEqual(op['status'], 'completed')
        self.assertEqual(op['results'][0]['status'], 'accepted')

        node = asyncio.run(g.get_node("z"))
        self.assertIsNotNone(node)
        self.assertEqual(node.get('labels'), ['New'])

    def test_operations_reject_result_does_not_write(self):
        """Rejecting a result does not write to the goat"""
        import asyncio
        g = self._setup_memory_goat()

        op_id = json.loads(
            self.client.post('/api/operations', json={"name": "reject_op", "node_ids": [], "params": {}}).data
        )['operation_id']
        result_id = json.loads(
            self.client.post(f'/api/operations/{op_id}/results', json={
                "results": [{"type": "add_node", "payload": {"nodeid": "should_not_exist"}}]
            }).data
        )['results'][0]['result_id']

        r = self.client.post(f'/api/operations/{op_id}/validate', json={"result_id": result_id, "action": "reject"})
        self.assertEqual(r.status_code, 200)
        op = json.loads(r.data)
        self.assertEqual(op['results'][0]['status'], 'rejected')
        self.assertEqual(op['status'], 'completed')

        self.assertIsNone(asyncio.run(g.get_node("should_not_exist")))

    def test_operations_accept_add_relationship(self):
        """Accepting add_relationship result creates the relationship in the goat"""
        import asyncio
        g = self._setup_memory_goat()

        op_id = json.loads(
            self.client.post('/api/operations', json={"name": "link_op", "node_ids": [], "params": {}}).data
        )['operation_id']
        result_id = json.loads(
            self.client.post(f'/api/operations/{op_id}/results', json={
                "results": [{"type": "add_relationship", "payload": {"source": "x", "target": "y", "story": "CONNECTED"}}]
            }).data
        )['results'][0]['result_id']

        r = self.client.post(f'/api/operations/{op_id}/validate', json={"result_id": result_id, "action": "accept"})
        self.assertEqual(r.status_code, 200)

        rels = asyncio.run(g.get_relationships("x", "y", "CONNECTED"))
        self.assertEqual(len(rels), 1)

    def test_operations_delete(self):
        """DELETE /api/operations/<id> removes the operation"""
        op_id = json.loads(
            self.client.post('/api/operations', json={"name": "del_op", "node_ids": [], "params": {}}).data
        )['operation_id']

        r = self.client.delete(f'/api/operations/{op_id}')
        self.assertEqual(r.status_code, 200)

        r2 = self.client.get(f'/api/operations/{op_id}')
        self.assertEqual(r2.status_code, 404)

    def test_operations_missing_name_returns_400(self):
        """POST /api/operations without name returns 400"""
        r = self.client.post('/api/operations', json={"node_ids": []})
        self.assertEqual(r.status_code, 400)

    def test_operations_validate_bad_action_returns_400(self):
        """POST /api/operations/<id>/validate with unknown action returns 400"""
        self._setup_memory_goat()
        op_id = json.loads(
            self.client.post('/api/operations', json={"name": "x", "node_ids": [], "params": {}}).data
        )['operation_id']
        self.client.post(f'/api/operations/{op_id}/results', json={
            "results": [{"type": "add_node", "payload": {"nodeid": "q"}}]
        })
        result_id = json.loads(self.client.get(f'/api/operations/{op_id}').data)['results'][0]['result_id']

        r = self.client.post(f'/api/operations/{op_id}/validate', json={"result_id": result_id, "action": "maybe"})
        self.assertEqual(r.status_code, 400)

    # ------------------------------------------------------------------
    # Item 14 — TextGoat compaction (ADR-0007)
    # ------------------------------------------------------------------

    def test_compact_textgoat_preserves_rels_and_removes_old_snapshots(self):
        """POST /api/active-goat/compact preserves relationships and deletes orphaned snapshots"""
        import asyncio
        import mojogoatapi
        from mojogoat.goatbases.textgoat import TextGoat

        goat_dir = os.path.join(self.test_dir, "compact_goat")
        goat = TextGoat({"goatpath": goat_dir, "goatname": "compact"})
        asyncio.run(goat.add_node("a"))
        asyncio.run(goat.add_node("b"))
        asyncio.run(goat.create_relationship("a", "b", "KNOWS"))
        asyncio.run(goat.create_relationship("a", "b", "LIKES"))

        snapshots_dir = os.path.join(goat_dir, "snapshots")
        self.assertGreater(len(os.listdir(snapshots_dir)), 1)

        mojogoatapi.active_goat = goat
        mojogoatapi.active_goat_name = "compact"

        r = self.client.post('/api/active-goat/compact')
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertEqual(data['relationship_count'], 2)

        self.assertEqual(len(os.listdir(snapshots_dir)), 1)
        rels = asyncio.run(goat.get_relationships())
        self.assertEqual(len(rels), 2)

    def test_compact_non_textgoat_returns_400(self):
        """POST /api/active-goat/compact returns 400 for non-text backends"""
        import mojogoatapi
        from mojogoat.goatbases.memorygoat import MemoryGoat

        mojogoatapi.active_goat = MemoryGoat()
        mojogoatapi.active_goat_name = "mem"

        r = self.client.post('/api/active-goat/compact')
        self.assertEqual(r.status_code, 400)
        self.assertIn('text', json.loads(r.data)['error'])

    # ------------------------------------------------------------------
    # Item 15 — Bulk import (inverse of dump-relationships)
    # ------------------------------------------------------------------

    def test_import_relationships_round_trip(self):
        """dump → import into empty goat → verify count and content match"""
        import asyncio
        import mojogoatapi
        from mojogoat.goatbases.textgoat import TextGoat

        src_dir = os.path.join(self.test_dir, "src_goat")
        src = TextGoat({"goatpath": src_dir, "goatname": "src"})
        asyncio.run(src.add_node("a"))
        asyncio.run(src.add_node("b"))
        asyncio.run(src.create_relationship("a", "b", "KNOWS"))

        dump_file = os.path.join(self.test_dir, "dump.gq")
        asyncio.run(src.dump_all_rels(dump_file))

        dst_dir = os.path.join(self.test_dir, "dst_goat")
        dst = TextGoat({"goatpath": dst_dir, "goatname": "dst"})
        mojogoatapi.active_goat = dst
        mojogoatapi.active_goat_name = "dst"

        r = self.client.post('/api/active-goat/import-relationships', json={"filename": dump_file})
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertEqual(data['imported'], 1)
        self.assertEqual(data['skipped'], 0)
        self.assertEqual(data['errors'], [])

        rels = asyncio.run(dst.get_relationships())
        self.assertEqual(len(rels), 1)
        self.assertEqual(rels[0]['source_id'], 'a')
        self.assertEqual(rels[0]['target_id'], 'b')
        self.assertEqual(rels[0]['story'], 'KNOWS')

    def test_import_relationships_round_trip_preserves_props(self):
        """dump → import must not drop relationship_id or **props (regression for #16)"""
        import asyncio
        import mojogoatapi
        from mojogoat.goatbases.textgoat import TextGoat

        src_dir = os.path.join(self.test_dir, "src_props_goat")
        src = TextGoat({"goatpath": src_dir, "goatname": "src"})
        asyncio.run(src.add_node("a"))
        asyncio.run(src.add_node("b"))
        created = asyncio.run(
            src.create_relationship("a", "b", "KNOWS", smriti_state="confirmed", weight=3)
        )

        dump_file = os.path.join(self.test_dir, "dump_props.gq")
        asyncio.run(src.dump_all_rels(dump_file))

        dst_dir = os.path.join(self.test_dir, "dst_props_goat")
        dst = TextGoat({"goatpath": dst_dir, "goatname": "dst"})
        mojogoatapi.active_goat = dst
        mojogoatapi.active_goat_name = "dst"

        r = self.client.post('/api/active-goat/import-relationships', json={"filename": dump_file})
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertEqual(data['imported'], 1)
        self.assertEqual(data['errors'], [])

        rels = asyncio.run(dst.get_relationships())
        self.assertEqual(len(rels), 1)
        self.assertEqual(rels[0]['smriti_state'], 'confirmed')
        self.assertEqual(rels[0]['weight'], 3)
        # import-relationships creates a fresh relationship via create_relationship(),
        # so the destination gets its own goat-scoped ID rather than reusing the source's.
        self.assertNotEqual(rels[0]['relationship_id'], created['relationship_id'])

    def test_import_missing_filename_returns_400(self):
        """POST /api/active-goat/import-relationships without filename returns 400"""
        import mojogoatapi
        from mojogoat.goatbases.memorygoat import MemoryGoat

        mojogoatapi.active_goat = MemoryGoat()
        mojogoatapi.active_goat_name = "mem"

        r = self.client.post('/api/active-goat/import-relationships', json={})
        self.assertEqual(r.status_code, 400)

    def test_import_nonexistent_file_returns_400(self):
        """POST /api/active-goat/import-relationships with missing file returns 400"""
        import mojogoatapi
        from mojogoat.goatbases.memorygoat import MemoryGoat

        mojogoatapi.active_goat = MemoryGoat()
        mojogoatapi.active_goat_name = "mem"

        r = self.client.post('/api/active-goat/import-relationships', json={"filename": "/nonexistent/path.gq"})
        self.assertEqual(r.status_code, 400)
        self.assertIn('not found', json.loads(r.data)['error'])


if __name__ == '__main__':
    unittest.main()
