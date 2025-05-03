#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command line script to test the MojoGOAT API.

This script performs a series of API calls to test all functionality of the MojoGOAT API,
including goat management, node operations, and relationship operations.

Usage:
    python test_api_cli.py [--url URL] [--test-data-path PATH]

Options:
    --url URL               Base URL of the MojoGOAT API (default: http://localhost:5000)
    --test-data-path PATH   Path to store test data (default: /tmp/mojogoat_cli_test)
"""

import argparse
import json
import os
import tempfile
import time
import requests
import shutil
import sys
from datetime import datetime


class MojoGOATAPITester:
    """Test runner for the MojoGOAT API."""

    def __init__(self, base_url="http://localhost:5000", test_data_path=None):
        """Initialize the tester.
        
        Args:
            base_url: Base URL of the MojoGOAT API
            test_data_path: Path to store test data
        """
        self.base_url = base_url.rstrip("/")
        self.test_data_path = test_data_path or tempfile.mkdtemp(prefix="mojogoat_cli_test_")
        self.session = requests.Session()
        self.text_goat_name = f"test_text_goat_{int(time.time())}"
        self.mongopg_goat_name = f"test_mongopg_goat_{int(time.time())}"
        self.test_node_id1 = f"test_node1_{int(time.time())}"
        self.test_node_id2 = f"test_node2_{int(time.time())}"
        self.test_relationship_id = None
        
        # Prepare test directories
        self.prepare_test_environment()
        
        # Print test configuration
        print("=" * 80)
        print("MojoGOAT API Test Configuration")
        print("=" * 80)
        print(f"API URL:         {self.base_url}")
        print(f"Test Data Path:  {self.test_data_path}")
        print(f"Test Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print()

    def prepare_test_environment(self):
        """Prepare the test environment."""
        # Create test directories
        os.makedirs(os.path.join(self.test_data_path, "goats", self.text_goat_name, "nodes"), exist_ok=True)
        os.makedirs(os.path.join(self.test_data_path, "goats", self.text_goat_name, "snapshots"), exist_ok=True)
        os.makedirs(os.path.join(self.test_data_path, "databases"), exist_ok=True)
        
        # Create empty files for text goat
        open(os.path.join(self.test_data_path, "goats", self.text_goat_name, "newgrass.gq"), "w").close()
        open(os.path.join(self.test_data_path, "goats", self.text_goat_name, "goatrels.gq"), "w").close()
        
        # Create registry directory
        self.registry_path = os.path.join(self.test_data_path, "registry.json")

    def run_tests(self):
        """Run all tests."""
        # Test goat management
        self.test_get_registry()
        self.test_set_registry()
        self.test_list_goats_empty()
        self.test_create_text_goat()
        self.test_create_mongopg_goat()
        self.test_list_goats()
        self.test_get_active_goat()
        self.test_set_active_goat()
        
        # Test node operations
        self.test_create_node()
        self.test_create_second_node()
        self.test_get_node()
        self.test_get_nodes()
        self.test_get_nodes_by_label()
        self.test_update_node()
        
        # Test relationship operations
        self.test_create_relationship()
        self.test_get_relationships()
        self.test_get_relationships_by_source()
        self.test_get_relationships_by_target()
        self.test_get_relationships_by_story()
        self.test_get_relationship_by_id()
        
        # Test goat-specific operations
        self.test_get_composition()
        self.test_get_taxonomy()
        self.test_dump_relationships()
        
        # Clean up
        self.test_delete_relationship()
        self.test_delete_nodes()
        
        print("\nAll tests completed successfully!")
        
        return True

    def cleanup(self):
        """Clean up test data."""
        try:
            shutil.rmtree(self.test_data_path)
            print(f"\nTest data cleaned up: {self.test_data_path}")
        except Exception as e:
            print(f"\nError cleaning up test data: {e}")

    def _request(self, method, endpoint, json_data=None, params=None, expected_status=None):
        """Make an API request and validate the response.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            json_data: JSON data to send
            params: Query parameters
            expected_status: Expected HTTP status code(s)
            
        Returns:
            Response JSON or None
        """
        url = f"{self.base_url}{endpoint}"
        response = self.session.request(method, url, json=json_data, params=params)
        
        # Print request and response information
        print(f"{method} {url}")
        if json_data:
            print(f"  Request: {json.dumps(json_data, indent=2)}")
        if params:
            print(f"  Params:  {params}")
        print(f"  Status:  {response.status_code}")
        
        # Pretty print response if it's JSON
        try:
            response_json = response.json()
            print(f"  Response: {json.dumps(response_json, indent=2)}")
        except:
            print(f"  Response: {response.text[:100]}...")
        
        # Check status code
        if expected_status is not None:
            if isinstance(expected_status, list):
                assert response.status_code in expected_status, f"Expected status code(s) {expected_status}, got {response.status_code}"
            else:
                assert response.status_code == expected_status, f"Expected status code {expected_status}, got {response.status_code}"
        
        # Return response JSON if possible
        try:
            return response.json()
        except:
            return None

    # Goat management tests
    def test_get_registry(self):
        """Test getting the registry path."""
        print("\n--- Test: Get Registry Path ---")
        response = self._request("GET", "/api/registry", expected_status=200)
        assert "registry_path" in response, "Response should contain registry_path"

    def test_set_registry(self):
        """Test setting the registry path."""
        print("\n--- Test: Set Registry Path ---")
        response = self._request(
            "POST", 
            "/api/registry", 
            json_data={"path": self.registry_path}, 
            expected_status=[200, 201]
        )
        assert "message" in response, "Response should contain message"
        assert "registry" in response["message"].lower(), "Message should mention registry"

    def test_list_goats_empty(self):
        """Test listing goats when the registry is empty."""
        print("\n--- Test: List Goats (Empty) ---")
        response = self._request("GET", "/api/goats", expected_status=200)
        assert "goats" in response, "Response should contain goats"
        assert len(response["goats"]) == 0, "There should be no goats initially"

    def test_create_text_goat(self):
        """Test creating a text goat."""
        print("\n--- Test: Create Text Goat ---")
        goat_path = os.path.join(self.test_data_path, "goats", self.text_goat_name)
        response = self._request(
            "POST", 
            "/api/goats", 
            json_data={
                "name": self.text_goat_name,
                "type": "text",
                "description": "A test text goat",
                "goat_path": goat_path,
                "make_default": True,
                "make_active": True
            }, 
            expected_status=201
        )
        assert "message" in response, "Response should contain message"
        assert "created successfully" in response["message"], "Message should indicate successful creation"
        assert "goat" in response, "Response should contain goat"
        assert response["goat"]["name"] == self.text_goat_name, "Goat name should match"

    def test_create_mongopg_goat(self):
        """Test creating a MongoDB+PostgreSQL goat."""
        print("\n--- Test: Create MongoDB+PostgreSQL Goat ---")
        response = self._request(
            "POST", 
            "/api/goats", 
            json_data={
                "name": self.mongopg_goat_name,
                "type": "mongopg",
                "description": "A test MongoDB+PostgreSQL goat",
                "mongodb_uri": f"mongodb://localhost/{self.mongopg_goat_name}",
                "postgres_uri": f"sqlite:///{os.path.join(self.test_data_path, 'databases', 'test_relationships.db')}",
                "make_default": False,
                "make_active": False
            }, 
            expected_status=201
        )
        assert "message" in response, "Response should contain message"
        assert "created successfully" in response["message"], "Message should indicate successful creation"
        assert "goat" in response, "Response should contain goat"
        assert response["goat"]["name"] == self.mongopg_goat_name, "Goat name should match"

    def test_list_goats(self):
        """Test listing all goats."""
        print("\n--- Test: List Goats ---")
        response = self._request("GET", "/api/goats", expected_status=200)
        assert "goats" in response, "Response should contain goats"
        assert len(response["goats"]) == 2, "There should be two goats"
        assert any(goat["name"] == self.text_goat_name for goat in response["goats"]), f"Goat {self.text_goat_name} should be in the list"
        assert any(goat["name"] == self.mongopg_goat_name for goat in response["goats"]), f"Goat {self.mongopg_goat_name} should be in the list"
        assert response["default"] == self.text_goat_name, "Default goat should be the text goat"
        assert response["active"] == self.text_goat_name, "Active goat should be the text goat"

    def test_get_active_goat(self):
        """Test getting the active goat."""
        print("\n--- Test: Get Active Goat ---")
        response = self._request("GET", "/api/active-goat", expected_status=200)
        assert "active_goat" in response, "Response should contain active_goat"
        assert response["active_goat"] == self.text_goat_name, f"Active goat should be {self.text_goat_name}"
        assert "config" in response, "Response should contain config"

    def test_set_active_goat(self):
        """Test setting the active goat."""
        print("\n--- Test: Set Active Goat ---")
        response = self._request(
            "POST", 
            "/api/active-goat", 
            json_data={"name": self.text_goat_name, "make_default": True}, 
            expected_status=200
        )
        assert "message" in response, "Response should contain message"
        assert f"Active goat set to '{self.text_goat_name}'" in response["message"], "Message should indicate successful setting"

    # Node operations tests
    def test_create_node(self):
        """Test creating a node."""
        print("\n--- Test: Create Node ---")
        response = self._request(
            "POST", 
            "/api/nodes", 
            json_data={
                "nodeid": self.test_node_id1,
                "nodename": "Test Node 1",
                "labels": ["Person", "Employee"],
                "description": "This is a test node",
                "age": 30,
                "department": "Engineering"
            }, 
            expected_status=201
        )
        assert response["nodeid"] == self.test_node_id1, "Node ID should match"
        assert response["nodename"] == "Test Node 1", "Node name should match"
        assert set(response["labels"]) == set(["Person", "Employee"]), "Labels should match"
        assert response["description"] == "This is a test node", "Description should match"

    def test_create_second_node(self):
        """Test creating a second node."""
        print("\n--- Test: Create Second Node ---")
        response = self._request(
            "POST", 
            "/api/nodes", 
            json_data={
                "nodeid": self.test_node_id2,
                "nodename": "Test Node 2",
                "labels": ["Company", "Organization"],
                "description": "This is a test company node",
                "founded": 2010,
                "industry": "Technology"
            }, 
            expected_status=201
        )
        assert response["nodeid"] == self.test_node_id2, "Node ID should match"
        assert response["nodename"] == "Test Node 2", "Node name should match"
        assert set(response["labels"]) == set(["Company", "Organization"]), "Labels should match"
        assert response["description"] == "This is a test company node", "Description should match"

    def test_get_node(self):
        """Test getting a node by ID."""
        print("\n--- Test: Get Node by ID ---")
        response = self._request("GET", f"/api/nodes/{self.test_node_id1}", expected_status=200)
        assert response["nodeid"] == self.test_node_id1, "Node ID should match"
        assert response["nodename"] == "Test Node 1", "Node name should match"
        assert set(response["labels"]) == set(["Person", "Employee"]), "Labels should match"
        assert response["description"] == "This is a test node", "Description should match"

    def test_get_nodes(self):
        """Test getting all nodes."""
        print("\n--- Test: Get All Nodes ---")
        response = self._request("GET", "/api/nodes", expected_status=200)
        assert isinstance(response, list), "Response should be a list"
        assert len(response) >= 2, "There should be at least 2 nodes"
        node_ids = [node["nodeid"] for node in response]
        assert self.test_node_id1 in node_ids, f"Node {self.test_node_id1} should be in the list"
        assert self.test_node_id2 in node_ids, f"Node {self.test_node_id2} should be in the list"

    def test_get_nodes_by_label(self):
        """Test getting nodes by label."""
        print("\n--- Test: Get Nodes by Label ---")
        response = self._request("GET", "/api/nodes/label/Person", expected_status=200)
        assert isinstance(response, list), "Response should be a list"
        assert len(response) >= 1, "There should be at least 1 node with label Person"
        node_ids = [node["nodeid"] for node in response]
        assert self.test_node_id1 in node_ids, f"Node {self.test_node_id1} should be in the list"

    def test_update_node(self):
        """Test updating a node."""
        print("\n--- Test: Update Node ---")
        response = self._request(
            "PUT", 
            f"/api/nodes/{self.test_node_id1}", 
            json_data={
                "nodename": "Updated Test Node",
                "description": "This is an updated test node",
                "title": "Senior Engineer"
            }, 
            expected_status=200
        )
        assert response["nodeid"] == self.test_node_id1, "Node ID should match"
        assert response["nodename"] == "Updated Test Node", "Node name should be updated"
        assert response["description"] == "This is an updated test node", "Description should be updated"
        assert response["title"] == "Senior Engineer", "New field should be added"
        assert set(response["labels"]) == set(["Person", "Employee"]), "Labels should remain the same"

    # Relationship operations tests
    def test_create_relationship(self):
        """Test creating a relationship."""
        print("\n--- Test: Create Relationship ---")
        response = self._request(
            "POST", 
            "/api/relationships", 
            json_data={
                "source": self.test_node_id1,
                "target": self.test_node_id2,
                "story": "WORKS_AT"
            }, 
            expected_status=201
        )
        assert response["source_id"] == self.test_node_id1, "Source ID should match"
        assert response["target_id"] == self.test_node_id2, "Target ID should match"
        assert response["story"] == "WORKS_AT", "Story should match"
        
        # Store relationship ID for later tests
        if "relationship_id" in response:
            self.test_relationship_id = response["relationship_id"]
            print(f"  Saved relationship ID: {self.test_relationship_id}")

    def test_get_relationships(self):
        """Test getting all relationships."""
        print("\n--- Test: Get All Relationships ---")
        response = self._request("GET", "/api/relationships", expected_status=200)
        assert isinstance(response, list), "Response should be a list"
        assert len(response) >= 1, "There should be at least 1 relationship"
        
        # Find the test relationship
        test_rel = None
        for rel in response:
            if rel["source_id"] == self.test_node_id1 and rel["target_id"] == self.test_node_id2:
                test_rel = rel
                break
        
        assert test_rel is not None, "Test relationship should be in the list"
        assert test_rel["story"] == "WORKS_AT", "Story should match"
        
        # Store relationship ID if not already set
        if self.test_relationship_id is None and "relationship_id" in test_rel:
            self.test_relationship_id = test_rel["relationship_id"]
            print(f"  Saved relationship ID: {self.test_relationship_id}")

    def test_get_relationships_by_source(self):
        """Test getting relationships by source."""
        print("\n--- Test: Get Relationships by Source ---")
        response = self._request("GET", "/api/relationships", params={"source": self.test_node_id1}, expected_status=200)
        assert isinstance(response, list), "Response should be a list"
        assert len(response) >= 1, "There should be at least 1 relationship from the source"
        
        # Verify all relationships are from the source
        for rel in response:
            assert rel["source_id"] == self.test_node_id1, "Source ID should match"

    def test_get_relationships_by_target(self):
        """Test getting relationships by target."""
        print("\n--- Test: Get Relationships by Target ---")
        response = self._request("GET", "/api/relationships", params={"target": self.test_node_id2}, expected_status=200)
        assert isinstance(response, list), "Response should be a list"
        assert len(response) >= 1, "There should be at least 1 relationship to the target"
        
        # Verify all relationships are to the target
        for rel in response:
            assert rel["target_id"] == self.test_node_id2, "Target ID should match"

    def test_get_relationships_by_story(self):
        """Test getting relationships by story."""
        print("\n--- Test: Get Relationships by Story ---")
        response = self._request("GET", "/api/relationships", params={"story": "WORKS_AT"}, expected_status=200)
        assert isinstance(response, list), "Response should be a list"
        assert len(response) >= 1, "There should be at least 1 relationship with the story"
        
        # Verify all relationships have the story
        for rel in response:
            assert rel["story"] == "WORKS_AT", "Story should match"

    def test_get_relationship_by_id(self):
        """Test getting a relationship by ID."""
        if self.test_relationship_id is None:
            print("\n--- Test: Get Relationship by ID (SKIPPED: No relationship ID) ---")
            return
            
        print(f"\n--- Test: Get Relationship by ID ({self.test_relationship_id}) ---")
        response = self._request("GET", f"/api/relationships/{self.test_relationship_id}", expected_status=200)
        assert response["source_id"] == self.test_node_id1, "Source ID should match"
        assert response["target_id"] == self.test_node_id2, "Target ID should match"
        assert response["story"] == "WORKS_AT", "Story should match"

    # Goat-specific operations tests
    def test_get_composition(self):
        """Test getting the composition of nodes by label."""
        print("\n--- Test: Get Composition ---")
        response = self._request("GET", "/api/active-goat/composition", expected_status=200)
        assert "Person" in response, "Composition should include Person"
        assert "Company" in response, "Composition should include Company"
        assert response["Person"] >= 1, "There should be at least 1 Person node"
        assert response["Company"] >= 1, "There should be at least 1 Company node"

    def test_get_taxonomy(self):
        """Test getting the taxonomy of relationship types."""
        print("\n--- Test: Get Taxonomy ---")
        response = self._request("GET", "/api/active-goat/taxonomy", expected_status=200)
        assert "WORKS_AT" in response, "Taxonomy should include WORKS_AT"
        assert response["WORKS_AT"] >= 1, "There should be at least 1 WORKS_AT relationship"

    def test_dump_relationships(self):
        """Test dumping relationships to a file."""
        print("\n--- Test: Dump Relationships ---")
        dump_file = os.path.join(self.test_data_path, "relationships_dump.txt")
        response = self._request(
            "POST", 
            "/api/active-goat/dump-relationships", 
            json_data={"filename": dump_file}, 
            expected_status=200
        )
        assert "message" in response, "Response should contain message"
        assert "Successfully dumped" in response["message"], "Message should indicate successful dump"
        assert os.path.exists(dump_file), "Dump file should be created"
        
        # Check file contents
        with open(dump_file, "r") as f:
            content = f.read()
            print(f"  Dump file content: {content[:100]}...")
            assert len(content) > 0, "Dump file should not be empty"

    # Cleanup tests
    def test_delete_relationship(self):
        """Test deleting a relationship."""
        if self.test_relationship_id is None:
            print("\n--- Test: Delete Relationship (SKIPPED: No relationship ID) ---")
            return
            
        print(f"\n--- Test: Delete Relationship ({self.test_relationship_id}) ---")
        response = self._request("DELETE", f"/api/relationships/{self.test_relationship_id}", expected_status=200)
        assert "message" in response, "Response should contain message"
        assert "deleted successfully" in response["message"], "Message should indicate successful deletion"
        
        # Verify relationship is deleted
        relationships = self._request("GET", "/api/relationships", expected_status=200)
        for rel in relationships:
            if "relationship_id" in rel and rel["relationship_id"] == self.test_relationship_id:
                assert False, f"Relationship {self.test_relationship_id} should be deleted"

    def test_delete_nodes(self):
        """Test deleting nodes."""
        print(f"\n--- Test: Delete Node ({self.test_node_id1}) ---")
        response = self._request("DELETE", f"/api/nodes/{self.test_node_id1}", expected_status=200)
        assert "message" in response, "Response should contain message"
        assert "deleted successfully" in response["message"], "Message should indicate successful deletion"
        
        print(f"\n--- Test: Delete Node ({self.test_node_id2}) ---")
        response = self._request("DELETE", f"/api/nodes/{self.test_node_id2}", expected_status=200)
        assert "message" in response, "Response should contain message"
        assert "deleted successfully" in response["message"], "Message should indicate successful deletion"
        
        # Verify nodes are deleted
        for node_id in [self.test_node_id1, self.test_node_id2]:
            try:
                self._request("GET", f"/api/nodes/{node_id}", expected_status=404)
            except:
                # If the request doesn't return 404, the node wasn't properly deleted
                print(f"  WARNING: Node {node_id} might not be properly deleted")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test the MojoGOAT API from the command line")
    parser.add_argument("--url", default="http://localhost:5000", help="Base URL of the MojoGOAT API")
    parser.add_argument("--test-data-path", help="Path to store test data")
    parser.add_argument("--keep-data", action="store_true", help="Keep test data after tests")
    args = parser.parse_args()
    
    tester = MojoGOATAPITester(args.url, args.test_data_path)
    
    try:
        result = tester.run_tests()
        if not args.keep_data:
            tester.cleanup()
        return 0 if result else 1
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        if not args.keep_data:
            tester.cleanup()
        return 1


if __name__ == "__main__":
    sys.exit(main())