# Importing dependencies
#from platform import node
import pygsheets
import pandas
import os,datetime
from py2neo import Graph
from py2neo.ogm import Repository, Model, Property, RelatedTo, Label
from py2neo.matching import *
import re,json

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
def get_mgc(dbname="neo4j", goatconfigpath="/xpal-data/goatconfigs/neo4jgoatconfig.json"):
    with open(goatconfigpath) as f:
        goatconfig=json.loads(f.read())
    goatconfig['dbname']=dbname
    return goatconfig

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
    url=Property() # Added to point to the mojogoat API node

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

'''
Obsolete or redundant

These are only useful to keep additional data in Neo4J which we dont need. 

# define a class to store Person records with properties nodeid, name, linkedto, urls
class Person(Node):
    __primarykey__="nodeid"
    nodeid = Property()
    name = Property()
    role=Property()
    linkedto=RelatedTo(Node)
    urls=Property()
    organization=Property()
    isthesameas=RelatedTo(Node)
    def get_properties(self):
        return {
            "nodeid": self.nodeid,
            "name": self.name,
            "role": self.role,
            "urls": self.urls,
            "organization": self.organization
        }
    
    
# define a class to store Organizations with properties nodeid, name, linkedto
class Organization(Node):
    __primarykey__="nodeid"
    nodeid = Property()
    name = Property()
    linkedto=RelatedTo(Node)    
    description=Property()
    founded=Property()
    hq=Property()
    isthesameas=RelatedTo("Node")
    
    def get_properties(self):
        return {
            "nodeid": self.nodeid,
            "name": self.name,
            "description": self.description,
            "founded": self.founded,
            "hq": self.hq
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
'''

# Define a class for a MojoGOAT
class Neo4jGoat:
    def __init__(self,goatconfig):
        self.graph = Graph("bolt://"+goatconfig['dburl'], auth=(goatconfig['username'], goatconfig['password']), name=goatconfig['dbname'])
        self.repo = Repository("bolt://" + goatconfig['username'] + "@" +goatconfig['dburl'], password=goatconfig['password'], name=goatconfig['dbname'])
        self.nodes=NodeMatcher(self.graph)
        self.dbname=goatconfig['dbname']

    # Self Reporting

    #function to get the graph composition
    def get_compostion(self):
        return {label:self.nodes.match(label).count() for label in list(self.graph.schema.node_labels)}
        
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
    # function to return all nodes as a list of dictionaries
    def get_node_dicts(self):
        nodes=[]
        for node in self.repo.match(Node):
            nodedict=node.get_properties()
            nodedict['labels']=list(self.nodes.match("Node",nodeid=node.nodeid).first().labels)
            nodes.append(nodedict)
        return nodes
    # function to return a specific node as a dictionary
    def get_node_dict(self,nodeid):
        node=self.repo.match(Node,nodeid).first().get_properties()
        nodelabels=self.nodes.match("Node",nodeid=nodeid).first().labels
        node['labels']=list(nodelabels)
        return node
    # function to return a list of all nodeids
    def get_nodeids(self):
        return [node.nodeid for node in self.repo.match(Node)]
    
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
        curstory=self.get_story(x,y)
        newstory=[storyline]
        #print(newstory)
        if curstory is not None:
            newstory=list(set(newstory+curstory))
        output=x.linkedto.add(y, properties={"story":newstory,"adddate":adddate,"updatedate":datetime.datetime.now()})
        return output

    # function to link nodes with relationship storyline "is"
    def link_is(self,node1,node2):
        node1.isthesameas.add(node2)
        node2.isthesameas.add(node1)
        self.repo.save(node1)
        self.repo.save(node2)

    def eat_goat_nodes(self,goat):
        for node in goat.all_nodes():
            self.add_node(**node)
            self.update_labels(node['nodeid'],node['labels'])
    
    def eat_goat_rels(self,goat):
        for rel in goat.all_rels():
            source=self.add_node(nodeid=rel['source'])
            target=self.add_node(nodeid=rel['target'])
            self.link(source,target,rel['story'],rel['date'])
            self.repo.save(source)

    # function to dump all relationships to a file
    def dump_all_rels(self,path="/opt/xpal-data/mojogoat"):
        rellines=""    
        for node in self.repo.match(Node).all():
            for rel in node.linkedto.triples():
                try:
                    for line in rel[1][1]['story']:
                        rellines=rellines+"\n"+"|".join([rel[0].nodeid,line,rel[2].nodeid])
                except Exception as e:
                    print(str(e))
            for rel in node.isthesameas.triples():
                rellines=rellines+"\n"+"|".join([rel[0].nodeid,"is the same as",rel[2].nodeid])
        with open(os.path.join(path,self.dbname+"-"+datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")),"w") as f:
            f.write(rellines)
    
    def get_rels_as_dicts(self,nodeid=None):
        rels=[]
        reldicts=[]
        if nodeid is not None:
            node=self.nodes.match("Node",nodeid=nodeid).first()
            rels=self.graph.match({node},r_type="LINKEDTO")
        else:
            rels=self.graph.match(r_type="LINKEDTO")
        for rel in rels:
            stories=rel.get("story")
            if stories is None:
                stories=['']
            for story in stories:
                reldict={}
                reldict['source']=rel.start_node.get("nodeid")
                reldict['target']=rel.end_node.get("nodeid")
                reldict['story']=story
                #reldict['adddate']=rel.get("adddate")
                reldicts.append(reldict)
        return reldicts


def update_keystones(goat,labels):
    k1=goat.add_node(nodeid="__keystone1")
    k2=goat.add_node(nodeid="__keystone2")

    k1labels=list(goat.nodes.match("Node",nodeid="__keystone1").first().labels)
    k2labels=list(goat.nodes.match("Node",nodeid="__keystone2").first().labels)
    
    nlabels=list(set(k1labels+k2labels+labels))

    print("Original Labels: "+str(list(set(k1labels+k2labels))))
    print("New Labels: "+str(nlabels))

    

    goat.update_labels("__keystone1",nlabels)
    goat.update_labels("__keystone2",nlabels)

    k1.isthesameas.add(k2)
    k1.linkedto.add(k2)
    k2.isthesameas.add(k1)
    k2.linkedto.add(k1)
    goat.repo.save(k2)
    goat.repo.save(k1)
