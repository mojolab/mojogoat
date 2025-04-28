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
from mongoengine import Document, StringField

class Node(Document):
    node_id = StringField(required=True, unique=True)
    data = StringField()

def create_mongo_node(node_id, data):
    node = Node(node_id=node_id, data=json.dumps(data))
    node.save()

def read_mongo_node(node_id):
    return Node.objects(node_id=node_id).first()

def update_mongo_node(node_id, updates):
    node = read_mongo_node(node_id)
    if node:
        node.data = json.dumps(updates)
        node.save()

def delete_mongo_node(node_id):
    node = read_mongo_node(node_id)
    if node:
        node.delete()
