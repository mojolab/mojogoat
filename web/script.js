let relationships = [];
let currentFile = null;

// DOM Elements
const fileInput = document.getElementById('fileInput');
const saveBtn = document.getElementById('saveBtn');
const addBtn = document.getElementById('addBtn');
const relationshipsList = document.getElementById('relationshipsList');
const sourceInput = document.getElementById('sourceInput');
const storyInput = document.getElementById('storyInput');
const targetInput = document.getElementById('targetInput');
const dateInput = document.getElementById('dateInput');

// Set today's date as default
dateInput.valueAsDate = new Date();

// File input handler
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    currentFile = file;
    const reader = new FileReader();
    
    reader.onload = (e) => {
        const content = e.target.result;
        relationships = content.split('\n')
            .filter(line => line.trim())
            .map(line => {
                const [source, story, target, timestamp] = line.split('|');
                return { source, story, target, timestamp };
            });
        
        renderRelationships();
        saveBtn.disabled = false;
    };
    
    reader.readAsText(file);
});

// Add new relationship
addBtn.addEventListener('click', () => {
    const source = sourceInput.value.trim();
    const story = storyInput.value.trim();
    const target = targetInput.value.trim();
    const date = new Date(dateInput.value);
    
    if (!source || !story || !target || !date) {
        alert('Please fill in all fields');
        return;
    }
    
    const timestamp = date.toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
    }).replace(/ /g, '-');
    
    relationships.push({ source, story, target, timestamp });
    renderRelationships();
    
    // Clear inputs
    sourceInput.value = '';
    storyInput.value = '';
    targetInput.value = '';
    dateInput.valueAsDate = new Date();
    
    saveBtn.disabled = false;
});

// Save changes
saveBtn.addEventListener('click', () => {
    const content = relationships
        .map(r => `${r.source}|${r.story}|${r.target}|${r.timestamp}`)
        .join('\n');
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = currentFile ? currentFile.name : 'relationships.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
});

// Delete relationship
function deleteRelationship(index) {
    relationships.splice(index, 1);
    renderRelationships();
    saveBtn.disabled = false;
}

// Render relationships list
function renderRelationships() {
    relationshipsList.innerHTML = relationships
        .map((r, i) => `
            <div class="relationship-card">
                <div class="row align-items-center">
                    <div class="col-md-11">
                        <strong>${r.source}</strong> |
                        ${r.story} |
                        <strong>${r.target}</strong> |
                        <span class="text-muted">${r.timestamp}</span>
                    </div>
                    <div class="col-md-1 text-end">
                        <button class="btn btn-danger btn-sm" onclick="deleteRelationship(${i})">Delete</button>
                    </div>
                </div>
            </div>
        `)
        .join('');
} 