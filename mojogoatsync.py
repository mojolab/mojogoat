from mojogoat.goatherd import *
import requests,sys


if __name__ == '__main__':
    # Connect to the GOATs
    neo4jconfig=get_mgc("neo4j")
    print(neo4jconfig)
    neo4jdb=Neo4jGoat(neo4jconfig)
    print(neo4jdb.get_compostion())
    #TODO relace with API call to get all labels
    labels=[
    'Person',
    'Brand',
    'Company',
    'NGO',
    'Govt Body',
    'Node',
    ]
    update_keystones(neo4jdb,labels)
    url=sys.argv[1]+"/nodes"
    r=requests.get(url)
    for node in r.json():
        print(node)
        if "Company" in node['labels']:
            neo4jdb.add_node(name=node['companyname'],**node)
        if "Brand" in node['labels']:
            neo4jdb.add_node(name=node['brandname'],**node)
        neo4jdb.update_labels(node['nodeid'],node['labels'])
    url2='http://localhost:5001/relationships'
    print(neo4jdb.get_compostion())