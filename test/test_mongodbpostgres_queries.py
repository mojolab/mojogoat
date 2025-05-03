#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for MongoDB+Postgres advanced querying operations
"""

import json
import os
import sys
import unittest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mongoengine import MongoEngine
import uuid
from sqlalchemy import or_, and_, func
from datetime import datetime, timedelta

sys.path.append("/xpal-src/mojogoat")
from mojogoat.goatbases.mongogoat.models import Node, Relationship, sqldb

class TestMongoDBPostgresQueries(unittest.TestCase):
    """Test MongoDB+Postgres advanced query operations"""
    
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
        
        # Create test data
        cls.setup_test_data()
    
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
                query_prefix = "test_query_"
                Relationship.query.filter(
                    or_(
                        Relationship.source_id.like(f"{query_prefix}%"),
                        Relationship.target_id.like(f"{query_prefix}%")
                    )
                ).delete()
                sqldb.session.commit()
            except Exception as e:
                print(f"Error deleting relationships: {e}")
                sqldb.session.rollback()
            
            # Delete test nodes
            try:
                Node.objects(nodeid__startswith=query_prefix).delete()
            except Exception as e:
                print(f"Error deleting nodes: {e}")
    
    @classmethod
    def setup_test_data(cls):
        """Set up test data for query tests"""
        prefix = "test_query_"
        
        # Create person nodes
        cls.person1 = Node(
            nodeid=f"{prefix}person1",
            nodename="Query Person 1",
            labels=["Person", "Employee"],
            department="Engineering",
            years_experience=5
        ).save()
        
        cls.person2 = Node(
            nodeid=f"{prefix}person2",
            nodename="Query Person 2",
            labels=["Person", "Manager"],
            department="Engineering",
            years_experience=10
        ).save()
        
        cls.person3 = Node(
            nodeid=f"{prefix}person3",
            nodename="Query Person 3",
            labels=["Person", "Employee"],
            department="Marketing",
            years_experience=3
        ).save()
        
        # Create company nodes
        cls.company1 = Node(
            nodeid=f"{prefix}company1",
            nodename="Query Company 1",
            labels=["Company", "Organization"],
            industry="Technology",
            founded=2010
        ).save()
        
        cls.company2 = Node(
            nodeid=f"{prefix}company2",
            nodename="Query Company 2",
            labels=["Company", "Organization"],
            industry="Healthcare",
            founded=2015
        ).save()
        
        # Create project nodes
        cls.project1 = Node(
            nodeid=f"{prefix}project1",
            nodename="Query Project 1",
            labels=["Project"],
            status="Active",
            priority="High"
        ).save()
        
        cls.project2 = Node(
            nodeid=f"{prefix}project2",
            nodename="Query Project 2",
            labels=["Project"],
            status="Completed",
            priority="Medium"
        ).save()
        
        cls.project3 = Node(
            nodeid=f"{prefix}project3",
            nodename="Query Project 3",
            labels=["Project"],
            status="Planning",
            priority="Low"
        ).save()
        
        # Create relationships
        # Person to Company relationships
        now = datetime.now()
        
        # Person1 works at Company1
        rel1 = Relationship(
            source_id=f"{prefix}person1",
            target_id=f"{prefix}company1",
            story="WORKS_AT",
            timestamp=now - timedelta(days=365)
        )
        sqldb.session.add(rel1)
        
        # Person2 works at Company1 and manages Person1
        rel2 = Relationship(
            source_id=f"{prefix}person2",
            target_id=f"{prefix}company1",
            story="WORKS_AT",
            timestamp=now - timedelta(days=730)
        )
        sqldb.session.add(rel2)
        
        rel3 = Relationship(
            source_id=f"{prefix}person2",
            target_id=f"{prefix}person1",
            story="MANAGES",
            timestamp=now - timedelta(days=180)
        )
        sqldb.session.add(rel3)
        
        # Person3 works at Company2
        rel4 = Relationship(
            source_id=f"{prefix}person3",
            target_id=f"{prefix}company2",
            story="WORKS_AT",
            timestamp=now - timedelta(days=90)
        )
        sqldb.session.add(rel4)
        
        # Project relationships
        # Person1 works on Project1 and Project2
        rel5 = Relationship(
            source_id=f"{prefix}person1",
            target_id=f"{prefix}project1",
            story="WORKS_ON",
            timestamp=now - timedelta(days=60)
        )
        sqldb.session.add(rel5)
        
        rel6 = Relationship(
            source_id=f"{prefix}person1",
            target_id=f"{prefix}project2",
            story="WORKS_ON",
            timestamp=now - timedelta(days=120)
        )
        sqldb.session.add(rel6)
        
        # Person2 leads Project1
        rel7 = Relationship(
            source_id=f"{prefix}person2",
            target_id=f"{prefix}project1",
            story="LEADS",
            timestamp=now - timedelta(days=60)
        )
        sqldb.session.add(rel7)
        
        # Person3 works on Project3
        rel8 = Relationship(
            source_id=f"{prefix}person3",
            target_id=f"{prefix}project3",
            story="WORKS_ON",
            timestamp=now - timedelta(days=30)
        )
        sqldb.session.add(rel8)
        
        # Company sponsors projects
        rel9 = Relationship(
            source_id=f"{prefix}company1",
            target_id=f"{prefix}project1",
            story="SPONSORS",
            timestamp=now - timedelta(days=60)
        )
        sqldb.session.add(rel9)
        
        rel10 = Relationship(
            source_id=f"{prefix}company1",
            target_id=f"{prefix}project2",
            story="SPONSORS",
            timestamp=now - timedelta(days=120)
        )
        sqldb.session.add(rel10)
        
        rel11 = Relationship(
            source_id=f"{prefix}company2",
            target_id=f"{prefix}project3",
            story="SPONSORS",
            timestamp=now - timedelta(days=30)
        )
        sqldb.session.add(rel11)
        
        sqldb.session.commit()
    
    def test_01_query_nodes_by_custom_property(self):
        """Test querying nodes by custom property"""
        # Query engineers
        engineers = Node.objects(department="Engineering").all()
        
        # Verify query results
        self.assertEqual(len(engineers), 2)
        
        # Get node IDs
        engineer_ids = [node.nodeid for node in engineers]
        
        # Verify specific nodes are in the results
        self.assertIn("test_query_person1", engineer_ids)
        self.assertIn("test_query_person2", engineer_ids)
        self.assertNotIn("test_query_person3", engineer_ids)
    
    def test_02_query_nodes_by_numeric_comparison(self):
        """Test querying nodes by numeric comparison"""
        # Query experienced employees (>5 years)
        experienced = Node.objects(years_experience__gte=5).all()
        
        # Verify query results
        self.assertEqual(len(experienced), 2)
        
        # Get node IDs
        experienced_ids = [node.nodeid for node in experienced]
        
        # Verify specific nodes are in the results
        self.assertIn("test_query_person1", experienced_ids)
        self.assertIn("test_query_person2", experienced_ids)
        self.assertNotIn("test_query_person3", experienced_ids)
    
    def test_03_query_relationships_by_timestamp(self):
        """Test querying relationships by timestamp"""
        # Clean up existing relationships first
        Relationship.query.delete()
        sqldb.session.commit()
        
        # Create test relationships with specific timestamps
        prefix = "test_query_"
        now = datetime.now()
        
        # Create older relationship (120 days ago)
        old_rel = Relationship(
            source_id=f"{prefix}old_source",
            target_id=f"{prefix}old_target",
            story="OLD_REL",
            timestamp=now - timedelta(days=120)
        )
        
        # Create recent relationships (30 days ago)
        recent_rel1 = Relationship(
            source_id=f"{prefix}person1",
            target_id=f"{prefix}project1",
            story="WORKS_ON",
            timestamp=now - timedelta(days=30)
        )
        
        recent_rel2 = Relationship(
            source_id=f"{prefix}person3",
            target_id=f"{prefix}project3",
            story="WORKS_ON",
            timestamp=now - timedelta(days=20)
        )
        
        recent_rel3 = Relationship(
            source_id=f"{prefix}company2",
            target_id=f"{prefix}project3",
            story="SPONSORS",
            timestamp=now - timedelta(days=10)
        )
        
        sqldb.session.add(old_rel)
        sqldb.session.add(recent_rel1)
        sqldb.session.add(recent_rel2)
        sqldb.session.add(recent_rel3)
        sqldb.session.commit()
        
        # Query relationships created in the last 100 days
        cutoff_date = now - timedelta(days=100)
        
        recent_rels = Relationship.query.filter(
            Relationship.timestamp >= cutoff_date
        ).all()
        
        # Verify query results
        self.assertEqual(len(recent_rels), 3, f"Expected 3 recent relationships, got {len(recent_rels)}")
        
        # Get relationship stories
        recent_stories = [(rel.source_id, rel.story, rel.target_id) for rel in recent_rels]
        
        # Verify specific relationships are in the results
        self.assertIn((f"{prefix}person1", "WORKS_ON", f"{prefix}project1"), recent_stories)
        self.assertIn((f"{prefix}person3", "WORKS_ON", f"{prefix}project3"), recent_stories)
        self.assertIn((f"{prefix}company2", "SPONSORS", f"{prefix}project3"), recent_stories)
    
    def test_04_query_company_projects(self):
        """Test querying projects sponsored by a company"""
        # Clean up existing data
        Relationship.query.delete()
        sqldb.session.commit()
        
        prefix = "test_query_"
        company1_id = f"{prefix}company1"
        project1_id = f"{prefix}project1"
        project2_id = f"{prefix}project2"
        project3_id = f"{prefix}project3"
        
        # Create test relationships
        rel1 = Relationship(
            source_id=company1_id,
            target_id=project1_id,
            story="SPONSORS",
            timestamp=datetime.now()
        )
        
        rel2 = Relationship(
            source_id=company1_id,
            target_id=project2_id,
            story="SPONSORS",
            timestamp=datetime.now()
        )
        
        rel3 = Relationship(
            source_id=f"{prefix}company2",
            target_id=project3_id,
            story="SPONSORS",
            timestamp=datetime.now()
        )
        
        sqldb.session.add(rel1)
        sqldb.session.add(rel2)
        sqldb.session.add(rel3)
        sqldb.session.commit()
        
        # Query relationships where company1 is the source and story is SPONSORS
        company_projects = Relationship.query.filter(
            and_(
                Relationship.source_id == company1_id,
                Relationship.story == "SPONSORS"
            )
        ).all()
        
        # Verify query results
        self.assertEqual(len(company_projects), 2, f"Expected 2 company projects, got {len(company_projects)}")
        
        # Get project IDs
        project_ids = [rel.target_id for rel in company_projects]
        
        # Verify specific projects are in the results
        self.assertIn(project1_id, project_ids)
        self.assertIn(project2_id, project_ids)
        self.assertNotIn(project3_id, project_ids)
    
    def test_05_query_employees_by_manager(self):
        """Test querying employees managed by a specific manager"""
        manager_id = "test_query_person2"
        
        # Query relationships where manager is the source and story is MANAGES
        managed_rels = Relationship.query.filter(
            and_(
                Relationship.source_id == manager_id,
                Relationship.story == "MANAGES"
            )
        ).all()
        
        # Verify query results
        self.assertEqual(len(managed_rels), 1)
        
        # Get employee IDs
        employee_ids = [rel.target_id for rel in managed_rels]
        
        # Verify specific employees are in the results
        self.assertIn("test_query_person1", employee_ids)
    
    def test_06_query_node_by_label_and_property(self):
        """Test querying nodes by label and property"""
        # Query active projects
        active_projects = Node.objects(
            labels__contains="Project",
            status="Active"
        ).all()
        
        # Verify query results
        self.assertEqual(len(active_projects), 1)
        
        # Get project IDs
        project_ids = [node.nodeid for node in active_projects]
        
        # Verify specific projects are in the results
        self.assertIn("test_query_project1", project_ids)
        self.assertNotIn("test_query_project2", project_ids)
        self.assertNotIn("test_query_project3", project_ids)
    
    def test_07_count_relationships_by_type(self):
        """Test counting relationships by type"""
        # Count relationships by story (relationship type)
        relationship_counts = (
            sqldb.session.query(
                Relationship.story,
                func.count(Relationship.relationship_id)
            )
            .filter(
                or_(
                    Relationship.source_id.like("test_query_%"),
                    Relationship.target_id.like("test_query_%")
                )
            )
            .group_by(Relationship.story)
            .all()
        )
        
        # Convert results to dict
        count_dict = {story: count for story, count in relationship_counts}
        
        # Verify counts
        self.assertEqual(count_dict["WORKS_AT"], 3)
        self.assertEqual(count_dict["MANAGES"], 1)
        self.assertEqual(count_dict["WORKS_ON"], 3)
        self.assertEqual(count_dict["LEADS"], 1)
        self.assertEqual(count_dict["SPONSORS"], 3)
    
    def test_08_join_nodes_and_relationships(self):
        """Test joining node and relationship data"""
        person1_id = "test_query_person1"
        
        # Get relationships for person1
        person1_rels = Relationship.query.filter(
            Relationship.source_id == person1_id
        ).all()
        
        # Get target nodes for each relationship
        target_ids = [rel.target_id for rel in person1_rels]
        target_nodes = Node.objects(nodeid__in=target_ids).all()
        
        # Create a lookup dict for target nodes
        target_dict = {node.nodeid: node for node in target_nodes}
        
        # Join relationship and node data
        joined_data = []
        for rel in person1_rels:
            if rel.target_id in target_dict:
                target_node = target_dict[rel.target_id]
                joined_data.append({
                    'relationship': rel.to_dict(),
                    'target_node': json.loads(target_node.to_json())
                })
        
        # Verify join results
        self.assertEqual(len(joined_data), 3)
        
        # Check if specific targets are in the results
        target_types = []
        for item in joined_data:
            target_labels = item['target_node'].get('labels', [])
            if 'Company' in target_labels:
                target_types.append('Company')
            elif 'Project' in target_labels:
                target_types.append('Project')
            elif 'Person' in target_labels:
                target_types.append('Person')
        
        # Verify we have company and project targets
        self.assertIn('Company', target_types)
        self.assertIn('Project', target_types)
        self.assertEqual(target_types.count('Project'), 2)

if __name__ == '__main__':
    unittest.main()