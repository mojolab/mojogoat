from neo4j import GraphDatabase, RoutingControl
import json
import datetime

class Neo4jGoat:
    def __init__(self, configjson):
        with open(configjson) as f:
            goatconfig = json.loads(f.read())
        self.driver = GraphDatabase.driver(goatconfig['url'], auth=(goatconfig['database'], goatconfig['password']))

    def get_composition(self):
        with self.driver.session() as session:
            result = session.run("CALL db.labels()")
            for record in result:
                label = record[0]
                count = session.run(f"MATCH (n:{label}) RETURN count(n)").single()[0]
                print(f"Label: {label}, Count: {count}")
            #return [{label: session.run(f"MATCH (n:{label}) RETURN count(n)").single()[0]} for label in result]

    def add_node(self, **kwargs):
        nodeid = kwargs['nodeid']
        with self.driver.session() as session:
            existing_node = session.run(
                "MATCH (n {nodeid: $nodeid}) RETURN n", nodeid=nodeid
            ).single()
            if existing_node:
                session.run(
                    "MATCH (n {nodeid: $nodeid}) SET n += $properties",
                    nodeid=nodeid, properties=kwargs
                )
                return existing_node
            else:
                session.run(
                    "CREATE (n:Node {nodeid: $nodeid}) SET n += $properties",
                    nodeid=nodeid, properties=kwargs
                )
                return kwargs

    def get_node_dict(self, nodeid):
        with self.driver.session() as session:
            result = session.run(
                "MATCH (n {nodeid: $nodeid}) RETURN n", nodeid=nodeid
            ).single()
            if result:
                node = result["n"]
                labels = session.run(
                    "MATCH (n {nodeid: $nodeid}) RETURN labels(n)", nodeid=nodeid
                ).single()[0]
                node["labels"] = labels
                return node
            return None

    def update_labels(self, nodeid, labels):
        with self.driver.session() as session:
            session.run(
                "MATCH (n {nodeid: $nodeid}) SET n: $labels",
                nodeid=nodeid, labels=labels
            )

    def get_labels(self, nodeid):
        with self.driver.session() as session:
            result = session.run(
                "MATCH (n {nodeid: $nodeid}) RETURN labels(n)", nodeid=nodeid
            ).single()
            return result[0] if result else []

    def link(self, x_nodeid, y_nodeid, storyline, adddate):
        with self.driver.session() as session:
            session.run(
                "MATCH (x {nodeid: $x_nodeid}), (y {nodeid: $y_nodeid}) "
                "MERGE (x)-[r:LINKED_TO]->(y) "
                "SET r.story = $storyline, r.adddate = $adddate, r.updatedate = $updatedate",
                x_nodeid=x_nodeid, y_nodeid=y_nodeid, storyline=storyline,
                adddate=adddate, updatedate=datetime.datetime.now().isoformat()
            )

    def link_is(self, node1_id, node2_id):
        with self.driver.session() as session:
            session.run(
                "MATCH (n1 {nodeid: $node1_id}), (n2 {nodeid: $node2_id}) "
                "MERGE (n1)-[:IS_THE_SAME_AS]->(n2) "
                "MERGE (n2)-[:IS_THE_SAME_AS]->(n1)",
                node1_id=node1_id, node2_id=node2_id
            )

    def dump_all_rels(self, path):
        with self.driver.session() as session:
            result = session.run(
                "MATCH (n)-[r]->(m) RETURN n.nodeid, type(r), m.nodeid, r.story"
            )
            with open(path, "w") as f:
                for record in result:
                    f.write(f"{record['n.nodeid']}|{record['type(r)']}|{record['m.nodeid']}|{record['r.story']}\n")

    def get_taxonomy(self):
        with self.driver.session() as session:
            result = session.run(
                "MATCH (n)-[r:LINKED_TO]->(m) WHERE r.story CONTAINS 'is a' RETURN n, r, m"
            )
            return [record for record in result]

    def get_nodes(self):
        with self.driver.session() as session:
            result = session.run("MATCH (n) RETURN n")
            nodes = []
            for record in result:
                node = dict(record["n"])
                labels = session.run(
                    "MATCH (n {nodeid: $nodeid}) RETURN labels(n)",
                    nodeid=node["nodeid"]
                ).single()[0]
                node["labels"] = labels
                nodes.append(node)
            return nodes
