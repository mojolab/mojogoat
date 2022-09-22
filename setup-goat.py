# Importing dependencies
import pygsheets
import pandas
import os,datetime
from py2neo import Graph
from py2neo.ogm import Repository, Model, Property, RelatedTo, Label
from py2neo.matching import *
import re


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
def get_mgc(dbname="neo4j"):
    goatconfig = {
        'username': 'neo4j',
        'password': 'theansweris42',
        'dbname': dbname,
        'dburl': 'host.docker.internal:11003'
    }
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

    def get_properties(self):
        return {
            'nodeid': self.nodeid,
            'name': self.name,
            'nodetype': self.nodetype
        }
    
    def __repr__(self):
        return "Node(nodeid={}, name={})".format(
            self.nodeid, self.name
        )


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


# Define a class for a MojoGOAT
class MojoGoat:
    def __init__(self,goatconfig):
        self.graph = Graph("bolt://"+goatconfig['dburl'], auth=(goatconfig['username'], goatconfig['password']), name=goatconfig['dbname'])
        self.repo = Repository("bolt://" + goatconfig['username'] + "@" +goatconfig['dburl'], password=goatconfig['password'], name=goatconfig['dbname'])
        self.nodes=NodeMatcher(self.graph)
        self.dbname=goatconfig['dbname']

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
            return enode
        print("Adding new node")
        p=Node(**kwargs)
        self.repo.save(p)
        return p
    
    # function to update the labels of a node
    def update_labels(self,nodeid,labels):
        thisnode=self.nodes.match("Node",nodeid=nodeid).first()
        tx=self.graph.begin()
        thisnode.update_labels(labels)
        tx.push(thisnode)
        self.graph.commit(tx)
        return thisnode.labels

    # function to get the relationship between two nodes
    def get_story(self,node1,node2):
        story=node1.linkedto.get(node2,"story")
        return story

    #function to create and add lines to a relationship -- TODO: add a way to include timestamps for relationship updates
    def link(self,x,y,storyline,adddate):
        curstory=self.get_story(x,y)
        newstory=[storyline]
        print(newstory)
        if curstory is not None:
            newstory=list(set(newstory+curstory))
        output=x.linkedto.add(y, properties={"story":newstory,"adddate":adddate,"updatedate":datetime.datetime.now()})
        return output

    # function to add all relationships from a dataframe pulled from a table containing triples
    def add_sheet_relationships(self,df):
        for triple in df.to_dict(orient="records"):
            print(triple['source'],triple['story'],triple['target'])
            try:
                source=self.add_node(nodeid=get_nodeid(triple['source']))
                target=self.add_node(nodeid=get_nodeid(triple['target']))
                output=self.link(source,target,triple['story'],triple['date'])
                print("Result of linkage: ",output)
                self.repo.save(source)
            except Exception as e:
                print(str(e))
    def import_relfile(self,relfile):
        relationships=get_rels_from_file(relfile)
        for triple in relationships:
            print(triple['source'],triple['story'],triple['target'])
            try:
                source=self.add_node(nodeid=get_nodeid(triple['source']))
                target=self.add_node(nodeid=get_nodeid(triple['target']))
                output=self.link(source,target,triple['story'],triple['date'])
                print("Result of linkage: ",output)
                self.repo.save(source)
            except Exception as e:
                print(str(e))

    # function to link nodes with relationship storyline "is"
    def link_is(self,node1,node2):
        node1.isthesameas.add(node2)
        node2.isthesameas.add(node1)
        self.repo.save(node1)
        self.repo.save(node2)

    # function to add an artefact 
    def add_artefact(self,node, url=None, summary=None, atype=None):
        nodeid=get_nodeid(node)
        a=Artefact(nodeid=nodeid, name=node, url=url, summary=summary, atype=type)
        self.repo.save(a)
        return a

    
            

    # Functions to get poop and milk out of the GOAT

    # loop through all person nodes in repo and get properties as a dict
    def dump_person_records(self):
        recs=[]
        for person in self.repo.match(Person):
            props=get_person_properties(person)
            recs.append(props)
        return recs

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


# Feeding the GOAT



# Google Sheets Functions

# function to get a list of dicts with sheetnames and dataframes from a google sheet
def get_sheet_download(gd,url):
    iodws=gd.open_by_url(url)
    wslist=iodws.worksheets()
    dflist=[]
    for ws in wslist:
        dfname=ws.title
        df=ws.get_as_df()
        dflist.append({"dfname":dfname,"df":df})
    return dflist