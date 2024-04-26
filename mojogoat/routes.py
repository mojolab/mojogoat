from flask import Flask, request, jsonify
import json
from mojogoat.mojogoat.goatbases.mongogoat.models import sqldb, Relationship, Node
from mojogoat import *
from mojogoat import controllers

# Listener
@app.route('/listener', methods=["POST"])
def listener():
     input_json = request.get_json(force=True) 
     input_json['timercvd'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")    
     # send input_json to processing function
     with open(goatlog, 'a') as f:
         f.write(str(input_json) + '\n')
     result = controllers.process_message(input_json)
     result['timeresponded']=datetime.now().strftime("%Y-%m-%d %H:%M:%S IST") 
     with open(goatlog, 'a') as f:
         f.write(str(result) + '\n')
     return jsonify(result)

# Node
@app.route('/nodes', methods=['GET'])
def get_nodes():
    result, status_code = controllers.get_nodes()
    return jsonify(result), status_code

@app.route('/nodes/<nodeid>', methods=['GET'])
def get_node(nodeid):
    result, status_code = controllers.get_node(nodeid)
    return jsonify(result), status_code

#Route to get nodes by label using controllers.get_nodes_by_label()
@app.route('/nodes/label/<label>', methods=['GET'])
def get_nodes_by_label(label):
    result, status_code = controllers.get_nodes_by_label(label)
    return jsonify(result), status_code

'''
 Create a new mongonodes.Node from a POST request with a JSON payload. The JSON payload should contain a 'nodeid' field.
 If a mongonodes.Node already exists with the same 'nodeid' field, update the existing mongonodes.Node with the new data, else 
 create a new mongonodes.Node and return as JSON 
'''
@app.route('/nodes', methods=['POST'])
@app.route('/nodes/<nodeid>', methods=['POST'])
def add_node(nodeid=None):
    body = request.get_json()
    result, status_code = controllers.add_node(body)
    return jsonify(result), status_code


# Relationship
@app.route('/relationships', methods=['GET'])
def get_relationships():
    source = request.args.get('source')
    target = request.args.get('target')
    story = request.args.get('story')

    result, status_code = controllers.get_relationships(source=source, target=target, story=story)    
    return jsonify(result), status_code




@app.route('/relationships', methods=['POST'])
def create_relationship():
    data = request.get_json()
    result,status_code = controllers.create_relationship(data)
    return jsonify(result), status_code


@app.route('/relationships/<relationship_id>', methods=['DELETE'])
def delete_relationship(relationship_id):
    result,status_code  = controllers.delete_relationship_by_id(relationship_id)
    return jsonify(result), status_code

# Route to search relationships by source, target or story fragment by sending a POST queryu to /relationships/search
@app.route('/relationships/search', methods=['POST'])
def search_relationships():
    data = request.get_json()
    result, status_code = controllers.get_relationships(**data)
    return jsonify(result), status_code

@app.route('/relationships/<int:id>', methods=['GET'])
def get_relationship_by_id(id):
    # Get relationship by ID
    result, status_code = controllers.get_relationship_by_id(id)
    return jsonify(result), status_code

#App Route to delete node
@app.route('/nodes/<nodeid>', methods=['DELETE'])
def delete_node(nodeid):
    result, status_code = controllers.delete_node_by_id(nodeid)
    return jsonify(result), status_code

#Route to get all labels using controller.get_labels()
@app.route('/labels', methods=['GET'])
def get_labels():
    result, status_code = controllers.get_labels()
    return jsonify(result), status_code

#Route to get all node ids for a label using controller.get_nodeids_by_label()
@app.route('/nodeids/<label>', methods=['GET'])
def get_nodeids_by_label(label):
    result, status_code = controllers.get_nodeids_by_label(label)
    return jsonify(result), status_code

#Route to get all node ids using controller.get_nodeids()
@app.route('/nodeids', methods=['GET'])
def get_nodeids():
    result, status_code = controllers.get_nodeids()
    return jsonify(result), status_code

