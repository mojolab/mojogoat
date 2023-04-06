from mojogoat.models import sqldb, Relationship, Node
import datetime
import json
from .goat import *
from .utils import *
from mojogoat import herd, curgoat, herd_config

# Goat contollers

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



# Node Controllers
def get_nodes():
    nodes = Node.objects().all()
    response = json.loads(nodes.to_json())
    for node in response:
        node.pop('_id')
        node.pop('_cls')
    return response, 200

def get_node(nodeid):
    node = Node.objects(nodeid=nodeid).first()
    if node is None:
        return {"error":"node not found"}, 404
    response = json.loads(node.to_json())
    response.pop('_id')
    response.pop('_cls')
    return response, 200

def add_node(body):
    if "nodeid" not in body.keys():
        return {"error":"nodeid field is required"}, 400
    nodeid=body['nodeid']
    node = Node.objects(nodeid=nodeid).first()
    if node is None:
        node = Node(nodeid=nodeid)
        node.save()
    node.update(**body)
    node.save()
    node.reload()
    response=json.loads(node.to_json())
    response.pop('_id')
    response.pop('_cls')
    return response, 200
    



# Relationship controllers
def get_relationships(source=None, target=None, query=None):
    if source!=None:
        relationships = Relationship.query.filter_by(source_id=source).all()
    elif target!=None:
        relationships = Relationship.query.filter_by(target_id=target).all()
    elif query!=None:
        relationships = Relationship.query.filter(Relationship.story.contains(query)).all()
    else:
        relationships = Relationship.query.all()

    results = []

    for r in relationships:
        results.append({
            'relationship_id': r.relationship_id,
            'source_id': r.source_id,
            'target_id': r.target_id,
            'story': r.story,
            'timestamp': r.timestamp.isoformat()
        })

    return results, 200

def get_relationship_by_id(id):
    relationship = Relationship.query.filter_by(relationship_id=id).first()

    if not relationship:
        return {'message': 'Relationship not found'}, 404

    return relationship.to_dict(), 200


def create_relationship(data):

    if not data:
        return {'message': 'No input data provided'}, 400
    # user_source = User.objects(user_id=data['source_id']).first()
    # user_target = User.objects(user_id=data['target_id']).first()
    
    source_id=data['source']
    target_id=data['target']

    # check if source and target exist in the mongo db class Node 
    source_node = Node.objects(nodeid=source_id).first()
    target_node = Node.objects(nodeid=target_id).first()
    if not source_node:
        return {'message': 'Source node not found'}, 400
    if not target_node:
        return {'message': 'Target node not found'}, 400
    # Check if a relationship with the same source, story, and target exists
    relationship = Relationship.query.filter_by(source_id=source_id, story=data['story'], target_id=target_id).first()
    if relationship is not None:
        return {'message': 'Relationship already exists'}, 400
    relationship = Relationship(
    # source_id=user_source.user_id,
    # target_id=user_target.user_id,
    source_id=data['source'],
    target_id=data['target'],
    story=data['story'],
    timestamp=datetime.now()
    )
    try:
        sqldb.session.add(relationship)
        sqldb.session.commit()   

    except:
        return {'message': 'There was an internal error'}, 400
    
    return {'message': 'Relationship created successfully'}, 200

def delete_relationship_by_id(id):
    relationship = Relationship.query.filter_by(relationship_id=id).first()

    if not relationship:
        return {'message': 'Relationship not found'}, 404

    sqldb.session.delete(relationship)
    sqldb.session.commit()
    return {'message': 'Deleteled Successfully'}, 200

