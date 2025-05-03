# CRUD Operations for GOAT Storage Mechanisms

# Neo4j CRUD Operations
from neo4j import GraphDatabase

def create_node_neo4j(driver, label, properties):
    with driver.session() as session:
        session.run(f"CREATE (n:{label} {{props}})", props=properties)

def read_node_neo4j(driver, label, property_key, property_value):
    with driver.session() as session:
        result = session.run(f"MATCH (n:{label} {{{property_key}: $value}}) RETURN n", value=property_value)
        return [record["n"] for record in result]

def update_node_neo4j(driver, label, property_key, property_value, updates):
    with driver.session() as session:
        session.run(f"MATCH (n:{label} {{{property_key}: $value}}) SET n += $updates", value=property_value, updates=updates)

def delete_node_neo4j(driver, label, property_key, property_value):
    with driver.session() as session:
        session.run(f"MATCH (n:{label} {{{property_key}: $value}}) DELETE n", value=property_value)

# TextGoat CRUD Operations
import os

def create_textgoat_node(config, node_id, data):
    node_path = os.path.join(config['goatpath'], 'nodes', f"{node_id}.json")
    with open(node_path, 'w') as f:
        json.dump(data, f)

def read_textgoat_node(config, node_id):
    node_path = os.path.join(config['goatpath'], 'nodes', f"{node_id}.json")
    if os.path.exists(node_path):
        with open(node_path, 'r') as f:
            return json.load(f)
    return None

def update_textgoat_node(config, node_id, updates):
    node = read_textgoat_node(config, node_id)
    if node:
        node.update(updates)
        create_textgoat_node(config, node_id, node)

def delete_textgoat_node(config, node_id):
    node_path = os.path.join(config['goatpath'], 'nodes', f"{node_id}.json")
    if os.path.exists(node_path):
        os.remove(node_path)

# MongoDB CRUD Operations
from mongoengine import Document, StringField, ListField, DateTimeField
import json
from datetime import datetime

# Import the Node class from the models module
from mojogoat.goatbases.mongogoat.models import Node

def create_mongo_node(nodeid, data):
    """Create a new MongoDB node with provided data
    
    Args:
        nodeid: Unique identifier for the node
        data: Dictionary containing node data
    
    Returns:
        Created node object
    """
    node = Node.objects(nodeid=nodeid).first()
    if node is None:
        node = Node(nodeid=nodeid)
        
    # Update node with data
    for key, value in data.items():
        setattr(node, key, value)
    
    node.save()
    return node

def read_mongo_node(nodeid):
    """Read a MongoDB node by its ID
    
    Args:
        nodeid: Unique identifier for the node
    
    Returns:
        Node object if found, None otherwise
    """
    return Node.objects(nodeid=nodeid).first()

def update_mongo_node(nodeid, updates):
    """Update a MongoDB node with new data
    
    Args:
        nodeid: Unique identifier for the node
        updates: Dictionary containing node updates
    
    Returns:
        Updated node object if found, None otherwise
    """
    node = read_mongo_node(nodeid)
    if node:
        node.update(**updates)
        node.save()
        node.reload()
        return node
    return None

def delete_mongo_node(nodeid):
    """Delete a MongoDB node by its ID
    
    Args:
        nodeid: Unique identifier for the node
    
    Returns:
        True if node was deleted, False otherwise
    """
    node = read_mongo_node(nodeid)
    if node:
        node.delete()
        return True
    return False
