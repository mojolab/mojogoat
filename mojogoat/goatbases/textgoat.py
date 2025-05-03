import os, json, re
from datetime import datetime

#TODO: TextGoat Functions defined separately. Goat should use mongodb and not text files.


class TextGoat:
    def __init__(self,goatconfig):
        self.config=goatconfig
        self.goatpath = goatconfig['goatpath']
        self.goatname = goatconfig['goatname']
        
        # Debug output
        print(f"Initializing TextGoat with path: {self.goatpath}, name: {self.goatname}")
        
        # Create all necessary directories
        os.makedirs(self.goatpath, exist_ok=True)
        os.makedirs(os.path.join(self.goatpath, "nodes"), exist_ok=True)
        os.makedirs(os.path.join(self.goatpath, "snapshots"), exist_ok=True)
        
        # Create necessary files if they don't exist
        newgrass_path = os.path.join(self.goatpath, "newgrass.gq")
        if not os.path.exists(newgrass_path):
            with open(newgrass_path, 'w') as f:
                f.write("")
                print(f"Created empty newgrass file: {newgrass_path}")
                
        goatrels_path = os.path.join(self.goatpath, "goatrels.gq")
        if not os.path.exists(goatrels_path):
            with open(goatrels_path, 'w') as f:
                f.write("")
                print(f"Created empty goatrels file: {goatrels_path}")
                
        print(f"TextGoat initialized with config: {goatconfig}")
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
    # Node CRUD Operations
    def add_node(self, *args, **kwargs):
        """Create or update a node with the given node ID and data
        
        Args:
            nodeid: The unique identifier for the node
            **node_data: Additional node properties
            
        Returns:
            The node data dictionary
        """
        # Debug output
        print(f"TextGoat.add_node called with args: {args}, kwargs: {kwargs}")
        
        # Initialize variables
        nodeid = None
        node_data = {}
        
        # Handle legacy string format ('{...}')
        if len(args) == 1 and isinstance(args[0], str) and args[0].startswith('{'):
            try:
                # Try to parse as JSON
                node_dict = json.loads(args[0])
                if 'nodeid' in node_dict:
                    nodeid = node_dict['nodeid']
                    node_data = node_dict
                else:
                    raise ValueError("JSON node data must include 'nodeid'")
            except json.JSONDecodeError:
                # Not JSON, so treat as a node ID
                nodeid = args[0]
                node_data = kwargs.copy()
        # Handle dictionary format
        elif len(args) == 1 and isinstance(args[0], dict):
            node_dict = args[0].copy()
            if 'nodeid' in node_dict:
                nodeid = node_dict['nodeid']
                node_data = node_dict
            else:
                raise ValueError("Dictionary node data must include 'nodeid'")
        # Handle nodeid as first arg with kwargs
        elif len(args) == 1:
            nodeid = args[0]
            node_data = kwargs.copy()
        # Handle nodeid in kwargs
        elif 'nodeid' in kwargs:
            node_data = kwargs.copy()
            nodeid = node_data.pop('nodeid')
        # Error case
        else:
            raise ValueError("No nodeid provided")
            
        # Now that we have nodeid and node_data, proceed with node creation/update
        # Ensure nodeid is included in the node data
        node_data['nodeid'] = nodeid
        
        # Handle labels (ensure it's a list)
        if 'labels' in node_data and not isinstance(node_data['labels'], list):
            if isinstance(node_data['labels'], str):
                node_data['labels'] = [label.strip() for label in node_data['labels'].split(',')]
            else:
                node_data['labels'] = [str(node_data['labels'])]
        
        # Add nodelabels as 'labels' for backward compatibility
        if 'nodelabels' in node_data and 'labels' not in node_data:
            if isinstance(node_data['nodelabels'], list):
                node_data['labels'] = node_data['nodelabels']
            elif isinstance(node_data['nodelabels'], str):
                node_data['labels'] = [label.strip() for label in node_data['nodelabels'].split(',')]
            else:
                node_data['labels'] = [str(node_data['nodelabels'])]
                
        # Add timestamp if not present
        if 'created' not in node_data:
            node_data['created'] = datetime.now().isoformat()
        if 'updated' not in node_data:
            node_data['updated'] = datetime.now().isoformat()
        else:
            # Always update the updated timestamp
            node_data['updated'] = datetime.now().isoformat()
        
        # Check if node exists
        node_path = os.path.join(self.goatpath, "nodes", nodeid)
        print(f"Node path: {node_path}")
        
        if os.path.exists(node_path):
            # Update existing node
            try:
                with open(node_path, 'r') as f:
                    content = f.read().strip()
                    if content:
                        existing_node = json.loads(content)
                        # Update existing node with new data
                        existing_node.update(node_data)
                        node_data = existing_node
                    else:
                        print(f"Empty node file: {node_path}")
            except json.JSONDecodeError as e:
                print(f"Invalid JSON in node file {node_path}: {str(e)}")
            except Exception as e:
                print(f"Error updating existing node: {str(e)}")
        
        # Ensure nodes directory exists
        os.makedirs(os.path.dirname(node_path), exist_ok=True)
        
        # Debug output
        print(f"Saving node {nodeid} with data: {node_data}")
        
        # Write node data to file
        try:
            with open(node_path, 'w') as f:
                f.write(json.dumps(node_data, indent=2))
            print(f"Node {nodeid} saved successfully")
        except Exception as e:
            print(f"Error writing node file: {str(e)}")
            raise
            
        return node_data
    
    def get_nodes(self):
        """Get all nodes
        
        Returns:
            List of node dictionaries
        """
        nodes = []
        nodes_dir = os.path.join(self.goatpath, "nodes")
        
        # Debug output
        print(f"TextGoat.get_nodes called. Looking in directory: {nodes_dir}")
        
        # Check if nodes directory exists
        if not os.path.exists(nodes_dir):
            print(f"Nodes directory {nodes_dir} does not exist")
            # Create it to avoid future issues
            os.makedirs(nodes_dir, exist_ok=True)
            return nodes
            
        # List all files in the nodes directory
        try:
            node_files = os.listdir(nodes_dir)
            print(f"Found {len(node_files)} node files in {nodes_dir}")
        except Exception as e:
            print(f"Error listing node directory {nodes_dir}: {str(e)}")
            return nodes
            
        # Process each node file
        for nodefile in node_files:
            # Skip directories and system files
            file_path = os.path.join(nodes_dir, nodefile)
            if os.path.isdir(file_path) or nodefile.startswith('.'):
                continue
                
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    if not content.strip():
                        print(f"Empty node file: {file_path}")
                        continue
                        
                    node_data = json.loads(content)
                    
                    # Ensure node has required fields
                    if 'nodeid' not in node_data:
                        node_data['nodeid'] = nodefile
                        
                    nodes.append(node_data)
                    
            except json.JSONDecodeError as e:
                print(f"Invalid JSON in node file {file_path}: {str(e)}")
            except Exception as e:
                print(f"Error reading node file {file_path}: {str(e)}")
                
        # Debug info
        print(f"Returning {len(nodes)} nodes")
        return nodes
    
    def get_node(self, nodeid):
        """Get a node by its ID
        
        Args:
            nodeid: The node ID to retrieve
            
        Returns:
            Node data dictionary or None if not found
        """
        # Debug output
        print(f"TextGoat.get_node called with nodeid: {nodeid}")
        
        if not nodeid:
            print("Error: No nodeid provided")
            return None
            
        node_path = os.path.join(self.goatpath, "nodes", nodeid)
        print(f"Looking for node at path: {node_path}")
        
        if os.path.exists(node_path):
            try:
                with open(node_path, 'r') as f:
                    content = f.read()
                    if not content.strip():
                        print(f"Empty node file for {nodeid}")
                        return None
                        
                    node_data = json.loads(content)
                    
                    # Ensure node has nodeid
                    if 'nodeid' not in node_data:
                        node_data['nodeid'] = nodeid
                        
                    return node_data
                    
            except json.JSONDecodeError as e:
                print(f"Invalid JSON in node file for {nodeid}: {str(e)}")
            except Exception as e:
                print(f"Error reading node {nodeid}: {str(e)}")
                
        else:
            print(f"Node {nodeid} not found at path {node_path}")
                
        return None
        
    def get_nodes_by_label(self, label):
        """Get all nodes with a specific label
        
        Args:
            label: The label to filter by
            
        Returns:
            List of matching node dictionaries
        """
        # Debug output
        print(f"TextGoat.get_nodes_by_label called with label: {label}")
        
        matching_nodes = []
        
        # Get all nodes
        all_nodes = self.get_nodes()
        print(f"Filtering {len(all_nodes)} nodes for label: {label}")
        
        # Filter nodes by label
        for node in all_nodes:
            # Check both 'labels' and 'nodelabels' fields for backward compatibility
            node_labels = []
            
            # Check 'labels' field
            if 'labels' in node and node['labels']:
                if isinstance(node['labels'], list):
                    node_labels.extend(node['labels'])
                elif isinstance(node['labels'], str):
                    node_labels.append(node['labels'])
            
            # Check 'nodelabels' field for backward compatibility
            if 'nodelabels' in node and node['nodelabels']:
                if isinstance(node['nodelabels'], list):
                    node_labels.extend(node['nodelabels'])
                elif isinstance(node['nodelabels'], str):
                    node_labels.append(node['nodelabels'])
            
            # Match against label
            if label in node_labels:
                matching_nodes.append(node)
                
        # Debug output
        print(f"Found {len(matching_nodes)} nodes with label: {label}")
        return matching_nodes
        
    def delete_node(self, nodeid):
        """Delete a node by its ID
        
        Args:
            nodeid: The ID of the node to delete
            
        Returns:
            True if node was deleted, False otherwise
        """
        # Debug output
        print(f"TextGoat.delete_node called with nodeid: {nodeid}")
        
        if not nodeid:
            print("Error: No nodeid provided")
            return False
            
        node_path = os.path.join(self.goatpath, "nodes", nodeid)
        print(f"Attempting to delete node at path: {node_path}")
        
        if os.path.exists(node_path):
            try:
                # Check if it's a file before deleting
                if not os.path.isfile(node_path):
                    print(f"Error: {node_path} is not a file")
                    return False
                    
                # Delete the file
                os.remove(node_path)
                print(f"Successfully deleted node {nodeid}")
                return True
                
            except PermissionError as e:
                print(f"Permission error deleting node {nodeid}: {str(e)}")
            except Exception as e:
                print(f"Error deleting node {nodeid}: {str(e)}")
                
        else:
            print(f"Node {nodeid} not found at path {node_path}")
                
        return False
        
    def all_nodes(self):
        """Legacy method for backward compatibility
        
        Returns:
            List of all nodes
        """
        return self.get_nodes()
    # Relationship CRUD Operations
    def get_relationships(self, source=None, target=None, story=None):
        """Get relationships with optional filtering
        
        Args:
            source: Optional source node ID to filter by
            target: Optional target node ID to filter by
            story: Optional relationship type/story to filter by
            
        Returns:
            List of relationship dictionaries
        """
        relationships = []
        
        try:
            # Get the path to the current relationship file
            with open(os.path.join(self.goatpath, "goatrels.gq"), "r") as f:
                relfile = f.read().strip()
                
            # If relfile is empty, return empty list
            if not relfile:
                return relationships
                
            # Read relationships from file
            rel_path = os.path.join(self.goatpath, relfile)
            if not os.path.exists(rel_path):
                return relationships
                
            with open(rel_path) as f:
                rels = f.read().split("\n")
                
            # Remove empty lines
            rels = [rel for rel in rels if rel.strip()]
            
            # Parse relationships
            for i, rel in enumerate(rels):
                try:
                    parts = rel.split("|")
                    if len(parts) < 3:
                        print(f"Invalid relationship format: {rel}")
                        continue
                        
                    # Handle case where date might be missing
                    if len(parts) >= 4:
                        rel_date = parts[3]
                    else:
                        rel_date = datetime.now().strftime("%d-%b-%Y")
                        
                    reldict = {
                        "source_id": parts[0],
                        "story": parts[1],
                        "target_id": parts[2],
                        "date": rel_date,
                        "relationship_id": f"rel_{i}"  # Generate a unique ID
                    }
                    
                    # Apply filters if provided
                    if (source is None or reldict["source_id"] == source) and \
                       (target is None or reldict["target_id"] == target) and \
                       (story is None or reldict["story"] == story):
                        relationships.append(reldict)
                        
                except Exception as e:
                    print(f"Error parsing relationship: {rel}. Error: {str(e)}")
                    
            return relationships
            
        except Exception as e:
            print(f"Error getting relationships: {str(e)}")
            return relationships
            
    def create_relationship(self, source, target, story):
        """Create a new relationship between nodes
        
        Args:
            source: Source node ID
            target: Target node ID
            story: Relationship type/story
            
        Returns:
            Dictionary representing the created relationship or None if failed
        """
        try:
            # Verify that source and target nodes exist
            source_node = self.get_node(source)
            target_node = self.get_node(target)
            
            if not source_node or not target_node:
                print(f"Source or target node not found: {source}, {target}")
                return None
                
            # Format the relationship
            date_str = datetime.now().strftime("%d-%b-%Y")
            new_rel = f"{source}|{story}|{target}|{date_str}"
            
            # Get current relationships file
            rel_file_ref = os.path.join(self.goatpath, "goatrels.gq")
            
            # Create snapshots directory if it doesn't exist
            snapshots_dir = os.path.join(self.goatpath, "snapshots")
            os.makedirs(snapshots_dir, exist_ok=True)
            
            # Create a new relationships file in snapshots
            snapshot_name = f"mojogoat-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
            snapshot_path = os.path.join(self.goatpath, "snapshots", snapshot_name)
            
            # Read existing relationships
            existing_rels = []
            try:
                with open(rel_file_ref, "r") as f:
                    existing_file = f.read().strip()
                    
                if existing_file:
                    existing_path = os.path.join(self.goatpath, existing_file)
                    if os.path.exists(existing_path):
                        with open(existing_path, "r") as f:
                            existing_rels = f.read().split("\n")
                            existing_rels = [rel for rel in existing_rels if rel.strip()]
            except Exception as e:
                print(f"Error reading existing relationships: {str(e)}")
            
            # Add new relationship
            if new_rel not in existing_rels:
                existing_rels.append(new_rel)
                
            # Write to snapshot file
            with open(snapshot_path, "w") as f:
                f.write("\n".join(existing_rels))
                
            # Update reference file
            with open(rel_file_ref, "w") as f:
                f.write(os.path.join("snapshots", snapshot_name))
                
            # Create relationship object to return
            rel_id = f"rel_{len(existing_rels) - 1}"  # Use index as ID
            rel_dict = {
                "source_id": source,
                "target_id": target,
                "story": story,
                "date": date_str,
                "relationship_id": rel_id
            }
            
            return rel_dict
            
        except Exception as e:
            print(f"Error creating relationship: {str(e)}")
            return None
            
    def delete_relationship(self, relationship_id):
        """Delete a relationship by its ID
        
        Args:
            relationship_id: The ID of the relationship to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Parse relationship ID to get index
            if not relationship_id.startswith("rel_"):
                return False
                
            try:
                rel_index = int(relationship_id.replace("rel_", ""))
            except ValueError:
                return False
                
            # Get current relationships
            relationships = self.get_relationships()
            
            # Check if index is valid
            if rel_index < 0 or rel_index >= len(relationships):
                return False
                
            # Get current relationships file
            rel_file_ref = os.path.join(self.goatpath, "goatrels.gq")
            
            # Create snapshots directory if it doesn't exist
            snapshots_dir = os.path.join(self.goatpath, "snapshots")
            os.makedirs(snapshots_dir, exist_ok=True)
            
            # Create a new relationships file in snapshots
            snapshot_name = f"mojogoat-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
            snapshot_path = os.path.join(self.goatpath, "snapshots", snapshot_name)
            
            # Read existing relationships
            existing_rels = []
            try:
                with open(rel_file_ref, "r") as f:
                    existing_file = f.read().strip()
                    
                if existing_file:
                    existing_path = os.path.join(self.goatpath, existing_file)
                    if os.path.exists(existing_path):
                        with open(existing_path, "r") as f:
                            existing_rels = f.read().split("\n")
                            existing_rels = [rel for rel in existing_rels if rel.strip()]
            except Exception as e:
                print(f"Error reading existing relationships: {str(e)}")
                return False
                
            # Check if index is valid for the existing relationships
            if rel_index >= len(existing_rels):
                return False
                
            # Remove the relationship
            existing_rels.pop(rel_index)
            
            # Write to snapshot file
            with open(snapshot_path, "w") as f:
                f.write("\n".join(existing_rels))
                
            # Update reference file
            with open(rel_file_ref, "w") as f:
                f.write(os.path.join("snapshots", snapshot_name))
                
            return True
            
        except Exception as e:
            print(f"Error deleting relationship: {str(e)}")
            return False
            
    def get_composition(self):
        """Get the composition of nodes by label
        
        Returns:
            Dictionary with label counts
        """
        composition = {}
        
        for node in self.get_nodes():
            if 'labels' in node and node['labels']:
                for label in node['labels']:
                    if label in composition:
                        composition[label] += 1
                    else:
                        composition[label] = 1
        
        return composition
        
    def get_taxonomy(self):
        """Get the taxonomy of relationship types
        
        Returns:
            Dictionary with relationship type counts
        """
        taxonomy = {}
        
        for rel in self.get_relationships():
            story = rel['story']
            if story in taxonomy:
                taxonomy[story] += 1
            else:
                taxonomy[story] = 1
                
        return taxonomy
        
    def dump_all_rels(self, filename):
        """Dump all relationships to a file
        
        Args:
            filename: Path to dump file
            
        Returns:
            Number of relationships dumped
        """
        relationships = self.get_relationships()
        
        # Format relationships
        formatted_rels = []
        for rel in relationships:
            formatted_rels.append(f"{rel['source_id']}|{rel['story']}|{rel['target_id']}|{rel['date']}")
            
        # Write to file
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            f.write("\n".join(formatted_rels))
            
        return len(relationships)
    
    # Legacy method names for backward compatibility
    def all_rels(self):
        """Legacy method for backward compatibility
        
        Returns:
            List of all relationships
        """
        return self.get_relationships()
        
    def add_rels(self, newrels):
        """Legacy method to add multiple relationships
        
        Args:
            newrels: List of relationship strings
            
        Returns:
            Success message or error
        """
        try:
            # Get current relationships file
            rel_file_ref = os.path.join(self.goatpath, "goatrels.gq")
            
            # Create snapshots directory if it doesn't exist
            snapshots_dir = os.path.join(self.goatpath, "snapshots")
            os.makedirs(snapshots_dir, exist_ok=True)
            
            # Create a new relationships file in snapshots
            snapshot_name = f"mojogoat-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
            snapshot_path = os.path.join(self.goatpath, "snapshots", snapshot_name)
            
            # Read existing relationships
            existing_rels = []
            try:
                with open(rel_file_ref, "r") as f:
                    existing_file = f.read().strip()
                    
                if existing_file:
                    existing_path = os.path.join(self.goatpath, existing_file)
                    if os.path.exists(existing_path):
                        with open(existing_path, "r") as f:
                            existing_rels = f.read().split("\n")
                            existing_rels = [rel for rel in existing_rels if rel.strip()]
            except Exception as e:
                print(f"Error reading existing relationships: {str(e)}")
            
            # Combine existing and new relationships
            total_rels = list(set(existing_rels + newrels))
            
            # Write to snapshot file
            with open(snapshot_path, "w") as f:
                f.write("\n".join(total_rels))
                
            # Update reference file
            with open(rel_file_ref, "w") as f:
                f.write(os.path.join("snapshots", snapshot_name))
                
            return f"Added {len(newrels)} relationships. Total: {len(total_rels)}"
            
        except Exception as e:
            return str(e)

            
            