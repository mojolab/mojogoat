// Function to render a graph visualization
function renderGraph(data) {
    const width = 800;
    const height = 500;

    const svg = d3.select("#graphContainer").append("svg")
        .attr("width", width)
        .attr("height", height);

    const simulation = d3.forceSimulation(data.nodes)
        .force("link", d3.forceLink(data.links).id(d => d.id).distance(100))
        .force("charge", d3.forceManyBody().strength(-300))
        .force("center", d3.forceCenter(width / 2, height / 2));

    const link = svg.append("g")
        .selectAll("line")
        .data(data.links)
        .enter().append("line")
        .attr("stroke", "#999")
        .attr("stroke-width", 2);

    const node = svg.append("g")
        .selectAll("circle")
        .data(data.nodes)
        .enter().append("circle")
        .attr("r", 10)
        .attr("fill", "#69b3a2")
        .call(d3.drag()
            .on("start", dragStarted)
            .on("drag", dragged)
            .on("end", dragEnded));  

    node.append("title")
        .text(d => d.id);

    node.on("click", function(event, d) {
        // Remove any existing label divs
        d3.selectAll(".label-div").remove();

        // Create a new label div
        const labelDiv = d3.select("body").append("div")
            .attr("class", "tooltip-mine")
            .style("position", "absolute")
            .style("background", "#fff")
            .style("border", "1px solid #ddd")
            .style("padding", "5px")
            .style("pointer-events", "none")
            .style("left", `${event.pageX + 10}px`)
            .style("top", `${event.pageY + 10}px`)
            .text(`Node: ${d.id}`);

        // Remove the label div when clicking elsewhere
        d3.select("body").on("click", function(event) {
            if (!event.target.closest("circle")) {
                d3.selectAll(".tooltip-mine").remove();
            }
        });
    });

    // Add labels for nodes
    const nodeLabels = svg.append("g")
        .selectAll("text")
        .data(data.nodes)
        .enter().append("text")
        .attr("x", d => d.x)
        .attr("y", d => d.y - 15) // Position above the node
        .attr("text-anchor", "middle")
        .attr("font-size", "12px")
        .attr("fill", "#000")
        .text(d => d.id);

    // Add labels for links
    const linkLabels = svg.append("g")
        .selectAll("text")
        .data(data.links)
        .enter().append("text")
        .attr("x", d => (d.source.x + d.target.x) / 2)
        .attr("y", d => (d.source.y + d.target.y) / 2)
        .attr("text-anchor", "middle")
        .attr("font-size", "10px")
        .attr("fill", "#555")
        .text(d => d.label || "");

    // Update labels on simulation tick
    simulation.on("tick", () => {
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        node
            .attr("cx", d => d.x)
            .attr("cy", d => d.y);

        nodeLabels
            .attr("x", d => d.x)
            .attr("y", d => d.y - 15);

        linkLabels
            .attr("x", d => (d.source.x + d.target.x) / 2)
            .attr("y", d => (d.source.y + d.target.y) / 2);
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

// Example usage
const exampleData = {
    nodes: [
        { id: "Node1" },
        { id: "Node2" },
        { id: "Node3" }
    ],
    links: [
        { source: "Node1", target: "Node2" },
        { source: "Node2", target: "Node3" }
    ]
};

renderGraph(exampleData);

// Add a deselect all button next to the select all button
const buttonContainer = d3.select("#buttonContainer");

buttonContainer.append("button")
    .attr("id", "deselectAllButton")
    .text("Deselect All")
    .on("click", () => {
        d3.selectAll("circle").classed("selected", false);
        d3.selectAll("line").classed("selected", false);
    });

// Update the visualize graph button to refresh the graph based on current selection
const visualizeButton = d3.select("#visualizeGraphButton");
visualizeButton.on("click", () => {
    const selectedNodes = d3.selectAll("circle.selected").data();
    const selectedLinks = d3.selectAll("line.selected").data();

    const filteredData = {
        nodes: selectedNodes,
        links: selectedLinks
    };

    d3.select("#graphContainer").select("svg").remove(); // Clear the existing graph
    renderGraph(filteredData); // Re-render the graph with the filtered data
});
