import time
from mojogoat.goatherd import *
import requests,sys
        
   
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
        elif len(neoids)>len(goatids):
            print("Syncing from Neo4j to Goat")
            syncnodes=list(set(neoids)-set(goatids))
            print(syncnodes)
            for nodeid in syncnodes:
                node=neo4jdb.nodes.match("Node",nodeid=nodeid).first()
                nodedict=neo4jdb.get_node_dict(nodeid)
                url=apiroot+'/nodes'
                r=requests.post(url,json=nodedict)
                print(r.json())
                # add relationships
            for nodeid in syncnodes:
                reldicts=neo4jdb.get_rels_as_dicts(nodeid=nodeid)
                for rel in reldicts:
                    url2=apiroot+'/relationships'
                    print(rel)
                    r2=requests.post(url2,json=rel)
                    print(r2.json())
            
        else:
            print("Syncing from Goat to Neo4j")
            url=apiroot+'/labels'
            labels=list(requests.get(url).json().keys())
            print(labels)
            update_keystones(neo4jdb,labels)

            syncnodes=list(set(goatids)-set(neoids))
            print(syncnodes)
            for nodeid in syncnodes:
                url=apiroot+'/nodes/'+nodeid
                node=requests.get(url).json()
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
        time.sleep(60)