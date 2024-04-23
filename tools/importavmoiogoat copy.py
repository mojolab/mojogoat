import sys,os
import pandas as pd
import numpy as np

sys.path.append("/xpal-src/mojogoat/mojogoat")
from goatherd import *


# Connect to the GOATs

neo4jdb=Neo4jGoat("/xpal-data/conf/neo4jdbgoat.json")

 
 

mojolabels=labels+[]
print("Global Labels:"+str(labels)+"\nCurrent Composition: ",neo4jdb.get_compostion())
update_keystones(neo4jdb,mojolabels)
print("\nUpdated Composition: ",neo4jdb.get_compostion())


# Get the nodes from AVMojoGoat
goatpath="/xpal-data/goats/avmojogoat"
nodes=[]
nodelist=os.listdir(os.path.join(goatpath,"nodes"))
for nodefile in nodelist:
    with open(os.path.join(goatpath,"nodes",nodefile),"r") as f:
        nodes.append(json.loads(f.read()))
print("Nodes from AVMojoGoat: ",nodes)

with open("/xpal-data/goats/avmojogoat/snapshots/mojogoat-2023-01-09-03-39-24","r") as f:
    rellines=f.readlines()

rellist=[]
for rel in rellines:
    reldict={}
    reldict['source']=rel.split("|")[0]
    reldict['story']=rel.split("|")[1]
    reldict['target']=rel.split("|")[2]
    reldict['adddate']=rel.split("|")[3]
    rellist.append(reldict)

for rel in rellist:
    try:
        source=neo4jdb.repo.match(Node,rel['source']).first()
        target=neo4jdb.repo.match(Node,rel['target']).first()
        story=rel['story']
        adddate=rel['adddate']
        neo4jdb.link(source,target,story,adddate)
        neo4jdb.repo.save(source)
    except Exception as e:
        print(str(e),rel)
        
