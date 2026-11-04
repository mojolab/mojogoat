#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the MojoGOAT API (goat-scoped API v2, ADR-016).

There is no "active goat": every data route is /api/goats/<goat>/... Tests that need a
pre-populated goat create it through POST /api/goats and then use the scoped routes (or reach
the server's instance with ApiEnv.cached_goat()).
New v2-only behaviour lives in test_api_v2.py.
"""

import json
import os
import unittest

import pytest

from api_support import ApiEnv, run


class MojoGoatAPITestCase(unittest.TestCase):
    """Test case for the MojoGOAT API"""

    def setUp(self):
        """Set up test environment"""
        self.env = ApiEnv().start()
        self.client = self.env.client
        self.test_dir = self.env.root
        self.registry_file = self.env.registry_file

    def tearDown(self):
        """Clean up test environment"""
        self.env.stop()

    def _memory_goat(self, name="test_mem", nodes=()):
        """Create a memory goat via the API and return the server's instance of it."""
        self.env.create_goat(name, "memory")
        g = self.env.cached_goat(name)
        for nodeid in nodes:
            run(g.add_node(nodeid))
        return g

    def test_list_goats_empty(self):
        """Test listing goats when the registry is empty"""
        response = self.client.get('/api/goats')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(len(data.get('goats', [])), 0)
        self.assertNotIn('default', data)
        self.assertNotIn('active', data)

    def test_create_text_goat(self):
        """Test creating a text goat"""
        goat_dir = os.path.join(self.test_dir, "test_text_goat")
        os.makedirs(goat_dir, exist_ok=True)

        data = {
            "name": "test_text_goat",
            "type": "text",
            "goat_path": goat_dir
        }

        response = self.client.post('/api/goats', json=data)
        self.assertEqual(response.status_code, 201)

        response = self.client.get('/api/goats')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(len(data.get('goats', [])), 1)
        self.assertEqual(data['goats'][0]['name'], "test_text_goat")
        self.assertEqual(data['goats'][0]['goatpath'], goat_dir)
        self.assertNotIn('default', data)
        self.assertNotIn('active', data)

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
            "config_path": config_path
        }

        response = self.client.post('/api/goats', json=data)
        self.assertEqual(response.status_code, 201)

        response = self.client.get('/api/goats')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(len(data.get('goats', [])), 1)
        self.assertEqual(data['goats'][0]['name'], "test_neo4j_goat")

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

    def test_get_goat_entry_among_several(self):
        """GET /api/goats/<name> addresses one goat of several (replaces 'set active goat')"""
        for name in ("test_goat1", "test_goat2"):
            response = self.client.post('/api/goats', json={
                "name": name,
                "type": "text",
                "goat_path": os.path.join(self.test_dir, name),
            })
            self.assertEqual(response.status_code, 201)

        for name in ("test_goat1", "test_goat2"):
            response = self.client.get(f'/api/goats/{name}')
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data['name'], name)
            self.assertEqual(data['goatpath'], os.path.join(self.test_dir, name))

        # Looking at goats does not select one: the list carries no active/default marker
        data = json.loads(self.client.get('/api/goats').data)
        self.assertEqual(len(data['goats']), 2)
        self.assertNotIn('default', data)
        self.assertNotIn('active', data)

    def test_error_unknown_goat(self):
        """Scoped routes return 404 for a goat that is not in the registry (was: no active goat)"""
        response = self.client.get('/api/goats/nope/nodes')
        self.assertEqual(response.status_code, 404)

        data = json.loads(response.data)
        self.assertEqual(data.get('error'), "Goat 'nope' not found")

        response = self.client.post('/api/goats/nope/nodes', json={"nodeid": "test_node"})
        self.assertEqual(response.status_code, 404)

        data = json.loads(response.data)
        self.assertEqual(data.get('error'), "Goat 'nope' not found")

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
        self.assertNotIn('active_goat', data)

    def test_health_reflects_goat_count(self):
        """Test that /health goat_count updates when goats are added"""
        r1 = self.client.get('/health')
        count_before = json.loads(r1.data)['goat_count']

        self.client.post('/api/goats', json={"name": "hgoat", "type": "text"})

        r2 = self.client.get('/health')
        self.assertEqual(json.loads(r2.data)['goat_count'], count_before + 1)

    def test_post_node_with_slash_returns_400(self):
        """Test that nodeids containing '/' return 400 with a useful message"""
        self._memory_goat()

        r = self.client.post('/api/goats/test_mem/nodes', json={"nodeid": "val:/some/path"})
        self.assertEqual(r.status_code, 400)
        data = json.loads(r.data)
        self.assertIn("nodeid", data["error"])
        self.assertIn("/", data["error"])

    def test_get_relationships_props_filter(self):
        """Test GET /api/goats/<goat>/relationships filters by arbitrary props and limit"""
        g = self._memory_goat(nodes=("a", "b", "c"))
        run(g.create_relationship("a", "b", "KNOWS", state="pending"))
        run(g.create_relationship("a", "c", "KNOWS", state="confirmed"))

        base = '/api/goats/test_mem/relationships'
        r = self.client.get(f'{base}?state=pending')
        self.assertEqual(r.status_code, 200)
        rels = json.loads(r.data)
        self.assertEqual(len(rels), 1)
        self.assertEqual(rels[0]['target_id'], 'b')

        r = self.client.get(f'{base}?target=c')
        self.assertEqual(r.status_code, 200)
        rels = json.loads(r.data)
        self.assertEqual(len(rels), 1)
        self.assertEqual(rels[0]['state'], 'confirmed')

        r = self.client.get(f'{base}?limit=1')
        self.assertEqual(r.status_code, 200)
        rels = json.loads(r.data)
        self.assertEqual(len(rels), 1)

        r = self.client.get(f'{base}?story=KNOWS&state=confirmed&target=c')
        self.assertEqual(r.status_code, 200)
        rels = json.loads(r.data)
        self.assertEqual(len(rels), 1)
        self.assertEqual(rels[0]['source_id'], 'a')

    def test_get_relationships_offset(self):
        """Test GET /api/goats/<goat>/relationships?offset=N paginates correctly"""
        g = self._memory_goat(nodes=("src",))
        for i in range(5):
            run(g.add_node(f"tgt{i}"))
            run(g.create_relationship("src", f"tgt{i}", "LINKED"))

        base = '/api/goats/test_mem/relationships'
        all_r = self.client.get(base)
        all_rels = json.loads(all_r.data)
        self.assertEqual(len(all_rels), 5)

        r = self.client.get(f'{base}?offset=2')
        paged = json.loads(r.data)
        self.assertEqual(len(paged), 3)
        self.assertEqual(paged[0]['relationship_id'], all_rels[2]['relationship_id'])

        r2 = self.client.get(f'{base}?offset=2&limit=2')
        paged2 = json.loads(r2.data)
        self.assertEqual(len(paged2), 2)

    # ------------------------------------------------------------------
    # Item 16 — API coverage gaps
    # ------------------------------------------------------------------

    def test_patch_relationship_updates_props(self):
        """PATCH /api/goats/<goat>/relationships/<id> merges props and returns 200"""
        g = self._memory_goat(nodes=("a", "b"))
        rel = run(g.create_relationship("a", "b", "KNOWS", state="pending"))
        rel_id = rel['relationship_id']

        base = '/api/goats/test_mem/relationships'
        r = self.client.patch(f'{base}/{rel_id}', json={"state": "confirmed", "note": "verified"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(json.loads(r.data)['relationship_id'], rel_id)

        r2 = self.client.get(f'{base}/{rel_id}')
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
        from mojogoat.goatbases.textgoat import TextGoat

        goat_dir = os.path.join(self.test_dir, "summary_goat")
        r = self.client.post('/api/goats', json={"name": "summary_test", "type": "text", "goat_path": goat_dir})
        self.assertEqual(r.status_code, 201)

        g = TextGoat({"goatpath": goat_dir, "goatname": "summary_test"})
        run(g.add_node("a"))
        run(g.add_node("b"))
        run(g.create_relationship("a", "b", "KNOWS"))

        r = self.client.get('/api/goats/summary_test/summary')
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertEqual(data['node_count'], 2)
        self.assertEqual(data['rel_count'], 1)
        self.assertIn('KNOWS', data['taxonomy'])

    # ------------------------------------------------------------------
    # Item 12 — GET /api/goats/<goat>/graph (ADR-011)
    # ------------------------------------------------------------------

    def test_get_graph_basic(self):
        """GET graph returns nodes referenced by edges; orphan nodes excluded"""
        g = self._memory_goat()
        run(g.add_node("a", labels=["Person"]))
        run(g.add_node("b", labels=["Person"]))
        run(g.add_node("c", labels=["Thing"]))  # orphan — no edges
        run(g.create_relationship("a", "b", "KNOWS"))

        r = self.client.get('/api/goats/test_mem/graph')
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)

        self.assertEqual(data['edge_count'], 1)
        self.assertEqual(data['node_count'], 2)
        node_ids = {n['nodeid'] for n in data['nodes']}
        self.assertIn('a', node_ids)
        self.assertIn('b', node_ids)
        self.assertNotIn('c', node_ids)

    def test_get_graph_story_filter(self):
        """GET graph?story= filters edges by story"""
        g = self._memory_goat(nodes=("a", "b", "c"))
        run(g.create_relationship("a", "b", "KNOWS"))
        run(g.create_relationship("a", "c", "HATES"))

        r = self.client.get('/api/goats/test_mem/graph?story=KNOWS')
        data = json.loads(r.data)
        self.assertEqual(data['edge_count'], 1)
        self.assertEqual(data['edges'][0]['story'], 'KNOWS')

    def test_get_graph_node_ids_subgraph(self):
        """GET graph?node_ids= restricts to the specified subgraph"""
        g = self._memory_goat(nodes=("a", "b", "c"))
        run(g.create_relationship("a", "b", "KNOWS"))
        run(g.create_relationship("b", "c", "KNOWS"))

        r = self.client.get('/api/goats/test_mem/graph?node_ids=a,b')
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertEqual(data['edge_count'], 1)  # only a→b; b→c excluded
        node_ids = {n['nodeid'] for n in data['nodes']}
        self.assertIn('a', node_ids)
        self.assertIn('b', node_ids)
        self.assertNotIn('c', node_ids)

    def test_get_graph_unknown_goat(self):
        """GET graph returns 404 for an unknown goat (was: no active goat)"""
        r = self.client.get('/api/goats/nope/graph')
        self.assertEqual(r.status_code, 404)

    # ------------------------------------------------------------------
    # Item 13 — Operations API (ADR-012), scoped per goat (ADR-016)
    # ------------------------------------------------------------------

    OPS = '/api/goats/test_mem/operations'

    def _setup_memory_goat(self):
        return self._memory_goat(nodes=("x", "y"))

    def test_operations_create_and_get(self):
        """POST operations creates with pending status; GET returns it"""
        self._setup_memory_goat()
        r = self.client.post(self.OPS, json={"name": "label_prop", "node_ids": ["x"], "params": {}})
        self.assertEqual(r.status_code, 201)
        op = json.loads(r.data)
        self.assertEqual(op['status'], 'pending')
        self.assertEqual(op['name'], 'label_prop')
        self.assertEqual(op['goat'], 'test_mem')
        op_id = op['operation_id']

        r2 = self.client.get(f'{self.OPS}/{op_id}')
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(json.loads(r2.data)['operation_id'], op_id)

    def test_operations_post_results_transitions_to_awaiting_validation(self):
        """POST operations/<id>/results transitions status to awaiting_validation"""
        self._setup_memory_goat()
        op_id = json.loads(
            self.client.post(self.OPS, json={"name": "op1", "node_ids": [], "params": {}}).data
        )['operation_id']

        r = self.client.post(f'{self.OPS}/{op_id}/results', json={
            "results": [{"type": "add_node", "payload": {"nodeid": "z", "labels": ["New"]}}]
        })
        self.assertEqual(r.status_code, 200)
        op = json.loads(r.data)
        self.assertEqual(op['status'], 'awaiting_validation')
        self.assertEqual(len(op['results']), 1)
        self.assertEqual(op['results'][0]['status'], 'proposed')

    def test_operations_accept_result_writes_to_goat(self):
        """Accepting a result executes the write and transitions op to completed"""
        g = self._setup_memory_goat()

        op_id = json.loads(
            self.client.post(self.OPS, json={"name": "add_z", "node_ids": [], "params": {}}).data
        )['operation_id']
        result_id = json.loads(
            self.client.post(f'{self.OPS}/{op_id}/results', json={
                "results": [{"type": "add_node", "payload": {"nodeid": "z", "labels": ["New"]}}]
            }).data
        )['results'][0]['result_id']

        r = self.client.post(f'{self.OPS}/{op_id}/validate', json={"result_id": result_id, "action": "accept"})
        self.assertEqual(r.status_code, 200)
        op = json.loads(r.data)
        self.assertEqual(op['status'], 'completed')
        self.assertEqual(op['results'][0]['status'], 'accepted')

        node = run(g.get_node("z"))
        self.assertIsNotNone(node)
        self.assertEqual(node.get('labels'), ['New'])

    def test_operations_reject_result_does_not_write(self):
        """Rejecting a result does not write to the goat"""
        g = self._setup_memory_goat()

        op_id = json.loads(
            self.client.post(self.OPS, json={"name": "reject_op", "node_ids": [], "params": {}}).data
        )['operation_id']
        result_id = json.loads(
            self.client.post(f'{self.OPS}/{op_id}/results', json={
                "results": [{"type": "add_node", "payload": {"nodeid": "should_not_exist"}}]
            }).data
        )['results'][0]['result_id']

        r = self.client.post(f'{self.OPS}/{op_id}/validate', json={"result_id": result_id, "action": "reject"})
        self.assertEqual(r.status_code, 200)
        op = json.loads(r.data)
        self.assertEqual(op['results'][0]['status'], 'rejected')
        self.assertEqual(op['status'], 'completed')

        self.assertIsNone(run(g.get_node("should_not_exist")))

    def test_operations_accept_add_relationship(self):
        """Accepting add_relationship result creates the relationship in the goat"""
        g = self._setup_memory_goat()

        op_id = json.loads(
            self.client.post(self.OPS, json={"name": "link_op", "node_ids": [], "params": {}}).data
        )['operation_id']
        result_id = json.loads(
            self.client.post(f'{self.OPS}/{op_id}/results', json={
                "results": [{"type": "add_relationship", "payload": {"source": "x", "target": "y", "story": "CONNECTED"}}]
            }).data
        )['results'][0]['result_id']

        r = self.client.post(f'{self.OPS}/{op_id}/validate', json={"result_id": result_id, "action": "accept"})
        self.assertEqual(r.status_code, 200)

        rels = run(g.get_relationships("x", "y", "CONNECTED"))
        self.assertEqual(len(rels), 1)

    def test_operations_delete(self):
        """DELETE operations/<id> removes the operation"""
        self._setup_memory_goat()
        op_id = json.loads(
            self.client.post(self.OPS, json={"name": "del_op", "node_ids": [], "params": {}}).data
        )['operation_id']

        r = self.client.delete(f'{self.OPS}/{op_id}')
        self.assertEqual(r.status_code, 200)

        r2 = self.client.get(f'{self.OPS}/{op_id}')
        self.assertEqual(r2.status_code, 404)

    def test_operations_missing_name_returns_400(self):
        """POST operations without name returns 400"""
        self._setup_memory_goat()
        r = self.client.post(self.OPS, json={"node_ids": []})
        self.assertEqual(r.status_code, 400)

    def test_operations_validate_bad_action_returns_400(self):
        """POST operations/<id>/validate with unknown action returns 400"""
        self._setup_memory_goat()
        op_id = json.loads(
            self.client.post(self.OPS, json={"name": "x", "node_ids": [], "params": {}}).data
        )['operation_id']
        self.client.post(f'{self.OPS}/{op_id}/results', json={
            "results": [{"type": "add_node", "payload": {"nodeid": "q"}}]
        })
        result_id = json.loads(self.client.get(f'{self.OPS}/{op_id}').data)['results'][0]['result_id']

        r = self.client.post(f'{self.OPS}/{op_id}/validate', json={"result_id": result_id, "action": "maybe"})
        self.assertEqual(r.status_code, 400)

    # ------------------------------------------------------------------
    # Item 14 — TextGoat compaction (ADR-007)
    # ------------------------------------------------------------------

    def test_compact_textgoat_preserves_rels_and_removes_old_snapshots(self):
        """POST /api/goats/<goat>/compact preserves relationships and deletes orphaned snapshots"""
        goat_dir = self.env.create_text_goat("compact")
        base = '/api/goats/compact'
        self.assertEqual(self.client.post(f'{base}/nodes', json={"nodeid": "a"}).status_code, 201)
        self.assertEqual(self.client.post(f'{base}/nodes', json={"nodeid": "b"}).status_code, 201)
        for story in ("KNOWS", "LIKES"):
            r = self.client.post(f'{base}/relationships',
                                 json={"source": "a", "target": "b", "story": story})
            self.assertEqual(r.status_code, 201)

        snapshots_dir = os.path.join(goat_dir, "snapshots")
        self.assertGreater(len(os.listdir(snapshots_dir)), 1)

        r = self.client.post(f'{base}/compact')
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertEqual(data['relationship_count'], 2)

        self.assertEqual(len(os.listdir(snapshots_dir)), 1)
        rels = json.loads(self.client.get(f'{base}/relationships').data)
        self.assertEqual(len(rels), 2)

    def test_compact_non_textgoat_returns_400(self):
        """POST /api/goats/<goat>/compact returns 400 for non-text backends"""
        self._memory_goat("mem")

        r = self.client.post('/api/goats/mem/compact')
        self.assertEqual(r.status_code, 400)
        self.assertIn('text', json.loads(r.data)['error'])

    # ------------------------------------------------------------------
    # Item 15 — Bulk import (inverse of dump-relationships)
    # ------------------------------------------------------------------

    def test_import_relationships_round_trip(self):
        """dump → import into empty goat → verify count and content match"""
        from mojogoat.goatbases.textgoat import TextGoat

        src_dir = os.path.join(self.test_dir, "src_goat")
        src = TextGoat({"goatpath": src_dir, "goatname": "src"})
        run(src.add_node("a"))
        run(src.add_node("b"))
        run(src.create_relationship("a", "b", "KNOWS"))

        dump_file = os.path.join(self.test_dir, "dump.gq")
        run(src.dump_all_rels(dump_file))

        self.env.create_text_goat("dst")

        r = self.client.post('/api/goats/dst/import-relationships', json={"filename": dump_file})
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertEqual(data['imported'], 1)
        self.assertEqual(data['skipped'], 0)
        self.assertEqual(data['errors'], [])

        rels = json.loads(self.client.get('/api/goats/dst/relationships').data)
        self.assertEqual(len(rels), 1)
        self.assertEqual(rels[0]['source_id'], 'a')
        self.assertEqual(rels[0]['target_id'], 'b')
        self.assertEqual(rels[0]['story'], 'KNOWS')

    def test_import_relationships_round_trip_preserves_props(self):
        """dump → import must not drop relationship_id or **props (regression for #16)"""
        from mojogoat.goatbases.textgoat import TextGoat

        src_dir = os.path.join(self.test_dir, "src_props_goat")
        src = TextGoat({"goatpath": src_dir, "goatname": "src"})
        run(src.add_node("a"))
        run(src.add_node("b"))
        created = run(
            src.create_relationship("a", "b", "KNOWS", smriti_state="confirmed", weight=3)
        )

        dump_file = os.path.join(self.test_dir, "dump_props.gq")
        run(src.dump_all_rels(dump_file))

        self.env.create_text_goat("dst")

        r = self.client.post('/api/goats/dst/import-relationships', json={"filename": dump_file})
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertEqual(data['imported'], 1)
        self.assertEqual(data['errors'], [])

        rels = json.loads(self.client.get('/api/goats/dst/relationships').data)
        self.assertEqual(len(rels), 1)
        self.assertEqual(rels[0]['smriti_state'], 'confirmed')
        self.assertEqual(rels[0]['weight'], 3)
        # import-relationships creates a fresh relationship via create_relationship(),
        # so the destination gets its own goat-scoped ID rather than reusing the source's.
        self.assertNotEqual(rels[0]['relationship_id'], created['relationship_id'])

    def test_import_missing_filename_returns_400(self):
        """POST /api/goats/<goat>/import-relationships without filename returns 400"""
        self._memory_goat("mem")

        r = self.client.post('/api/goats/mem/import-relationships', json={})
        self.assertEqual(r.status_code, 400)

    def test_import_nonexistent_file_returns_400(self):
        """POST /api/goats/<goat>/import-relationships with missing file returns 400"""
        self._memory_goat("mem")

        r = self.client.post('/api/goats/mem/import-relationships', json={"filename": "/nonexistent/path.gq"})
        self.assertEqual(r.status_code, 400)
        self.assertIn('not found', json.loads(r.data)['error'])

    def test_scoped_writes_follow_the_url_not_the_previous_request(self):
        """Writes land in the goat named in the URL (regression for #20, now structural).

        Replaces test_switching_active_goat_updates_routes_endpoints: there is nothing to
        switch any more, so alternate between two text goats and check each write's destination.
        """
        self.env.create_text_goat("goat_one")
        self.env.create_text_goat("goat_two")

        self.assertEqual(
            self.client.post('/api/goats/goat_one/nodes', json={"nodeid": "only_in_goat_one"}).status_code, 201
        )
        self.assertEqual(
            self.client.post('/api/goats/goat_two/nodes', json={"nodeid": "only_in_goat_two"}).status_code, 201
        )

        nodeids = {n['nodeid'] for n in json.loads(self.client.get('/api/goats/goat_two/nodes').data)}
        self.assertEqual(nodeids, {"only_in_goat_two"})

        nodeids = {n['nodeid'] for n in json.loads(self.client.get('/api/goats/goat_one/nodes').data)}
        self.assertEqual(nodeids, {"only_in_goat_one"})


class RoutesInjectedResolverTestCase(unittest.TestCase):
    """mojogoat.routes gets its goat resolver injected (ADR-016): no mojogoatapi import, no
    module-global goat. Replaces the old get_active_goat()/check_active_goat() unit tests
    (regression for #20, whose module-identity split can no longer occur)."""

    def test_init_routes_uses_the_injected_resolver(self):
        from flask import Flask
        from mojogoat import routes
        from mojogoat.errors import GoatNotFound
        from mojogoat.goatbases.memorygoat import MemoryGoat

        goats = {"g1": MemoryGoat()}
        run(goats["g1"].add_node("only_in_g1"))

        def resolver(name):
            if name not in goats:
                raise GoatNotFound(name)
            return goats[name]

        fresh = Flask(__name__)
        routes.init_routes(fresh, resolver)
        client = fresh.test_client()

        r = client.get('/api/goats/g1/nodes')
        self.assertEqual(r.status_code, 200)
        self.assertEqual([n['nodeid'] for n in r.get_json()], ["only_in_g1"])
        self.assertEqual(client.get('/api/goats/g2/nodes').status_code, 404)

    def test_active_goat_machinery_is_gone(self):
        import mojogoatapi
        from mojogoat import routes

        for attr in ("get_active_goat", "set_active_goat_ref", "check_active_goat",
                     "requires_active_goat"):
            self.assertFalse(hasattr(routes, attr), attr)
        for attr in ("active_goat", "active_goat_name", "set_active_goat"):
            self.assertFalse(hasattr(mojogoatapi, attr), attr)


if __name__ == '__main__':
    unittest.main()
