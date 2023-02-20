'''
API to parse recieve messages and parse GOAT commands
'''
# TODO: #1 FEATURE - Add a command to process facts as distict from relationships
# TODO: #2 FEATURE - Add a command to process meeting notes
# TODO: #3 FEATURE - Add a command to delete new lines by message reply
# TODO: #4 OPTIMIZE - Standardize command function nomencalture and taxonomy
# TODO: #6 ARCHITECTURE - Read labels from a schema file
# TODO: #7 ARCHITECTURE - Read object schemas from a schema file
# TODO: #8 ARCHITECTURE - Use appropriate stores for appropriate data - line records for relationships and doc records on entities

from datetime import datetime
import json
from flask import Flask, Response, request, jsonify
import io, os, re, sys
#from jmespath import search
import requests
#from sqlalchemy import outparam
from flask import Flask, request, jsonify
from flask_mongoengine import MongoEngine

from mojogoat.utils import *
from mojogoat.goat import *
from mojogoat import mongonodes


app = Flask(__name__)



global herd_config
herd_config=read_herd_config(sys.argv[1])
goatpen=herd_config['goatpen']
goatlog=os.path.join(goatpen,"goatlog")
global herd
herd=get_goats(herd_config)
global curgoat
curgoat=herd[0]

app.config['MONGODB_SETTINGS'] = {
    'host':'mongodb://localhost/'+curgoat.goatname
}




db = MongoEngine(app)



@app.route('/listener', methods=["POST"])
def listener():
     input_json = request.get_json(force=True) 
     input_json['timercvd'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")    
     # send input_json to processing function
     with open(goatlog, 'a') as f:
         f.write(str(input_json) + '\n')
     result = process_message(input_json)
     result['timeresponded']=datetime.now().strftime("%Y-%m-%d %H:%M:%S IST") 
     with open(goatlog, 'a') as f:
         f.write(str(result) + '\n')
     return jsonify(result)

# App routes for CRUD operations on mongonodes.Node objects

# Retrieve all existing mongonodes.Node from mongodb and return as json after removing cls and id fields
@app.route('/nodes', methods=['GET'])
def get_nodes():
    nodes = mongonodes.Node.objects().all()
    response = json.loads(nodes.to_json())
    for node in response:
        node.pop('_id')
        node.pop('_cls')
    return jsonify(response), 200

# Route to retrieve a single node speicified by nodeid

@app.route('/nodes/<nodeid>', methods=['GET'])
def get_node(nodeid):
    node = mongonodes.Node.objects(nodeid=nodeid).first()
    if node is None:
        return jsonify({"error":"node not found"}), 404
    response = json.loads(node.to_json())
    response.pop('_id')
    response.pop('_cls')
    return jsonify(response), 200

'''
 Create a new mongonodes.Node from a POST request with a JSON payload. The JSON payload should contain a 'nodeid' field.
 If a mongonodes.Node already exists with the same 'nodeid' field, update the existing mongonodes.Node with the new data, else 
 create a new mongonodes.Node and return as JSON 
'''
@app.route('/nodes', methods=['POST'])
@app.route('/nodes/<nodeid>', methods=['POST'])
def add_node(nodeid=None):
    body = request.get_json()
    if "nodeid" not in body.keys():
        return jsonify({"error":"nodeid field is required"}), 400
    nodeid=body['nodeid']
    node = mongonodes.Node.objects(nodeid=nodeid).first()
    if node is None:
        node = mongonodes.Node(nodeid=nodeid)
        node.save()
    node.update(**body)
    node.save()
    node.reload()
    response=json.loads(node.to_json())
    response.pop('_id')
    response.pop('_cls')
    return jsonify(response), 200



def set_current_goat(goatname):
    global curgoat
    global herd
    global herd_config
    herd=get_goats(herd_config)
    for goat in herd:
        if goat.goatname==goatname:
            curgoat=goat
            return "Current goat is now {}".format(curgoat.goatname)
    return "No such goat in the herd"

def add_goat(goatrepo):
    global herd
    global herd_config
    herd=get_goats(herd_config)
    newgoatname=goatrepo.split("/")[-1]
    output=os.popen("cd {} && git clone {}".format(goatpen,goatrepo)).read().lstrip().rstrip()
    print(output)
    goatconfig={
        "goatname":newgoatname,
        "goatpath":os.path.join(goatpen,newgoatname),
        "goatdesc":"{}".format(newgoatname)
    }
    print(goatconfig)
    newgoat=Goat(goatconfig)
    print(newgoat.goatname)
    herd.append(newgoat)
    herd_config['goatlist'].append(goatconfig)
    with open(sys.argv[1],'w') as f:
        json.dump(herd_config,f)
    return newgoat

def process_message(message):
    message['response']=["Me-eh!"]
    try:
        message['response']+=["Goat say > "+os.popen("fortune -s").read().strip()]
    except:
        pass
    apply_to=None

    # apply_to is a list of lines to apply the command in the message to
    if "apply_to" in message:
        message['response']+=["Now we are talking - that was a reply to {}".format(message['apply_to'])]
        apply_to=message['apply_to']
    message['gtype']="unknown"

    if re.match(r"HERD\?>listgoats",message['text']):
        message['response']=[goat.goatname for goat in herd]+['Current goat is {}'.format(curgoat.goatname)]
        message['gtype']="commandherd"

    if re.match(r"HERD!>setgoat",message['text']):
        newgoat=message['text'].replace("HERD!>setgoat","").lstrip().rstrip()
        if "apply_to" in message.keys() and message['apply_to'] is not None:
            newgoat=message['apply_to']
        message['response']=[set_current_goat(newgoat)]
        message['gtype']="commandherd"

    if re.match(r"HERD!>newgoat",message['text']):
        newgoatrepo=message['text'].replace("HERD!>newgoat","").lstrip().rstrip()
        newgoat=add_goat(newgoatrepo)

        message['response']=[set_current_goat(newgoat.goatname)]
        message['gtype']="commandherd"
    
    if re.match(r"GOAT\?>",message['text']):
        # do something
        message['gtype']="goatquery"
        message['query']=message['text'][6:].lstrip().rstrip()
        message['response']="I am a goat and I am not programmed to answer queries yet."
        message['response']=curgoat.ask_goat(message['query'])
    
    if re.match(r"GOAT!>",message['text']):
        # Feed the goat a triple
        message['gtype']="goattell"
        message['tell']=message['text'][6:].lstrip().rstrip()
        # Feed the goat a triple
        message['response']=curgoat.tell_goat(message['tell'], apply_to)

    if re.match(r"GOAT3>addrels",message['text']):
        message['gtype']="goatfeed"
        message['feed']=message['text'][13:].lstrip().rstrip()
        message['response']=curgoat.feed_goat(message['feed'])

    if re.match(r"GOAT3>addnode",message['text']):
        message['gtype']="goatfeed"
        message['feed']=message['text'][13:].lstrip().rstrip()
        message['response']=curgoat.add_node(message['feed'])
    return message

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',port='5000')





    
