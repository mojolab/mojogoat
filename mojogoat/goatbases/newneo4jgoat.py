
from neo4j import GraphDatabase,RoutingControl
import json

def get_driver_from_file(configjson):
    with open(configjson,"r") as f:
        config=json.loads(f.read())
    URI=config['url']
    AUTH=(config['database'],config['password'])
    driver=GraphDatabase.driver(URI, auth=AUTH)
    return driver

def getallnodes(driver):
     records, _, _ = driver.execute_query(
         "MATCH (n) "
         "RETURN n",
         database="neo4j", routing_=RoutingControl.READ,
         )
     return records

def matchnode(driver,nodeid):
     records, _, _ = driver.execute_query(
         "MATCH (n) where n.nodeid = $nodeid "
         "RETURN n",
         nodeid=nodeid,database="neo4j", routing_=RoutingControl.READ,
         )
     return records

def get_nodes_by_substring(driver, substring):
    query = (
        "MATCH (n) "
        "WHERE n.nodeid STARTS WITH $substring "
        "RETURN n"
    )
    records, _, _ = driver.execute_query(
        query,
        substring=substring,
        database="neo4j",
        routing_=RoutingControl.READ,
    )
    return records

def get_connected_nodes(driver, nodeid):
    query = (
        "MATCH (n)-[r]->(connected) "
        "WHERE n.nodeid = $nodeid "
        "RETURN connected,r"
    )
    records, _, _ = driver.execute_query(
        query,
        nodeid=nodeid,
        database="neo4j",
        routing_=RoutingControl.READ,
    )
    return records

def update_labels_from_graphset(p):
    for node in p:
        nodeid=node[0].get('nodeid')
        nodelabels=set(list(node[0].labels))
        filelabels=nodelabels
        print(nodeid)
        try:
            with open("./textdata/nodes/"+nodeid,"r") as nodefile:
                nodejson=json.loads(nodefile.read())
                filelabels=set(nodejson['labels'])
        except Exception as e:
            print(nodeid, " file does not exist")
        if filelabels != nodelabels:
            print(nodeid,"Labels are different",nodelabels,filelabels)
            nodejson['labels']=list(nodelabels)
            with open("./textdata/nodes/"+nodeid,"w") as nodefile:
                print(json.dump(nodejson,nodefile,indent=4))

def update_node_properties(driver, nodeid, properties):
    query = (
        "MATCH (n) "
        "WHERE n.nodeid = $nodeid "
        "SET n += $properties "
        "RETURN n"
    )
    records, _, _ = driver.execute_query(
        query,
        nodeid=nodeid,
        properties=properties,
        database="neo4j",
        routing_=RoutingControl.WRITE,
    )
    return records

def update_all_node_properties(driver,p):
    #print(p)
    for node in p:
        nodeid=node[0].get('nodeid')
        nodelabels=set(list(node[0].labels))
        gnodejson=dict(node[0].items())
        #print(nodeid)
        gnodejson['labels']=list(nodelabels)
        try:
            with open("./textdata/nodes/"+nodeid,"r") as nodefile:
                nodejson=json.loads(nodefile.read()) 
                if len(nodejson.keys())>len(gnodejson.keys()):
                    print(nodejson,gnodejson)
                    for key in nodejson.keys():
                        if type(nodejson[key])!=str:
                            nodejson[key]=json.dumps(nodejson[key])
                    print(nodejson)
                    try:
                        update_node_properties(driver,nodeid,nodejson)
                        print("successfully updated")
                    except Exception as e:
                        print(e)
                
        except Exception as e:
            print("No file")

def get_node_and_relationship_counts(driver):
    node_query = (
        "MATCH (n) "
        "RETURN labels(n) AS labels, count(n) AS count"
    )
    relationship_query = (
        "MATCH ()-[r]->() "
        "RETURN type(r) AS type, count(r) AS count"
    )

    node_counts, _, _ = driver.execute_query(
        node_query,
        database="neo4j",
        routing_=RoutingControl.READ,
    )

    relationship_counts, _, _ = driver.execute_query(
        relationship_query,
        database="neo4j",
        routing_=RoutingControl.READ,
    )

    node_count_dict = {tuple(record['labels']): record['count'] for record in node_counts}
    relationship_count_dict = {record['type']: record['count'] for record in relationship_counts}

    return node_count_dict, relationship_count_dict