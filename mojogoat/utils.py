import os,json,re
from .goat import Goat

def read_herd_config(herdpath):
    with open(herdpath,'r') as f:
        herd_config=json.load(f)
    return herd_config


def get_goats(herd_config):
    goats=[]
    for goat in herd_config['goatlist']:
        goats.append(Goat(goat))
    return goats

def get_nodeid(node):
    nodeid=node.replace(" ","")
    nodeid=re.sub('[^A-Za-z0-9]+', '', nodeid).lower()
    return nodeid
