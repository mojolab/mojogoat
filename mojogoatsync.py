from mojogoat.goatherd import *
import requests,sys


if __name__ == '__main__':
    apiroot='http://localhost:5001'
    neo4jconfig=get_mgc("neo4j")
    print(neo4jconfig)
    neo4jdb=Neo4jGoat(neo4jconfig)
    print(neo4jdb.get_compostion())
    # Get the latest list of labels on all Node objects
    url=apiroot+'/labels'
    labels=requests.get(url).json()
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
        
    print(neo4jdb.get_compostion())