from mojogoat.goatbases.mongogoat.models import sqldb, Relationship, Node
import datetime
import json
from .goatbases.textgoat import *
from .utils import *
from mojogoat import herd, curgoat, herd_config
from sqlalchemy import or_

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
    """Create or update a node
    
    Args:
        body: Dictionary containing node data
        
    Returns:
        Tuple of (response, status_code)
    """
    if "nodeid" not in body.keys():
        return {"error":"nodeid field is required"}, 400
    
    nodeid = body['nodeid']
    node = Node.objects(nodeid=nodeid).first()
    
    if node is None:
        node = Node(nodeid=nodeid)
        
    # Handle the case where labels are passed as nodelabels for backward compatibility
    if 'nodelabels' in body and 'labels' not in body:
        body['labels'] = body.pop('nodelabels')
    
    # Update node with data
    try:
        node.update(**body)
        node.save()
        node.reload()
        
        # Convert to JSON and clean up MongoDB-specific fields
        response = json.loads(node.to_json())
        if '_id' in response:
            response.pop('_id')
        if '_cls' in response:
            response.pop('_cls')
            
        return response, 200
    except Exception as e:
        return {"error": f"Failed to save node: {str(e)}"}, 500
    



# Relationship controllers
#TODO rewrite to be able to searh rels better
def get_relationships(source=None, target=None, story=None):
    if source!=None:
        relationships = Relationship.query.filter_by(source_id=source).all()
    elif target!=None:
        relationships = Relationship.query.filter_by(target_id=target).all()
    elif story!=None:
        relationships = Relationship.query.filter(Relationship.story.contains(story)).all()
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
    """Create a relationship between two nodes
    
    Args:
        data: Dictionary containing relationship data
            - source: Source node ID
            - target: Target node ID
            - story: Relationship description
            
    Returns:
        Tuple of (response, status_code)
    """
    if not data:
        return {'message': 'No input data provided'}, 400
    
    # Validate required fields
    required_fields = ['source', 'target', 'story']
    for field in required_fields:
        if field not in data:
            return {'message': f'Missing required field: {field}'}, 400
    
    source_id = data['source']
    target_id = data['target']

    # Check if source and target exist in MongoDB
    source_node = Node.objects(nodeid=source_id).first()
    target_node = Node.objects(nodeid=target_id).first()
    
    if not source_node:
        return {'message': f'Source node not found: {source_id}'}, 400
    if not target_node:
        return {'message': f'Target node not found: {target_id}'}, 400
        
    # Check if a relationship with the same source, story, and target exists
    relationship = Relationship.query.filter_by(
        source_id=source_id,
        story=data['story'],
        target_id=target_id
    ).first()
    
    if relationship is not None:
        return {'message': 'Relationship already exists'}, 400
        
    # Create new relationship
    try:
        relationship = Relationship(
            source_id=source_id,
            target_id=target_id,
            story=data['story'],
            timestamp=datetime.datetime.now()
        )
        
        sqldb.session.add(relationship)
        sqldb.session.commit()
        
        return {
            'message': 'Relationship created successfully',
            'relationship': {
                'relationship_id': relationship.relationship_id,
                'source_id': relationship.source_id,
                'target_id': relationship.target_id,
                'story': relationship.story,
                'timestamp': relationship.timestamp.isoformat()
            }
        }, 200
        
    except Exception as e:
        sqldb.session.rollback()
        return {'message': f'Failed to create relationship: {str(e)}'}, 500

def delete_relationship_by_id(id):
    relationship = Relationship.query.filter_by(relationship_id=id).first()

    if not relationship:
        return {'message': 'Relationship not found'}, 404

    sqldb.session.delete(relationship)
    sqldb.session.commit()
    return {'message': 'Deleteled Successfully'}, 200

# Function to delete node and all relationships associated with it
def delete_node_by_id(id):
    """Delete a node and all its relationships
    
    Args:
        id: Node ID to delete
        
    Returns:
        Tuple of (response, status_code)
    """
    # Find the node in MongoDB
    node = Node.objects(nodeid=id).first()
    if not node:
        return {'message': 'Node not found'}, 404

    try:
        # First, delete all relationships in PostgreSQL where this node is source or target
        relationships = Relationship.query.filter(
            or_(Relationship.source_id==id, Relationship.target_id==id)
        ).all()
        
        if relationships:
            for relationship in relationships:
                sqldb.session.delete(relationship)
            sqldb.session.commit()
        
        # Then delete the node from MongoDB
        node.delete()
        return {
            'message': 'Node and all associated relationships deleted successfully',
            'deleted_relationships_count': len(relationships)
        }, 200
        
    except Exception as e:
        sqldb.session.rollback()
        return {'message': f'Failed to delete node: {str(e)}'}, 500

#Controller to return all unique labels across all Nodes
def get_labels():
    nodes = Node.objects().all()
    labels = []
    for n in nodes:
        if hasattr(n, 'labels') and n.labels:
            labels.extend(n.labels)
    labels = list(set(labels))
    composition = {}
    for l in labels:
        composition[l]= Node.objects(labels__contains=l).count()
    return composition, 200

def get_nodeids_by_label(label):
    """Get all node IDs with a specific label
    
    Args:
        label: The label to search for
        
    Returns:
        Tuple of (node_ids, status_code)
    """
    try:
        nodes = Node.objects(labels__contains=label).all()
        nodeids = []
        for n in nodes:
            nodeids.append(n.nodeid)
        return nodeids, 200
    except Exception as e:
        return {"error": f"Failed to retrieve node IDs: {str(e)}"}, 500
def get_nodes_by_label(label):
    """Get all nodes with a specific label
    
    Args:
        label: The label to search for
        
    Returns:
        Tuple of (nodes, status_code)
    """
    try:
        nodes = Node.objects(labels__contains=label).all()
        response = json.loads(nodes.to_json())
        
        # Clean up MongoDB-specific fields
        for node in response:
            if '_id' in node:
                node.pop('_id')
            if '_cls' in node:
                node.pop('_cls')
                
        return response, 200
    except Exception as e:
        return {"error": f"Failed to retrieve nodes: {str(e)}"}, 500
def get_nodeids():
    """Get all node IDs in the database
    
    Returns:
        Tuple of (node_ids, status_code)
    """
    try:
        nodes = Node.objects().all()
        nodeids = []
        for n in nodes:
            nodeids.append(n.nodeid)
        return nodeids, 200
    except Exception as e:
        return {"error": f"Failed to retrieve node IDs: {str(e)}"}, 500
