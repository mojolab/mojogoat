const relationships = [];

document.getElementById('fileInput').addEventListener('change', function(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const lines = e.target.result.split('\n');
            const listContainer = document.getElementById('relationshipList');
            listContainer.innerHTML = '';
            relationships.length = 0;
            lines.forEach((line, index) => {
                if (line.trim()) {
                    relationships.push(line);
                    const listItem = document.createElement('li');
                    listItem.className = 'list-group-item';

                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.className = 'form-check-input me-2';
                    checkbox.dataset.index = index;

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
                }
            });
        };
        reader.readAsText(file);
    }
});

function editRelationship(index) {
    const newValue = prompt('Edit relationship:', relationships[index]);
    if (newValue) {
        relationships[index] = newValue;
        document.querySelectorAll('#relationshipList .list-group-item span')[index].textContent = newValue;
    }
}

function deleteRelationship(index) {
    relationships.splice(index, 1);
    document.querySelectorAll('#relationshipList .list-group-item')[index].remove();
}

document.getElementById('visualizeBtn').addEventListener('click', function() {
    const selectedRelationships = Array.from(document.querySelectorAll('#relationshipList .list-group-item input:checked'))
        .map(checkbox => relationships[checkbox.dataset.index]);

    renderGraph(selectedRelationships);
});

function renderGraph(selectedRelationships) {
    const graphContainer = document.getElementById('graphContainer');
    graphContainer.innerHTML = ''; // Clear previous graph

    const nodesMap = new Map();
    const links = [];

    selectedRelationships.forEach(rel => {
        const [source, label, target, timestamp] = rel.split('|');

        if (!nodesMap.has(source)) {
            nodesMap.set(source, { id: source });
        }
        if (!nodesMap.has(target)) {
            nodesMap.set(target, { id: target });
        }

        links.push({ source, target, label, timestamp });
    });

    const nodes = Array.from(nodesMap.values());

    const width = graphContainer.clientWidth;
    const height = graphContainer.clientHeight;

    const svg = d3.select(graphContainer).append('svg')
        .attr('width', width)
        .attr('height', height);

    const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2));

    const link = svg.append('g')
        .selectAll('line')
        .data(links)
        .enter().append('line')
        .attr('stroke', '#999')
        .attr('stroke-width', 2)
        .on('mouseover', function (event, d) {
            const tooltip = d3.select('body').append('div')
                .attr('class', 'tooltip')
                .style('position', 'absolute')
                .style('background', '#fff')
                .style('border', '1px solid #ddd')
                .style('padding', '5px')
                .style('pointer-events', 'none')
                .style('color', '#000') // Ensure text is visible
                .text(d.label);

            d3.select(this).attr('stroke', '#ff5733');

            d3.select(this).on('mousemove', function (event) {
                tooltip.style('left', `${event.pageX + 10}px`)
                    .style('top', `${event.pageY + 10}px`);
            });
        })
        .on('mouseout', function () {
            d3.select(this).attr('stroke', '#999');
            d3.selectAll('.tooltip').remove();
        })
        .on('click', function (event, d) {
            const popup = d3.select('body').append('div')
                .attr('class', 'popup')
                .style('position', 'absolute')
                .style('background', '#fff')
                .style('border', '1px solid #ddd')
                .style('padding', '10px')
                .style('color', '#000') // Ensure text is visible
                .html(`<strong>Relationship:</strong> ${d.label}<br><strong>Timestamp:</strong> ${d.timestamp}`);

            popup.style('left', `${event.pageX + 10}px`)
                .style('top', `${event.pageY + 10}px`);

            d3.select('body').on('click', function () {
                popup.remove();
            });
        });

    const node = svg.append('g')
        .selectAll('circle')
        .data(nodes)
        .enter().append('circle')
        .attr('r', 8)
        .attr('fill', '#69b3a2')
        .call(d3.drag()
            .on('start', dragStarted)
            .on('drag', dragged)
            .on('end', dragEnded))
        .on('mouseover', function (event, d) {
            const tooltip = d3.select('body').append('div')
                .attr('class', 'tooltip')
                .style('position', 'absolute')
                .style('background', '#fff')
                .style('border', '1px solid #ddd')
                .style('padding', '5px')
                .style('pointer-events', 'none')
                .style('color', '#000') // Ensure text is visible
                .text(d.id);

            d3.select(this).attr('fill', '#ff5733');

            d3.select(this).on('mousemove', function (event) {
                tooltip.style('left', `${event.pageX + 10}px`)
                    .style('top', `${event.pageY + 10}px`);
            });
        })
        .on('mouseout', function () {
            d3.select(this).attr('fill', '#69b3a2');
            d3.selectAll('.tooltip').remove();
        })
        .on('click', function (event, d) {
            const popup = d3.select('body').append('div')
                .attr('class', 'popup')
                .style('position', 'absolute')
                .style('background', '#fff')
                .style('border', '1px solid #ddd')
                .style('padding', '10px')
                .style('color', '#000') // Ensure text is visible
                .text(`Node: ${d.id}`);

            popup.style('left', `${event.pageX + 10}px`)
                .style('top', `${event.pageY + 10}px`);

            d3.select('body').on('click', function () {
                popup.remove();
            });
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

// Add event listener for the Select All button
const selectAllBtn = document.getElementById('selectAllBtn');
selectAllBtn.addEventListener('click', function() {
    const checkboxes = document.querySelectorAll('#relationshipList .list-group-item input[type="checkbox"]');
    checkboxes.forEach(checkbox => checkbox.checked = true);
});
