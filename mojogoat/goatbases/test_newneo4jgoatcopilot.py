import argparse
import json
from newneo4jgoatcopilot import Neo4jGoat

def main():
    parser = argparse.ArgumentParser(description="Test script for newneo4jgoatcopilot.py")
    parser.add_argument("configjson", help="Path to the JSON file containing Neo4j connection details.")
    args = parser.parse_args()

    # Load configuration
    with open(args.configjson, "r") as f:
        config = json.load(f)

    # Initialize Neo4jGoat
    goat = Neo4jGoat(args.configjson)

    # Test methods
    print("Testing get_composition...")
    print(goat.get_composition())

    print("Testing add_node...")
    goat.add_node(nodeid="test_node", name="Test Node", description="This is a test node.")

    print("Testing get_node_dict...")
    print(goat.get_node_dict("test_node"))

    print("Testing update_labels...")
    goat.update_labels("test_node", ["TestLabel"])

    print("Testing get_labels...")
    print(goat.get_labels("test_node"))

    print("Testing link...")
    goat.add_node(nodeid="test_node_2", name="Test Node 2")
    goat.link("test_node", "test_node_2", "Test Storyline", "2025-04-28")

    print("Testing dump_all_rels...")
    goat.dump_all_rels("relationships_dump.txt")

    print("Testing get_taxonomy...")
    print(goat.get_taxonomy())

    print("Testing get_nodes...")
    print(goat.get_nodes())

if __name__ == "__main__":
    main()

# Help message for JSON file format
# {
#     "url": "bolt://localhost:7687",
#     "database": "neo4j",
#     "password": "your_password"
# }
