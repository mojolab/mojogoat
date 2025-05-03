const relationships = [];

document.getElementById('fileInput').addEventListener('change', function(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const lines = e.target.result.split('\n');
            const listContainer = document.getElementById('relationshipList');
            listContainer.innerHTML = '';
            relationships.length = 0; // Clear existing relationships
            
            // Only add non-empty lines
            const nonEmptyLines = lines.filter(line => line.trim());
            
            nonEmptyLines.forEach((line, index) => {
                relationships.push(line);
                const listItem = document.createElement('li');
                listItem.className = 'list-group-item';

                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.className = 'form-check-input me-2';
                checkbox.dataset.index = index;
                checkbox.addEventListener('change', function() {
                    // Automatically update graph when selection changes
                    renderSelectedRelationships();
                });

                const textSpan = document.createElement('span');
                textSpan.textContent = line;

                const editBtn = document.createElement('button');
                editBtn.textContent = 'Edit';
                editBtn.className = 'btn btn-sm btn-warning ms-2';
                editBtn.addEventListener('click', () => editRelationship(index));

                const deleteBtn = document.createElement('button');
                deleteBtn.textContent = 'Delete';
                deleteBtn.className = 'btn btn-sm btn-danger ms-2';
                deleteBtn.addEventListener('click', () => deleteRelationship(index));

                listItem.appendChild(checkbox);
                listItem.appendChild(textSpan);
                listItem.appendChild(editBtn);
                listItem.appendChild(deleteBtn);
                listContainer.appendChild(listItem);
            });
            
            // Auto-select all relationships when loading a file
            const checkboxes = document.querySelectorAll('#relationshipList .list-group-item input[type="checkbox"]');
            checkboxes.forEach(checkbox => checkbox.checked = false);
        };
        reader.readAsText(file);
    }
});

function editRelationship(index) {
    const newValue = prompt('Edit relationship:', relationships[index]);
    if (newValue && newValue.trim() && newValue.includes('|')) {
        // Validate format before updating
        const parts = newValue.split('|');
        if (parts.length >= 3) {
            relationships[index] = newValue;
            document.querySelectorAll('#relationshipList .list-group-item span')[index].textContent = newValue;
            renderSelectedRelationships();
        } else {
            alert('Invalid format. Please use the format: source|story|target|date');
        }
    }
}

function deleteRelationship(index) {
    // Remove the relationship from the array
    relationships.splice(index, 1);
    
    // Remove the list item from the DOM
    document.querySelectorAll('#relationshipList .list-group-item')[index].remove();
    
    // Update the data-index attributes of all remaining checkboxes
    const checkboxes = document.querySelectorAll('#relationshipList .list-group-item input[type="checkbox"]');
    checkboxes.forEach((checkbox, i) => {
        checkbox.dataset.index = i;
    });
    
    // Update the graph
    renderSelectedRelationships();
}

document.getElementById('visualizeBtn').addEventListener('click', function() {
    renderSelectedRelationships();
});

function renderSelectedRelationships() {
    // Get all checked checkboxes and ensure they have valid indices
    const selectedRelationships = Array.from(document.querySelectorAll('#relationshipList .list-group-item input:checked'))
        .filter(checkbox => {
            const index = parseInt(checkbox.dataset.index);
            return !isNaN(index) && index >= 0 && index < relationships.length;
        })
        .map(checkbox => relationships[parseInt(checkbox.dataset.index)]);

    // Log for debugging
    console.log(`Selected ${selectedRelationships.length} relationships`);
    
    renderGraph(selectedRelationships);
}

function renderGraph(selectedRelationships) {
    const graphContainer = document.getElementById('graphContainer');
    const isFullscreen = graphContainer.classList.contains('fullscreen');
    
    graphContainer.innerHTML = ''; // Clear previous graph
    
    // Add instructions back after clearing
    addInstructions();
    
    // Skip rendering if no relationships are selected
    if (selectedRelationships.length === 0) {
        const noDataMessage = document.createElement('div');
        noDataMessage.className = 'alert alert-info mt-3';
        noDataMessage.textContent = 'Select relationships from the list to visualize them in the graph.';
        graphContainer.appendChild(noDataMessage);
        return;
    }
    
    // Add a title when in fullscreen mode
    if (isFullscreen) {
        const title = document.createElement('h1');
        title.className = 'mb-4';
        title.textContent = 'Graph Visualization (Fullscreen Mode)';
        title.style.marginTop = '30px';
        graphContainer.insertBefore(title, graphContainer.firstChild);
    }

    const nodesMap = new Map();
    const links = [];

    // Process each selected relationship
    selectedRelationships.forEach(rel => {
        // Skip invalid relationships
        if (!rel || !rel.includes('|')) return;
        
        const parts = rel.split('|');
        // Make sure we have at least source, label, target
        if (parts.length < 3) return;
        
        const [source, label, target, timestamp] = parts;

        if (!nodesMap.has(source)) {
            nodesMap.set(source, { id: source });
        }
        if (!nodesMap.has(target)) {
            nodesMap.set(target, { id: target });
        }

        links.push({ source, target, label, timestamp });
    });

    const nodes = Array.from(nodesMap.values());

    // Exit early if no valid data to display
    if (nodes.length === 0) {
        const noDataMessage = document.createElement('div');
        noDataMessage.className = 'alert alert-warning mt-3';
        noDataMessage.textContent = 'No valid relationships found to visualize.';
        graphContainer.appendChild(noDataMessage);
        return;
    }

    const width = graphContainer.clientWidth;
    const height = graphContainer.clientHeight;

    // Create SVG with zoom functionality
    const svg = d3.select(graphContainer).append('svg')
        .attr('width', width)
        .attr('height', height)
        .call(d3.zoom()
            .scaleExtent([0.1, 10])
            .on('zoom', zoomed));

    // Create a g element to hold the graph
    const g = svg.append('g');

    // Function to handle zoom
    function zoomed(event) {
        g.attr('transform', event.transform);
    }

    const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2));

    // Add link elements
    const link = g.append('g')
        .selectAll('line')
        .data(links)
        .enter().append('line')
        .attr('stroke', '#999')
        .attr('stroke-width', 2);

    // Create link labels with click toggle
    const linkLabels = g.append('g')
        .selectAll('text')
        .data(links)
        .enter().append('text')
        .attr('font-size', '10px')
        .attr('fill', '#555')
        .text(d => d.label)
        .attr('text-anchor', 'middle')
        .attr('dy', -5)
        .style('opacity', 0) // Start with labels hidden
        .style('pointer-events', 'none');

    // Add node elements
    const node = g.append('g')
        .selectAll('circle')
        .data(nodes)
        .enter().append('circle')
        .attr('r', 8)
        .attr('fill', '#69b3a2')
        .call(d3.drag()
            .on('start', dragStarted)
            .on('drag', dragged)
            .on('end', dragEnded));

    // Create node labels with click toggle
    const nodeLabels = g.append('g')
        .selectAll('text')
        .data(nodes)
        .enter().append('text')
        .attr('font-size', '12px')
        .attr('fill', '#000')
        .text(d => d.id)
        .attr('text-anchor', 'middle')
        .attr('dy', -15)
        .style('opacity', 0) // Start with labels hidden
        .style('pointer-events', 'none');

    // Store visibility state
    let nodeLabelsVisible = false;
    let linkLabelsVisible = false;

    // Toggle node labels on node click
    node.on('click', function(event, d) {
        event.stopPropagation(); // Prevent container click from triggering
        
        nodeLabelsVisible = !nodeLabelsVisible;
        nodeLabels.style('opacity', nodeLabelsVisible ? 1 : 0);

        // Highlight the clicked node
        d3.select(this)
            .transition()
            .duration(200)
            .attr('fill', nodeLabelsVisible ? '#ff5733' : '#69b3a2');
    });

    // Toggle link labels on link click
    link.on('click', function(event, d) {
        event.stopPropagation(); // Prevent container click from triggering
        
        linkLabelsVisible = !linkLabelsVisible;
        linkLabels.style('opacity', linkLabelsVisible ? 1 : 0);

        // Highlight the clicked link
        d3.select(this)
            .transition()
            .duration(200)
            .attr('stroke', linkLabelsVisible ? '#ff5733' : '#999');
    });

    // Click on the background to hide all labels
    svg.on('click', function() {
        nodeLabelsVisible = false;
        linkLabelsVisible = false;
        nodeLabels.style('opacity', 0);
        linkLabels.style('opacity', 0);
        
        // Reset colors
        node.attr('fill', '#69b3a2');
        link.attr('stroke', '#999');
    });

    // Tooltip behavior on hover
    node.on('mouseover', function(event, d) {
        d3.select(this).attr('fill', '#ff5733');
        
        d3.select('body').append('div')
            .attr('class', 'tooltip')
            .style('position', 'absolute')
            .style('background', '#fff')
            .style('border', '1px solid #ddd')
            .style('padding', '5px')
            .style('pointer-events', 'none')
            .style('color', '#000')
            .style('z-index', 1000)
            .style('left', `${event.pageX + 10}px`)
            .style('top', `${event.pageY + 10}px`)
            .text(d.id);
    })
    .on('mouseout', function() {
        d3.select(this).attr('fill', nodeLabelsVisible ? '#ff5733' : '#69b3a2');
        d3.selectAll('.tooltip').remove();
    });

    link.on('mouseover', function(event, d) {
        d3.select(this).attr('stroke', '#ff5733');
        
        d3.select('body').append('div')
            .attr('class', 'tooltip')
            .style('position', 'absolute')
            .style('background', '#fff')
            .style('border', '1px solid #ddd')
            .style('padding', '5px')
            .style('pointer-events', 'none')
            .style('color', '#000')
            .style('z-index', 1000)
            .style('left', `${event.pageX + 10}px`)
            .style('top', `${event.pageY + 10}px`)
            .text(d.label);
    })
    .on('mouseout', function() {
        d3.select(this).attr('stroke', linkLabelsVisible ? '#ff5733' : '#999');
        d3.selectAll('.tooltip').remove();
    });

    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);

        node
            .attr('cx', d => d.x)
            .attr('cy', d => d.y);

        // Update label positions
        nodeLabels
            .attr('x', d => d.x)
            .attr('y', d => d.y - 15);

        linkLabels
            .attr('x', d => (d.source.x + d.target.x) / 2)
            .attr('y', d => (d.source.y + d.target.y) / 2);
    });

    function dragStarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    function dragEnded(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
}

// Function to add a new relationship from the form inputs
document.getElementById('addBtn').addEventListener('click', function() {
    const source = document.getElementById('sourceInput').value.trim();
    const story = document.getElementById('storyInput').value.trim();
    const target = document.getElementById('targetInput').value.trim();
    const date = document.getElementById('dateInput').value;
    
    if (source && story && target) {
        const formattedDate = date || new Date().toISOString().split('T')[0];
        const newRelationship = `${source}|${story}|${target}|${formattedDate}`;
        
        // Add to our relationships array
        relationships.push(newRelationship);
        
        // Create the list item
        const listContainer = document.getElementById('relationshipList');
        const index = relationships.length - 1;
        
        const listItem = document.createElement('li');
        listItem.className = 'list-group-item';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'form-check-input me-2';
        checkbox.dataset.index = index;
        checkbox.checked = true; // Auto-check new relationships
        checkbox.addEventListener('change', function() {
            renderSelectedRelationships();
        });

        const textSpan = document.createElement('span');
        textSpan.textContent = newRelationship;

        const editBtn = document.createElement('button');
        editBtn.textContent = 'Edit';
        editBtn.className = 'btn btn-sm btn-warning ms-2';
        editBtn.addEventListener('click', () => editRelationship(index));

        const deleteBtn = document.createElement('button');
        deleteBtn.textContent = 'Delete';
        deleteBtn.className = 'btn btn-sm btn-danger ms-2';
        deleteBtn.addEventListener('click', () => deleteRelationship(index));

        listItem.appendChild(checkbox);
        listItem.appendChild(textSpan);
        listItem.appendChild(editBtn);
        listItem.appendChild(deleteBtn);
        listContainer.appendChild(listItem);
        
        // Clear inputs
        document.getElementById('sourceInput').value = '';
        document.getElementById('storyInput').value = '';
        document.getElementById('targetInput').value = '';
        document.getElementById('dateInput').value = '';
        
        // Update the graph
        renderSelectedRelationships();
    }
});

// Add event listener for the Select All button
const selectAllBtn = document.getElementById('selectAllBtn');
selectAllBtn.addEventListener('click', function() {
    const checkboxes = document.querySelectorAll('#relationshipList .list-group-item input[type="checkbox"]');
    checkboxes.forEach(checkbox => checkbox.checked = true);
    renderSelectedRelationships();
});

// Add event listener for the Deselect All button
const deselectAllBtn = document.getElementById('deselectAllBtn');
deselectAllBtn.addEventListener('click', function() {
    const checkboxes = document.querySelectorAll('#relationshipList .list-group-item input[type="checkbox"]');
    checkboxes.forEach(checkbox => checkbox.checked = false);
    renderSelectedRelationships();
});

// Add a simple instruction text to explain how to use the visualization
function addInstructions() {
    const instructions = document.createElement('div');
    instructions.className = 'instructions';
    instructions.style.cssText = 'position: absolute; top: 40px; right: 10px; background: rgba(255, 255, 255, 0.8); padding: 10px; border-radius: 5px; font-size: 12px; z-index: 100;';
    instructions.innerHTML = `
        <p><strong>Instructions:</strong></p>
        <ul>
            <li>Click on nodes or links to toggle labels</li>
            <li>Scroll to zoom in/out</li>
            <li>Drag nodes to reposition</li>
            <li>Click fullscreen button to expand view</li>
        </ul>
    `;
    document.getElementById('graphContainer').appendChild(instructions);
    
    // Add fullscreen toggle button
    addFullscreenToggle();
}

function addFullscreenToggle() {
    const graphContainer = document.getElementById('graphContainer');
    
    // Create the fullscreen toggle button if it doesn't exist already
    if (!document.querySelector('.fullscreen-toggle')) {
        const toggleButton = document.createElement('button');
        toggleButton.className = 'fullscreen-toggle btn btn-sm btn-outline-secondary';
        toggleButton.innerHTML = '<i class="fa fa-expand"></i> Fullscreen';
        toggleButton.onclick = toggleFullscreen;
        
        graphContainer.appendChild(toggleButton);
    }
}

function toggleFullscreen(event) {
    const graphContainer = document.getElementById('graphContainer');
    const isFullscreen = graphContainer.classList.contains('fullscreen');
    const toggleButton = document.querySelector('.fullscreen-toggle');
    
    if (isFullscreen) {
        // Exit fullscreen
        graphContainer.classList.remove('fullscreen');
        toggleButton.innerHTML = '<i class="fa fa-expand"></i> Fullscreen';
        document.body.style.overflow = 'auto'; // Restore scrolling
    } else {
        // Enter fullscreen
        graphContainer.classList.add('fullscreen');
        toggleButton.innerHTML = '<i class="fa fa-compress"></i> Exit Fullscreen';
        document.body.style.overflow = 'hidden'; // Prevent page scrolling in fullscreen
    }
    
    // Re-render to adjust the graph to the new container size
    setTimeout(renderSelectedRelationships, 100);
    
    // Prevent the click from propagating to the graph
    if (event) {
        event.stopPropagation();
    }
}

// Call addInstructions after the graph is rendered
window.addEventListener('load', function() {
    // Initial instructions
    addInstructions();
});