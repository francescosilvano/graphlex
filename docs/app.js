const exampleCsv = [
  'text',
  'Network analysis reveals relationships in data',
  'Research methods support reliable data analysis',
  'Graph models reveal relationships between data points',
  'Good research combines data and analysis'
].join('\n');

const elements = {
  file: document.querySelector('#csv-file'),
  keywords: document.querySelector('#keywords'),
  analyze: document.querySelector('#analyze'),
  loadExample: document.querySelector('#load-example'),
  status: document.querySelector('#status'),
  results: document.querySelector('#results'),
  summary: document.querySelector('#summary'),
  network: document.querySelector('#network'),
  keywordMetrics: document.querySelector('#keyword-metrics'),
  edgeMetrics: document.querySelector('#edge-metrics')
};

function parseCsv(csv) {
  const rows = [];
  let row = [];
  let value = '';
  let quoted = false;

  for (let index = 0; index < csv.length; index += 1) {
    const character = csv[index];
    const next = csv[index + 1];
    if (character === '"' && quoted && next === '"') {
      value += '"';
      index += 1;
    } else if (character === '"') {
      quoted = !quoted;
    } else if (character === ',' && !quoted) {
      row.push(value);
      value = '';
    } else if ((character === '\n' || character === '\r') && !quoted) {
      if (character === '\r' && next === '\n') index += 1;
      row.push(value);
      if (row.some((cell) => cell.trim() !== '')) rows.push(row);
      row = [];
      value = '';
    } else {
      value += character;
    }
  }
  row.push(value);
  if (row.some((cell) => cell.trim() !== '')) rows.push(row);

  if (!rows.length) throw new Error('The CSV does not contain any rows.');
  return rows.map((cells) => cells.join(' ').trim()).filter(Boolean);
}

function getKeywords() {
  return [...new Set(elements.keywords.value.split(',').map((keyword) => keyword.trim()).filter(Boolean))];
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  })[character]);
}

function analyze(documents, keywords) {
  const nodes = keywords.map((keyword) => ({ keyword, documents: 0, degree: 0, strength: 0 }));
  const edges = [];
  const lookup = new Map(nodes.map((node) => [node.keyword, node]));

  documents.forEach((document) => {
    const text = document.toLocaleLowerCase();
    const matches = keywords.filter((keyword) => text.includes(keyword.toLocaleLowerCase()));
    matches.forEach((keyword) => { lookup.get(keyword).documents += 1; });
    for (let left = 0; left < matches.length; left += 1) {
      for (let right = left + 1; right < matches.length; right += 1) {
        const first = matches[left];
        const second = matches[right];
        const existing = edges.find((edge) => edge.left === first && edge.right === second);
        if (existing) existing.count += 1;
        else edges.push({ left: first, right: second, count: 1 });
      }
    }
  });

  edges.forEach((edge) => {
    lookup.get(edge.left).degree += 1;
    lookup.get(edge.right).degree += 1;
    lookup.get(edge.left).strength += edge.count;
    lookup.get(edge.right).strength += edge.count;
  });

  return { nodes, edges };
}

function renderSummary(documents, network) {
  const possibleEdges = network.nodes.length * (network.nodes.length - 1) / 2;
  const density = possibleEdges ? network.edges.length / possibleEdges : 0;
  const cards = [
    ['Documents', documents.length],
    ['Keywords', network.nodes.length],
    ['Edges', network.edges.length],
    ['Density', density.toFixed(3)]
  ];
  elements.summary.innerHTML = cards.map(([label, value]) => `
    <div class="col-6 col-md-3"><div class="card"><div class="card-body">
      <div class="text-body-secondary small">${label}</div><div class="fs-3">${value}</div>
    </div></div></div>`).join('');
}

function renderTables(network) {
  const sortedNodes = [...network.nodes].sort((left, right) => right.strength - left.strength || right.documents - left.documents);
  elements.keywordMetrics.innerHTML = sortedNodes.map((node) => `<tr><td>${escapeHtml(node.keyword)}</td><td>${node.documents}</td><td>${node.degree}</td><td>${node.strength}</td></tr>`).join('');
  elements.edgeMetrics.innerHTML = [...network.edges].sort((left, right) => right.count - left.count)
    .map((edge) => `<tr><td>${escapeHtml(edge.left)}</td><td>${escapeHtml(edge.right)}</td><td>${edge.count}</td></tr>`).join('');
}

function renderNetwork(network) {
  const svg = elements.network;
  const center = { x: 360, y: 210 };
  const radius = Math.min(165, 30 + network.nodes.length * 10);
  const positions = new Map();
  const maxDocuments = Math.max(...network.nodes.map((node) => node.documents), 1);
  network.nodes.forEach((node, index) => {
    const angle = -Math.PI / 2 + (index * 2 * Math.PI) / Math.max(network.nodes.length, 1);
    positions.set(node.keyword, { x: center.x + radius * Math.cos(angle), y: center.y + radius * Math.sin(angle) });
  });
  const edgeLines = network.edges.map((edge) => {
    const start = positions.get(edge.left);
    const end = positions.get(edge.right);
    return `<line x1="${start.x}" y1="${start.y}" x2="${end.x}" y2="${end.y}" stroke="currentColor" stroke-opacity="0.35" stroke-width="${1 + edge.count}" />`;
  }).join('');
  const nodeGroups = network.nodes.map((node) => {
    const position = positions.get(node.keyword);
    const size = 7 + (node.documents / maxDocuments) * 14;
    return `<g><circle cx="${position.x}" cy="${position.y}" r="${size}" fill="currentColor" opacity="0.8" /><text x="${position.x}" y="${position.y + size + 15}" text-anchor="middle" font-size="12">${escapeHtml(node.keyword)}</text></g>`;
  }).join('');
  svg.innerHTML = `<rect width="720" height="420" fill="white" />${edgeLines}${nodeGroups}`;
}

async function runAnalysis(csv) {
  try {
    const documents = parseCsv(csv);
    const keywords = getKeywords();
    if (!keywords.length) throw new Error('Enter at least one keyword.');
    const network = analyze(documents, keywords);
    renderSummary(documents, network);
    renderTables(network);
    renderNetwork(network);
    elements.results.classList.remove('d-none');
    elements.status.className = 'mt-3 alert alert-success';
    elements.status.textContent = `Analyzed ${documents.length} documents.`;
  } catch (error) {
    elements.status.className = 'mt-3 alert alert-danger';
    elements.status.textContent = error.message;
  }
}

elements.analyze.addEventListener('click', async () => {
  if (!elements.file.files.length) {
    elements.status.className = 'mt-3 alert alert-warning';
    elements.status.textContent = 'Choose a CSV file first, or load the example.';
    return;
  }
  await runAnalysis(await elements.file.files[0].text());
});

elements.loadExample.addEventListener('click', () => runAnalysis(exampleCsv));