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
        if re.match(r"search", query):
            tokens=query.replace("search","").lstrip().rstrip().split(" ")
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
        if re.match(r"shownew", query):
            tokens=query.replace("shownew","").lstrip().rstrip().split(" ")
            curfile=os.path.join(self.goatpath,"newgrass.gq")
            searchcommand="cat {} ".format(curfile)
            if len(tokens)>0:
                for token in tokens:
                    if token!="":
                        searchcommand = searchcommand + "| grep " + token + " "
            #searchcommand+=" | head 500"
            responselines=os.popen(searchcommand).read().lstrip().rstrip().split("\n")
            return responselines[:50]

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