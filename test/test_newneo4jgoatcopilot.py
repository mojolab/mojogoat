import argparse
import json
import os
import sys
sys.path.append("/xpal-src/mojogoat")
from mojogoat.goatbases.newneo4jgoatcopilot import Neo4jGoat

def main():
    parser = argparse.ArgumentParser(description="Test script for newneo4jgoatcopilot.py")
    parser.add_argument("configjson", help="Path to the JSON file containing Neo4j connection details.")
    args = parser.parse_args()

    # Load configuration
    with open(args.configjson, "r") as f:
        config = json.load(f)

    # Initialize Neo4jGoat
    goat = Neo4jGoat(args.configjson)

    # Load test data from testdatarels.gq
    testdata_path = os.path.join(os.path.dirname(__file__), "testdata", "testdatarels.gq")
    with open(testdata_path, "r") as f:
        testdata = f.readlines()

    # Parse and use test data
    for line in testdata:
        subject, predicate, obj, date = line.strip().split('|')
        goat.add_node(nodeid=subject, name=subject)
        goat.add_node(nodeid=obj, name=obj)
        goat.link(subject, obj, predicate, date)

    # Test methods
    print("Testing get_composition...")
    print(goat.get_composition())

    print("Testing get_nodes...")
    print(goat.get_nodes())

    print("Testing dump_all_rels...")
    goat.dump_all_rels("relationships_dump.txt")

    print("Testing get_taxonomy...")
    print(goat.get_taxonomy())

if __name__ == "__main__":
    main()

# Help message for JSON file format
# {
#     "url": "bolt://localhost:7687",
#     "database": "neo4j",
#     "password": "your_password"
# }
