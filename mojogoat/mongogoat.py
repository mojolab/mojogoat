from . import mongonodes

def create_node(inputdict):
    if 'nodeid' in inputdict.keys():
        nodeid=inputdict['nodeid']
        if mongonodes.Node.objects(id=nodeid).first() is None:
            newnode=mongonodes.Node(id=nodeid)
            newnode.save()
            return newnode
        else:
            return mongonodes.Node.objects(id=nodeid).first()
    else:
        return None


def get_node_by_id(nodeid):
    return mongonodes.Node.objects(id=nodeid).first()

def get_node_by_label(label):
    return mongonodes.Node.objects(label=label).first()

def get_node_by_property(property,value):
    return mongonodes.Node.objects(property=value).first()