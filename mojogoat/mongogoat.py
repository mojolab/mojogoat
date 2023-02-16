#TODO Refactor this file to use MongoDB to store nodes and postgresql to store relationships
import os, json, re
from datetime import datetime

class Goat:
    def __init__(self,goatconfig):
        self.config=goatconfig
        self.goatpath = goatconfig['goatpath']
        self.goatname = goatconfig['goatname']
        # if goatpath does not exist create it
        if not os.path.exists(self.goatpath):
            os.makedirs(self.goatpath)
        # if goatpath does not contain nodes and snapshots folders, create them
        if not os.path.exists(os.path.join(self.goatpath,"nodes")):
            os.mkdir(os.path.join(self.goatpath,"nodes"))
        if not os.path.exists(os.path.join(self.goatpath,"snapshots")):
            os.mkdir(os.path.join(self.goatpath,"snapshots"))
        # if goatpath does not contain a newgrass file, create it
        if not os.path.exists(os.path.join(self.goatpath,"newgrass.gq")):
            with open(os.path.join(self.goatpath,"newgrass.gq"),'w') as f:
                f.write("")
        # if goatpath does not contain a goatrels file, create it
        if not os.path.exists(os.path.join(self.goatpath,"goatrels.gq")):
            with open(os.path.join(self.goatpath,"goatrels.gq"),'w') as f:
                f.write("")
        print(goatconfig)
    # function to parse goatqueries
    def ask_goat(self,query):
        #if query starts with "search" do something
        if re.match(r"searchrels", query):
            tokens=query.replace("searchrels","").lstrip().rstrip().split(" ")
            with open(os.path.join(self.goatpath,"goatrels.gq"),"r") as f:
                latestfile=f.read().lstrip().rstrip()
            curfile=os.path.join(self.goatpath,latestfile)
            searchcommand="cat {} ".format(curfile)
            for token in tokens:
                searchcommand = searchcommand + "| grep " + token + " "
            print(searchcommand)

            responselines=os.popen(searchcommand).read().lstrip().rstrip().split("\n")
            responselines=[line for line in responselines if line != ""]    
            return responselines
        if re.match(r"shownewrels", query):
            tokens=query.replace("shownewrels","").lstrip().rstrip().split(" ")
            curfile=os.path.join(self.goatpath,"newgrass.gq")
            searchcommand="cat {} ".format(curfile)
            if len(tokens)>0:
                for token in tokens:
                    if token!="":
                        searchcommand = searchcommand + "| grep " + token + " "
            #searchcommand+=" | head 500"
            responselines=os.popen(searchcommand).read().lstrip().rstrip().split("\n")
            return responselines[:50]
        if re.match(r"searchnode", query):
            tokens=query.replace("searchnode","").lstrip().rstrip().split(" ")
            searchresults=[]
            for token in tokens:
                searchcommand="find {} -name '*{}*'".format(os.path.join(self.goatpath,"nodes"),token)
                responselines=[os.path.split(line)[1] for line in os.popen(searchcommand).read().lstrip().rstrip().split("\n")]
                searchresults.extend(responselines)
                #searchresults+=os.popen().read().lstrip().rstrip().split("\n")
            return searchresults
        if re.match(r"getnode", query):
            nodeid=query.replace("getnode","").lstrip().rstrip()
            print("Getting node {}".format(query))
            if os.path.exists(os.path.join(self.goatpath,"nodes",nodeid)): 
                print("Node found")
                with open(os.path.join(self.goatpath,"nodes",query.replace("getnode","").lstrip().rstrip()),'r') as f:
                    return json.dumps(json.loads(f.read()))

    def feed_goat(self,feed):
        feedlines=feed.lstrip().rstrip().split("\n")
        print(feedlines)
        quadlist=[]
        for line in feedlines:
            if len(line.split(" "))<3:
                print("line too short")
                break
            source=line.split(" ")[0]
            target=line.split(" ")[-1]
            story=line.replace(source,"").replace(target,"").lstrip().rstrip()
            triple="|".join([source,story,target])
            quad=triple+"|"+datetime.now().strftime("%d-%b-%Y")        
            quadlist.append(quad)
        with open(os.path.join(self.goatpath,"newgrass.gq"),'a') as f:
            f.write("\n")
            f.write("\n".join(quadlist))
        return quadlist

    
    def tell_goat(self,tell,apply_to=None):
        if re.match(r"pull", tell):
            try:
                output=os.popen("cd {} && git pull && cd".format(self.goatpath)).read().strip()
                return output
            except Exception as e:
                return str(e)
        if re.match(r"push", tell):
            try:
                output=os.popen("cd {} && git add * && git commit -a -m 'auto commit' && git push && cd".format(self.goatpath)).read().strip()
                return output
            except Exception as e:
                return str(e)
        if re.match(r"dropline", tell):
            try:
                output="Really drop lines?\n"
                if apply_to is not None:
                    output+=apply_to
                return output
            except Exception as e:
                return str(e)
    def add_node(self,node):
        # add a node to the goat
        # first check if node exists
        nodedict={}
        if "{" in node:
            try:
                nodedict=json.loads(node)
            except Exception as e:
                return str(e)
        else:
            nodelines=node.lstrip().rstrip().split("\n")
            for line in nodelines:
                key=line.split("=")[0].lstrip().rstrip()
                value=line.split("=")[1].lstrip().rstrip()
                nodedict[key]=value
        if "nodeid" in nodedict.keys():
            if os.path.exists(os.path.join(self.goatpath,"nodes",nodedict['nodeid'])):
                with open(os.path.join(self.goatpath,"nodes",nodedict['nodeid']),'r') as f:
                    oldnode=json.loads(f.read())
                for key in nodedict.keys():
                    oldnode[key]=nodedict[key]
                with open(os.path.join(self.goatpath,"nodes",nodedict['nodeid']),'w') as f:
                    f.write(json.dumps(oldnode))
                return "Updated node \n {}".format(nodedict)    
            else:
                with open(os.path.join(self.goatpath,"nodes",nodedict['nodeid']),'w') as f:
                    f.write(json.dumps(nodedict))
                return(json.dumps(nodedict))     
    def all_nodes(self):
        nodelist=[]
        for nodefile in [os.path.join(self.goatpath,"nodes",node) for node in os.listdir(os.path.join(self.goatpath,"nodes"))]:
            with open(nodefile,"r") as f:
                nodelist.append(json.loads(f.read()))
        return(nodelist)
    def all_rels(self):
        try:
            with open(os.path.join(self.goatpath,"goatrels.gq"),"r") as f:
                relfile=f.read().lstrip().rstrip()   
        except Exception as e:
            return str(e)
        try:
            print(os.path.join(self.goatpath,relfile))
            with open(os.path.join(self.goatpath,relfile)) as f:
                rels=f.read().split("\n")
            if "" in rels:
                rels.remove("")
            relationships=[]
            for rel in rels:
                try:
                    reldict={"source":rel.split("|")[0],"story":rel.split("|")[1],"target":rel.split("|")[2],"date":rel.split("|")[3]}
                    relationships.append(reldict)
                except Exception as e:
                    print(e)
                    print(rel)
            return relationships
        except Exception as e:
            return str(e)
    def add_rels(self,newrels):
        try:
            with open(os.path.join(self.goatpath,"goatrels.gq"),"r") as f:
                relfile=f.read().lstrip().rstrip()
        except Exception as e:
            return str(e)
        try:
            print(os.path.join(self.goatpath,relfile))
            with open(os.path.join(self.goatpath,relfile)) as f:
                rels=f.read().split("\n")
            if "" in rels:
                rels.remove("")
            totalrels=list(set(rels+newrels))
            #save these in a file under the snapshots folder
            with open(os.path.join(self.goatpath,"snapshots","mojogoat-"+datetime.now().strftime("%Y-%m-%d-%H-%M-%S")),"w") as f:
                f.write("\n".join(totalrels))
            with open(os.path.join(self.goatpath,"goatrels.gq"),"w") as f:
                f.write("/".join(["snapshots","mojogoat-"+datetime.now().strftime("%Y-%m-%d-%H-%M-%S")]))
        except Exception as e:
            return str(e)

            
            