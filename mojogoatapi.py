'''
API to parse recieve messages and parse GOAT commands
'''
# TODO: #1 FEATURE - Add a command to process facts as distict from relationships
# TODO: #2 FEATURE - Add a command to process meeting notes
# TODO: #3 FEATURE - Add a command to delete new lines by message reply
# TODO: #4 OPTIMIZE - Standardize command function nomencalture and taxonomy
# TODO: #5 ARCHITECTURE - Shift to reading all constants from config files
# TODO: #6 ARCHITECTURE - Read labels from a schema file
# TODO: #7 ARCHITECTURE - Read object schemas from a schema file
# TODO: #8 ARCHITECTURE - Use appropriate stores for appropriate data - line records for relationships and doc records on entities

from datetime import datetime
from flask import Flask, request, jsonify
import io, os, re, sys
from jmespath import search
import requests

from mojogoat.utils import *
from mojogoat.goat import *

herd_config=read_herd_config(sys.argv[1])
herdroot=herd_config['herdroot']
goatlog=os.path.join(herdroot,"goatlog")
herd=get_goats(herd_config)
curgoat=herd[0]

app = Flask(__name__)

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


def set_current_goat(goatname):
    for goat in herd:
        if goat.goatname==goatname:
            curgoat=goat
            return "Current goat is now {}".format(curgoat.goatname)
    return "No such goat in the herd"

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

    if re.match(r"GOAT3>",message['text']):
        message['gtype']="goatfeed"
        message['feed']=message['text'][6:].lstrip().rstrip()
        message['response']=curgoat.feed_goat(message['feed'])
    return message

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',port='5001')





    
