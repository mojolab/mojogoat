import time
from mojogoat.goatherd import *
import requests,sys

def update_neo4j_from_mojogoat(apiroot,neo4jdb):
    # Get the latest list of labels on all Node objects
    url=apiroot+'/labels'
    labels=list(requests.get(url).json().keys())
    print(labels)
    update_keystones(neo4jdb,labels)
    url=apiroot+'/nodes'
    r=requests.get(url)
    for node in r.json():
        neo4jdb.add_node(**node)
        neo4jdb.update_labels(node['nodeid'],node['labels'])
    url2=apiroot + '/relationships'
    r2=requests.get(url2)
    for rel in r2.json():
        try:
            p=neo4jdb.repo.match(Node,rel['source_id']).first()
            q=neo4jdb.repo.match(Node,rel['target_id']).first()
            neo4jdb.link(p,q,storyline=rel['story'],adddate=rel['timestamp'])
            neo4jdb.link(p,q,storyline=rel['story'],adddate=rel['timestamp'])
            neo4jdb.repo.save(p)
        except:
            print(rel)
        
   
def update_mojogoat_from_neo4j(apiroot,neo4jdb):
    neo4jcomp=neo4jdb.get_compostion()
    url=apiroot+'/labels'
    goatcomp=requests.get(url).json()
    #for label in neo4jcomp:

        
   
if __name__ == '__main__':
    apiroot='http://localhost:5001'
    neo4jconfig=get_mgc("neo4j")
    neo4jdb=Neo4jGoat(neo4jconfig)
    while True:
        neoids=neo4jdb.get_nodeids()
        url=apiroot+'/nodeids'
        goatids=requests.get(url).json()
        if len(neoids)==len(goatids):
            print("Nothing to sync")
            continue
        elif len(neoids)>len(goatids):
            print("Syncing from Neo4j to Goat")
            syncnodes=list(set(neoids)-set(goatids))
            print(syncnodes)
            for nodeid in syncnodes:
                node=neo4jdb.get_node_dict(nodeid)
                url=apiroot+'/nodes'
                r=requests.post(url,json=node)
                print(r.status_code)
        else:
            print("Syncing from Goat to Neo4j")
            syncnodes=list(set(goatids)-set(neoids))
            print(syncnodes)
            update_neo4j_from_mojogoat(apiroot,neo4jdb)
            

        #update_neo4j_from_mojogoat(apiroot,neo4jdb)
        #update_mojogoat_from_neo4j(apiroot,neo4jdb)    
        #print(neo4jdb.get_compostion())
        time.sleep(60)