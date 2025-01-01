# Importing dependencies
from platform import node

import pandas
import os,datetime
from py2neo import Graph
from py2neo.ogm import Repository, Model, Property, RelatedTo, Label
from py2neo.matching import *
import re,json

labels=[
    "Node",
    "Person",
    "Organization",
    "Artefact",
    "Role",
    "Place"
]
#Import pyxlrd
#Read configs from file in path "goatconfigs"
# GOAT Definitions
def get_rels_from_file(relfile):
    adddate=relfile.split("/")[-1].replace("relationships-","")
    with open(relfile) as f:
        rels=f.read().split("\n")
        if "" in rels:
            rels.remove("")
        relationships=[{"source":rel.split("|")[0],"story":rel.split("|")[1],"target":rel.split("|")[2],"date":"29-May-2022"} for rel in rels]
    return relationships
# function to get a mojogoat configuration for a specific dbname
def get_mgc(dbname="neo4j", goatconfigpath="/content/conf/neo4jgoatconfig.json"):
    try:
        with open(goatconfigpath) as f:
            goatconfig=json.loads(f.read())
        goatconfig['dbname']=dbname
        return goatconfig
    except Exception as e:
        print(str(e))
        return None

def update_keystones(goat, labels=labels):
    k1=goat.add_node(nodeid="__keystone0")
    k2=goat.add_node(nodeid="__keystone1")
    goat.update_labels("__keystone0",labels)
    goat.update_labels("__keystone1",labels)

    k1.isthesameas.add(k2)
    k1.linkedto.add(k2)
    k2.isthesameas.add(k1)
    k2.linkedto.add(k1)
    goat.repo.save(k2)
    goat.repo.save(k1)

# function to generate a nodeid
def get_nodeid(node):
    nodeid=node.replace(" ","")
    nodeid=re.sub('[^A-Za-z0-9]+', '', nodeid).lower()
    return nodeid

# Defining the types of nodes we are tracking
class Node(Model):
    __primarykey__="nodeid"
    nodeid = Property()
    name = Property()
    linkedto=RelatedTo("Node")
    isthesameas=RelatedTo("Node")
    nodetype = Property()
    url=Property()
    addedts=Property()
    updatedts=Property()

    def get_properties(self):
        return {
            'nodeid': self.nodeid,
            'name': self.name,
            'nodetype': self.nodetype
        }
    def set_properties(self,nodedict):
        if "name" in nodedict.keys():
            self.name=nodedict['name']
        return {
            'nodeid': self.nodeid,
            'name': self.name,
            'nodetype': self.nodetype
        }
    def __repr__(self):
        return "Node(nodeid={}, name={})".format(
            self.nodeid, self.name
        )

# These classes are only relevant for having more properties in the Neo4J daabase itself. Not strictly relevant methinks: Arjun 2023-04-06
# define a class to store Person records with properties nodeid, name, linkedto, urls
class Person(Node):
    __primarykey__="nodeid"
    nodeid = Property()
    name = Property()
    linkedto=RelatedTo(Node)
    urls=Property()
    isthesameas=RelatedTo(Node)
    def get_properties(self):
        return {
            "nodeid": self.nodeid,
            "name": self.name,
            "urls": self.urls
        }
    
# define a class to store Organizations with properties nodeid, name, linkedto
class Organization(Node):
    __primarykey__="nodeid"
    nodeid = Property()
    name = Property()
    linkedto=RelatedTo(Node)    
    description=Property()
    foundeddate=Property()
    hqlocation=Property()
    isthesameas=RelatedTo("Node")
    
    def get_properties(self):
        return {
            "nodeid": self.nodeid,
            "name": self.name,
            "description": self.description,
            "founded": self.founded,
            "hq": self.hq
        }

class Role(Node):
    __primarykey__="nodeid"
    nodeid = Property()
    name = Property()
    description = Property()
    linkedto=RelatedTo(Node)
    urls=Property()
    isthesameas=RelatedTo(Node)
    def get_properties(self):
        return {
            "nodeid": self.nodeid,
            "name": self.name,
            "urls": self.urls
        }

# define a class to store Artefacs with properties name, type, summary, and url
class Artefact(Node):
    __primarykey__="nodeid"
    nodeid = Property()
    name = Property()
    atype=Property()
    summary=Property()
    url=Property()
    linkedto=RelatedTo(Node)
    isthesameas=RelatedTo("Node")
 
    def get_properties(self):
        return {
            "nodeid": self.nodeid,
            "name": self.name,
            "atype": self.atype,
            "summary": self.summary,
            "url": self.url
        }

class Place(Node):
    __primarykey__="nodeid"
    nodeid = Property()
    name = Property()
    ptype=Property()
    summary=Property()
    url=Property()
    linkedto=RelatedTo(Node)
    isthesameas=RelatedTo("Node")
 
    def get_properties(self):
        return {
            "nodeid": self.nodeid,
            "name": self.name,
            "atype": self.atype,
            "summary": self.summary,
            "url": self.url
        }

# Define a class for a MojoGOAT
class Neo4jGoat:
    def __init__(self,configjson):
        with open(configjson) as f:
            goatconfig=json.loads(f.read())
        self.graph = Graph(goatconfig['url'], auth=(goatconfig['database'], goatconfig['password']))
        self.repo = Repository(goatconfig['url'], auth=(goatconfig['database'], goatconfig['password']))
        self.nodes=NodeMatcher(self.graph)
        self.rels=RelationshipMatcher(self.graph)
        #self.dbname=goatconfig['dbname']

    # Self Reporting

    #function to get the graph composition
    def get_compostion(self):
        return[{label:self.nodes.match(label).count()}for label in list(self.graph.schema.node_labels)]
        
    # function to add a generic node to the graph
    def add_node(self,**kwargs):
        nodeid=kwargs['nodeid']
        print(nodeid)
        enode=self.repo.match(Node,nodeid).first()
        if enode is not None:
            print("Node exists")
            enode.set_properties(kwargs)
            self.repo.save(enode)
            return enode
        print("Adding new node")
        p=Node(**kwargs)
        self.repo.save(p)
        return p
    
    def get_node_dict(self,nodeid):
        node=self.repo.match(Node,nodeid).first().get_properties()
        nodelabels=self.nodes.match("Node",nodeid=nodeid).first().labels
        node['labels']=list(nodelabels)
        return node
        
    # function to update the labels of a node
    def update_labels(self,nodeid,labels):
        thisnode=self.nodes.match("Node",nodeid=nodeid).first()
        tx=self.graph.begin()
        thisnode.update_labels(labels)
        tx.push(thisnode)
        self.graph.commit(tx)
        return thisnode.labels
    
    def get_labels(self,nodeid):
        thisnode=self.nodes.match("Node",nodeid=nodeid).first()
        return thisnode.labels

    # function to get the relationship between two nodes
    def get_story(self,node1,node2):
        story=node1.linkedto.get(node2,"story")
        return story

    #function to create and add lines to a relationship -- TODO: add a way to include timestamps for relationship updates
    def link(self,x,y,storyline,adddate):
        try:
            curstory=self.get_story(x,y)
            newstory=[storyline]
            print(newstory)
            if curstory is not None:
                newstory=list(set(newstory+curstory))
            output=x.linkedto.add(y, properties={"story":newstory,"adddate":adddate,"updatedate":datetime.datetime.now()})
            self.repo.save(x)
            return output
        except Exception as e:
            print(str(e))
            return None
    
    def link_nodes(self, x_nodeid, y_nodeid, story, adddate):
        x = self.repo.match(Node, x_nodeid).first()
        y = self.repo.match(Node, y_nodeid).first()
        print(x.nodeid, y.nodeid)
        if x is None or y is None:
            return None
        return self.link(x, y, story, adddate)

    # function to link nodes with relationship storyline "is"
    def link_is(self,node1,node2):
        node1.isthesameas.add(node2)
        node2.isthesameas.add(node1)
        self.repo.save(node1)
        self.repo.save(node2)

    # function to dump all relationships to a file
    def dump_all_rels(self,path="/opt/xpal-data/mojogoat"):
        rellines=""
        ts=datetime.datetime.now().strftime("%Y-%b-%d")
        for node in self.repo.match(Node).all():
            for rel in node.linkedto.triples():
                try:
                    for line in rel[1][1]['story']:
                        print("|".join([rel[0].nodeid,line,rel[2].nodeid]))
                        rellines=rellines+"\n"+"|".join([rel[0].nodeid,line,rel[2].nodeid],ts)
                except Exception as e:
                    print(str(e))
            for rel in node.isthesameas.triples():
                rellines=rellines+"\n"+"|".join([rel[0].nodeid,"is the same as",rel[2].nodeid],ts)
        with open(os.path.join(path,self.dbname+"-"+datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")),"w") as f:
            f.write(rellines)

    def get_taxonomy(self):
        graphlabels=self.graph.schema.node_labels
        #get all linked_to relationships from the graph that contain the text "is a" in the story property
        taxonomy=[rel for rel in self.rels.match((None,None,None)).where("_.story CONTAINS 'is a'").all()]
        return taxonomy
    
    #define a function to return an array of dictionaries with each dictionary representing a node. Add a property to the dictionary called "labels" that contains the labels of the node   
    def get_nodes(self):
        nodes=[node.get_properties() for node in self.repo.match(Node).all()]
        for node in nodes:
            nodelabels=self.nodes.match("Node",nodeid=node['nodeid']).first().labels
            node['labels']=list(nodelabels)
        return nodes