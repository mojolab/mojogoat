
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

def update_labels_from_graphset(p):
    for node in p:
        nodeid=node[0].get('nodeid')
        nodelabels=set(list(node[0].labels))
        filelabels=nodelabels
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
