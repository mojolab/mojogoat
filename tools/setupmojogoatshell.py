import sys,os
import pandas as pd
import numpy as np
import re
import datetime
sys.path.append("/xpal-src/mojogoat")
from mojogoat.goatbases.neo4jgoat import *


# Connect to the GOATs

avmojogoat=Neo4jGoat("/xpal-data/conf/neo4jdbgoat-arjun.json")



mojolabels=labels+[]
print("Global Labels:"+str(labels)+"\nCurrent Composition: ",avmojogoat.get_compostion())
update_keystones(avmojogoat,mojolabels)
print("\nUpdated Composition: ",avmojogoat.get_compostion())