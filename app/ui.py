# ruff: noqa: E501
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["web"])


@router.get("/", response_class=HTMLResponse)
async def home() -> str:
    return HTML_PAGE


HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SecureRAG EvalOps</title>
  <style>
    :root { color-scheme: light; --bg:#fbfaf7; --panel:#fffdf8; --ink:#171717; --muted:#5c6269; --line:#ddd9cf; --green:#0f9f73; --blue:#2563eb; --amber:#d97706; --red:#dc2626; }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--bg); color:var(--ink); font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
    main { max-width:1180px; margin:0 auto; padding:24px; }
    header { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; }
    h1 { margin:0; font-size:28px; letter-spacing:-.03em; }
    .subtle { color:var(--muted); }
    .status-row { display:flex; gap:10px; align-items:center; }
    .pill { padding:7px 12px; border-radius:999px; background:#edf4ff; color:#1d4ed8; font-size:14px; }
    .healthy { background:#e9f8f2; color:#047857; }
    .tabs { display:flex; gap:6px; border-bottom:1px solid var(--line); margin-top:24px; }
    .tab { width:auto; background:transparent; border:1px solid transparent; padding:12px 18px; border-radius:12px 12px 0 0; color:var(--ink); font-weight:600; cursor:pointer; }
    .tab.active { border-color:var(--line); border-bottom-color:var(--bg); background:var(--panel); }
    .panel { display:none; }
    .panel.active { display:block; }
    .metric-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin:26px 0; }
    .metric { background:var(--panel); border:1px solid #efece5; border-radius:14px; padding:18px; }
    .metric-label { color:var(--muted); font-size:13px; text-transform:uppercase; letter-spacing:.08em; }
    .metric-value { font-size:28px; font-weight:700; margin-top:6px; }
    .card { background:var(--panel); border:1px solid var(--line); border-radius:18px; padding:20px; }
    .guard-row { display:grid; grid-template-columns:1.5fr .8fr .5fr; gap:14px; align-items:center; padding:14px 0; border-top:1px solid #ebe7dd; }
    .guard-row:first-of-type { border-top:none; }
    .guard-title { font-weight:650; }
    .guard-meta { color:var(--muted); font-size:14px; }
    .count { text-align:right; font-variant-numeric:tabular-nums; }
    .badge { justify-self:end; border-radius:999px; padding:6px 10px; background:#e9f8f2; color:#047857; font-size:13px; }
    .split { display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:20px; }
    label { display:block; font-size:14px; color:var(--muted); margin:12px 0 6px; }
    input, textarea, button { width:100%; border-radius:12px; border:1px solid var(--line); background:white; color:var(--ink); padding:11px 12px; }
    textarea { min-height:110px; resize:vertical; }
    button.action { background:#111827; color:white; border:none; cursor:pointer; margin-top:14px; }
    .inline-actions { display:flex; gap:10px; }
    .inline-actions button { width:auto; }
    .status { min-height:22px; margin-top:10px; color:var(--green); }
    .answer { white-space:pre-wrap; line-height:1.5; }
    .citation, .doc-row { border-top:1px solid #ebe7dd; margin-top:12px; padding-top:12px; }
    .doc-row button { width:auto; margin-left:10px; }
    .danger { background:#fff1f2; color:#be123c; border-color:#fecdd3; }
    .graph-layout { display:grid; grid-template-columns:minmax(0, 2fr) minmax(280px, .9fr); gap:18px; margin-top:20px; }
    .graph-stage { min-height:560px; border:1px solid var(--line); border-radius:18px; background:radial-gradient(circle at top left,#fffdf8,#f5efe5); overflow:hidden; }
    #graph-svg { width:100%; height:560px; display:block; }
    .graph-edge { stroke:#94a3b8; stroke-width:1.5; opacity:.8; }
    .graph-edge.active { stroke:var(--blue); stroke-width:2.5; opacity:1; }
    .graph-node circle { fill:#111827; stroke:white; stroke-width:2; cursor:pointer; }
    .graph-node text { font-size:12px; fill:#111827; pointer-events:none; }
    .graph-node.active circle { fill:var(--blue); }
    .graph-node.related circle { fill:var(--green); }
    .graph-side h3 { margin-top:0; }
    .graph-list { margin-top:14px; border-top:1px solid #ebe7dd; padding-top:12px; }
    .graph-chip { display:inline-block; margin:0 6px 6px 0; padding:5px 8px; border-radius:999px; background:#eef2ff; color:#3730a3; font-size:12px; }
    .graph-empty { display:flex; align-items:center; justify-content:center; min-height:560px; color:var(--muted); }
    .graph-hint { color:var(--muted); font-size:13px; margin-top:8px; }
    .toolbar { display:grid; grid-template-columns:minmax(220px,1fr) auto auto; gap:10px; align-items:end; }
    .toolbar button { width:auto; }
    @media (max-width:900px) { .metric-grid, .split, .graph-layout { grid-template-columns:1fr; } .guard-row { grid-template-columns:1fr; } .count, .badge { text-align:left; justify-self:start; } }
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>SecureRAG EvalOps</h1>
      <div class="subtle">enterprise · offline-first · <span style="color:var(--green)">● live</span></div>
    </div>
    <div class="status-row"><span class="pill" id="pipeline-count">0 collections</span><span class="pill healthy">healthy</span></div>
  </header>
  <nav class="tabs">
    <button class="tab active" data-tab="pipeline">Pipeline</button>
    <button class="tab" data-tab="evaluation">Evaluation</button>
    <button class="tab" data-tab="traces">Traces</button>
    <button class="tab" data-tab="guardrails">Guardrails</button>
    <button class="tab" data-tab="graph">Memory Graph</button>
  </nav>

  <section id="pipeline" class="panel active">
    <div class="split">
      <div class="card">
        <h2>Ingest</h2>
        <label for="file">File</label><input id="file" type="file" accept=".txt,.md,.pdf,.json,.py,.c,.cpp,.cc,.cxx,.java,.h,.hpp">
        <label for="namespace">Namespace</label><input id="namespace" value="real-docs">
        <label for="user-id">User ID</label><input id="user-id" value="demo-admin">
        <label for="api-token">API token</label><input id="api-token" type="password" placeholder="required outside local development">
        <label for="collection">Collection</label><input id="collection" value="default">
        <label for="retention-days">Retention days</label><input id="retention-days" type="number" min="0" placeholder="leave blank to keep forever">
        <div class="inline-actions"><button class="action" id="save-collection">Save collection</button><button class="action" id="ingest">Ingest file</button></div>
        <div id="ingest-status" class="status"></div>
      </div>
      <div class="card">
        <h2>Ask</h2>
        <label for="question">Question</label><textarea id="question" placeholder="What does this document say about ...?"></textarea>
        <button class="action" id="ask">Ask question</button>
        <div id="query-status" class="status"></div>
        <h3>Answer</h3><div id="answer" class="answer">No answer yet.</div><div id="citations"></div>
      </div>
    </div>
    <div class="card" style="margin-top:18px">
      <div class="inline-actions"><h2 style="flex:1">Documents</h2><button id="refresh-documents">Refresh</button></div>
      <div class="split">
        <div>
          <label for="cleanup-collection">Delete files from collection</label>
          <input id="cleanup-collection" placeholder="for example: default">
          <button class="danger" id="delete-collection-files">Delete collection files</button>
        </div>
        <div>
          <label for="cleanup-age">Delete files older than days</label>
          <input id="cleanup-age" type="number" min="0" placeholder="for example: 30">
          <button class="danger" id="delete-old-files">Delete older files</button>
        </div>
      </div>
      <div id="cleanup-status" class="status"></div>
      <div id="documents" class="status"></div>
    </div>
  </section>

  <section id="evaluation" class="panel">
    <div class="metric-grid">
      <div class="metric"><div class="metric-label">Latest run</div><div class="metric-value" id="eval-run">—</div></div>
      <div class="metric"><div class="metric-label">Latency p50</div><div class="metric-value" id="latency-p50">0</div></div>
      <div class="metric"><div class="metric-label">Latency p95</div><div class="metric-value" id="latency-p95">0</div></div>
      <div class="metric"><div class="metric-label">Samples</div><div class="metric-value" id="latency-samples">0</div></div>
    </div>
  </section>

  <section id="traces" class="panel">
    <div class="metric-grid">
      <div class="metric"><div class="metric-label">Cost events</div><div class="metric-value" id="cost-events">0</div></div>
      <div class="metric"><div class="metric-label">Estimated total</div><div class="metric-value" id="cost-total">$0</div></div>
      <div class="metric"><div class="metric-label">Chat</div><div class="metric-value" id="cost-chat">$0</div></div>
      <div class="metric"><div class="metric-label">Embeddings</div><div class="metric-value" id="cost-embeddings">$0</div></div>
    </div>
  </section>

  <section id="guardrails" class="panel">
    <div class="metric-grid">
      <div class="metric"><div class="metric-label">Queries blocked</div><div class="metric-value" id="queries-blocked">0</div></div>
      <div class="metric"><div class="metric-label">Injection attempts</div><div class="metric-value" id="injection-attempts">0</div></div>
      <div class="metric"><div class="metric-label">PII redacted</div><div class="metric-value" id="pii-redacted">0</div></div>
      <div class="metric"><div class="metric-label">Tool violations</div><div class="metric-value">0</div></div>
    </div>
    <div class="card">
      <h2>Guardrail checks</h2>
      <div class="guard-row"><div><div class="guard-title">Unsafe query filter</div><div class="guard-meta">Regex categories over user queries</div></div><div class="count" id="unsafe-count">0 blocked</div><div class="badge">active</div></div>
      <div class="guard-row"><div><div class="guard-title">Prompt injection detection</div><div class="guard-meta">Direct and indirect injection variants</div></div><div class="count" id="injection-count">0 blocked</div><div class="badge">active</div></div>
      <div class="guard-row"><div><div class="guard-title">PII redaction</div><div class="guard-meta">Email, phone, SSN, credit card candidates</div></div><div class="count" id="pii-count">0 redacted</div><div class="badge">active</div></div>
      <div class="guard-row"><div><div class="guard-title">Sensitive namespace isolation</div><div class="guard-meta">Authorization before retrieval</div></div><div class="count">0 violations</div><div class="badge">active</div></div>
    </div>
  </section>

  <section id="graph" class="panel">
    <div class="card">
      <div class="toolbar">
        <div>
          <label for="graph-search">Filter entities</label>
          <input id="graph-search" placeholder="for example: GitHub or PaymentService">
        </div>
        <button id="refresh-graph">Refresh graph</button>
        <button id="reset-graph">Reset view</button>
      </div>
      <div id="graph-status" class="status"></div>
      <div class="graph-hint">Drag nodes · wheel to zoom · drag empty space to pan · double-click a node to expand neighbors</div>
      <div class="graph-layout">
        <div class="graph-stage" id="graph-stage">
          <svg id="graph-svg" viewBox="0 0 900 560" aria-label="Graph memory visualization"></svg>
        </div>
        <div class="card graph-side">
          <h3>Selection</h3>
          <div id="graph-details" class="subtle">Click a node to inspect what the system remembers.</div>
        </div>
      </div>
    </div>
  </section>
</main>
<script>
const q=(selector)=>document.querySelector(selector),fileInput=q('#file'),namespaceInput=q('#namespace'),userInput=q('#user-id'),tokenInput=q('#api-token'),collectionInput=q('#collection'),retentionInput=q('#retention-days'),cleanupCollectionInput=q('#cleanup-collection'),cleanupAgeInput=q('#cleanup-age'),questionInput=q('#question'),graphSearchInput=q('#graph-search');
tokenInput.value=sessionStorage.getItem('api-token')||'';tokenInput.addEventListener('change',()=>sessionStorage.setItem('api-token',tokenInput.value));function authHeaders(extra={}){return tokenInput.value?{...extra,Authorization:`Bearer ${tokenInput.value}`}:{...extra}}
function sourceType(name){return name.split('.').pop().toLowerCase()} async function fileContent(file){if(sourceType(file.name)==='pdf'){const bytes=new Uint8Array(await file.arrayBuffer());let binary='';bytes.forEach((byte)=>binary+=String.fromCharCode(byte));return btoa(binary)}return file.text()}
async function loadMetrics(){const [guardrails,cost,latency,evalRun,collections]=await Promise.all([fetch('/api/v1/metrics/guardrails',{headers:authHeaders()}).then(r=>r.json()),fetch('/api/v1/metrics/cost',{headers:authHeaders()}).then(r=>r.json()),fetch('/api/v1/metrics/latency',{headers:authHeaders()}).then(r=>r.json()),fetch('/api/v1/metrics/eval',{headers:authHeaders()}).then(r=>r.json()),fetch(`/api/v1/collections?namespace=${encodeURIComponent(namespaceInput.value)}`,{headers:authHeaders()}).then(r=>r.json()).catch(()=>[])]);const injection=(guardrails.prompt_injection_detected||0)+(guardrails.indirect_injection_in_context||0);const unsafe=Object.entries(guardrails).filter(([key])=>key.startsWith('unsafe_query_')).reduce((sum,[,value])=>sum+value,0);const pii=guardrails.pii_redaction||0;q('#queries-blocked').textContent=String(injection+unsafe);q('#injection-attempts').textContent=String(injection);q('#pii-redacted').textContent=String(pii);q('#unsafe-count').textContent=`${unsafe} blocked`;q('#injection-count').textContent=`${injection} blocked`;q('#pii-count').textContent=`${pii} redacted`;q('#cost-events').textContent=String(cost.event_count||0);q('#cost-total').textContent=`$${Number(cost.estimated_total_usd||0).toFixed(2)}`;q('#cost-chat').textContent=`$${Number(cost.chat_usd||0).toFixed(2)}`;q('#cost-embeddings').textContent=`$${Number(cost.embedding_usd||0).toFixed(2)}`;q('#latency-p50').textContent=Number(latency.p50||0).toFixed(0);q('#latency-p95').textContent=Number(latency.p95||0).toFixed(0);q('#latency-samples').textContent=String(latency.sample_count||0);q('#eval-run').textContent=evalRun.run_id?evalRun.status:'none';q('#pipeline-count').textContent=`${collections.length||0} collections`}
async function refreshDocuments(){const response=await fetch(`/api/v1/documents?namespace=${encodeURIComponent(namespaceInput.value)}`,{headers:authHeaders()}),body=await response.json(),target=q('#documents');if(!response.ok){target.textContent=`${body.detail?.error||body.error||'error'}: ${body.detail?.reason||body.reason||'request failed'}`;return}target.innerHTML=body.length?body.map(doc=>`<div class="doc-row"><strong>${doc.source_filename}</strong> [${doc.collection_name||'unassigned'}] (${doc.chunk_count} chunks) · ingested ${new Date(doc.created_at).toLocaleString()}<button data-document-id="${doc.id}">Delete</button></div>`).join(''):'No documents in this namespace.';target.querySelectorAll('button[data-document-id]').forEach(button=>button.addEventListener('click',async()=>{if(!confirm('Delete this document and its retrieved chunks?')){return}await fetch(`/api/v1/documents/${button.dataset.documentId}`,{method:'DELETE',headers:authHeaders()});await refreshDocuments()}))}
async function cleanupDocuments(payload){const status=q('#cleanup-status');status.textContent='Checking matches...';const previewResponse=await fetch('/api/v1/documents/cleanup',{method:'POST',headers:authHeaders({'Content-Type':'application/json'}),body:JSON.stringify({namespace:namespaceInput.value,...payload,dry_run:true})}),preview=await previewResponse.json();if(!previewResponse.ok){status.textContent=`${preview.detail?.error||preview.error||'error'}: ${preview.detail?.reason||preview.reason||'request failed'}`;return}if(!preview.matched_documents){status.textContent='No matching documents.';return}if(!confirm(`Delete ${preview.matched_documents} matching document(s)? This cannot be undone.`)){status.textContent='Deletion cancelled.';return}status.textContent='Deleting...';const response=await fetch('/api/v1/documents/cleanup',{method:'POST',headers:authHeaders({'Content-Type':'application/json'}),body:JSON.stringify({namespace:namespaceInput.value,...payload,dry_run:false,confirm:true})}),body=await response.json();status.textContent=response.ok?`deleted ${body.deleted_documents} document(s)`: `${body.detail?.error||body.error||'error'}: ${body.detail?.reason||body.reason||'request failed'}`;if(response.ok){await refreshDocuments();await loadMetrics()}}
function escapeHtml(value){return value.replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]))}
const graphState={nodes:new Map(),edges:new Map(),positions:new Map(),velocities:new Map(),scale:1,offsetX:0,offsetY:0,dragNodeId:null,panning:false,lastPointer:null,animation:null};
function seededPosition(index,total){const angle=(Math.PI*2*index)/Math.max(total,1)-Math.PI/2,radius=Math.min(180,50+total*3);return{x:450+Math.cos(angle)*radius,y:280+Math.sin(angle)*radius}}
function resetGraphState(){graphState.nodes.clear();graphState.edges.clear();graphState.positions.clear();graphState.velocities.clear();graphState.scale=1;graphState.offsetX=0;graphState.offsetY=0}
function mergeGraphData(graph){const existing=graphState.nodes.size;graph.nodes.forEach((node,index)=>{if(!graphState.nodes.has(node.id)){graphState.nodes.set(node.id,node);graphState.positions.set(node.id,seededPosition(existing+index,existing+graph.nodes.length));graphState.velocities.set(node.id,{x:0,y:0})}else{graphState.nodes.set(node.id,node)}});graph.edges.forEach(edge=>graphState.edges.set(edge.id,edge))}
function graphToScreen(point){return{x:point.x*graphState.scale+graphState.offsetX,y:point.y*graphState.scale+graphState.offsetY}}
function screenToGraph(point){return{x:(point.x-graphState.offsetX)/graphState.scale,y:(point.y-graphState.offsetY)/graphState.scale}}
function drawGraph(){const stage=q('#graph-stage');if(!graphState.nodes.size){stage.innerHTML='<div class="graph-empty">No graph memory found for this namespace.</div>';return}if(!stage.querySelector('svg')){stage.innerHTML='<svg id="graph-svg" viewBox="0 0 900 560" aria-label="Graph memory visualization"></svg>'}const liveSvg=q('#graph-svg'),nodes=[...graphState.nodes.values()],edges=[...graphState.edges.values()];liveSvg.innerHTML=`<g transform="translate(${graphState.offsetX} ${graphState.offsetY}) scale(${graphState.scale})"><g>${edges.map(edge=>{const source=graphState.positions.get(edge.source),target=graphState.positions.get(edge.target);if(!source||!target){return''}return`<line class="graph-edge" data-edge-id="${edge.id}" x1="${source.x}" y1="${source.y}" x2="${target.x}" y2="${target.y}"></line>`}).join('')}</g><g>${nodes.map(node=>{const position=graphState.positions.get(node.id),radius=Math.min(24,10+node.mention_count);return`<g class="graph-node" data-node-id="${node.id}" transform="translate(${position.x},${position.y})"><circle r="${radius}"></circle><text x="0" y="${radius+18}" text-anchor="middle">${escapeHtml(node.label)}</text></g>`}).join('')}</g></g>`;wireGraphInteractions(liveSvg)}
function stepSimulation(){const nodes=[...graphState.nodes.values()],edges=[...graphState.edges.values()];nodes.forEach(left=>{const leftPos=graphState.positions.get(left.id),velocity=graphState.velocities.get(left.id);nodes.forEach(right=>{if(left.id===right.id){return}const rightPos=graphState.positions.get(right.id),dx=leftPos.x-rightPos.x,dy=leftPos.y-rightPos.y,distance=Math.max(18,Math.hypot(dx,dy)),force=1800/(distance*distance);velocity.x+=dx/distance*force;velocity.y+=dy/distance*force})});edges.forEach(edge=>{const source=graphState.positions.get(edge.source),target=graphState.positions.get(edge.target);if(!source||!target){return}const dx=target.x-source.x,dy=target.y-source.y,distance=Math.max(1,Math.hypot(dx,dy)),force=(distance-120)*0.004,sourceVelocity=graphState.velocities.get(edge.source),targetVelocity=graphState.velocities.get(edge.target);sourceVelocity.x+=dx/distance*force;sourceVelocity.y+=dy/distance*force;targetVelocity.x-=dx/distance*force;targetVelocity.y-=dy/distance*force});nodes.forEach(node=>{if(graphState.dragNodeId===node.id){return}const position=graphState.positions.get(node.id),velocity=graphState.velocities.get(node.id);velocity.x+=(450-position.x)*0.002;velocity.y+=(280-position.y)*0.002;velocity.x*=0.84;velocity.y*=0.84;position.x+=velocity.x;position.y+=velocity.y});drawGraph();graphState.animation=requestAnimationFrame(stepSimulation)}
function selectNode(nodeId){const liveSvg=q('#graph-svg'),details=q('#graph-details'),node=graphState.nodes.get(nodeId),edges=[...graphState.edges.values()].filter(edge=>edge.source===node.id||edge.target===node.id),relatedIds=new Set(edges.flatMap(edge=>[edge.source,edge.target]));liveSvg.querySelectorAll('.graph-node').forEach(element=>{element.classList.toggle('active',element.dataset.nodeId===node.id);element.classList.toggle('related',relatedIds.has(element.dataset.nodeId)&&element.dataset.nodeId!==node.id)});liveSvg.querySelectorAll('.graph-edge').forEach(element=>element.classList.toggle('active',edges.some(edge=>edge.id===element.dataset.edgeId)));details.innerHTML=`<h3>${escapeHtml(node.label)}</h3><div>${node.entity_type} · ${node.mention_count} mention(s)</div><button id="expand-node" class="action">Expand neighbors</button><div class="graph-list">${edges.length?edges.map(edge=>{const other=graphState.nodes.get(edge.source===node.id?edge.target:edge.source);return`<div class="citation"><span class="graph-chip">${escapeHtml(edge.relation_type.replaceAll('_',' '))}</span><strong>${escapeHtml(other.label)}</strong><br><span class="subtle">${escapeHtml(edge.source_filename)}</span><br>${escapeHtml(edge.snippet)}</div>`}).join(''):'No loaded relations yet. Expand this node to fetch its neighborhood.'}</div>`;q('#expand-node').addEventListener('click',()=>expandNode(node.id))}
function wireGraphInteractions(svg){svg.querySelectorAll('.graph-node').forEach(element=>{element.addEventListener('pointerdown',event=>{event.stopPropagation();graphState.dragNodeId=element.dataset.nodeId;graphState.lastPointer={x:event.clientX,y:event.clientY};element.setPointerCapture(event.pointerId)});element.addEventListener('click',event=>{event.stopPropagation();selectNode(element.dataset.nodeId)});element.addEventListener('dblclick',event=>{event.stopPropagation();expandNode(element.dataset.nodeId)})});svg.onpointerdown=event=>{graphState.panning=true;graphState.lastPointer={x:event.clientX,y:event.clientY}};svg.onpointermove=event=>{if(!graphState.lastPointer){return}const dx=event.clientX-graphState.lastPointer.x,dy=event.clientY-graphState.lastPointer.y;if(graphState.dragNodeId){const position=graphState.positions.get(graphState.dragNodeId);position.x+=dx/graphState.scale;position.y+=dy/graphState.scale}else if(graphState.panning){graphState.offsetX+=dx;graphState.offsetY+=dy}graphState.lastPointer={x:event.clientX,y:event.clientY};drawGraph()};svg.onpointerup=()=>{graphState.dragNodeId=null;graphState.panning=false;graphState.lastPointer=null};svg.onwheel=event=>{event.preventDefault();const nextScale=Math.min(2.5,Math.max(.35,graphState.scale*(event.deltaY<0?1.1:.9))),before=screenToGraph({x:event.offsetX,y:event.offsetY});graphState.scale=nextScale;const after=graphToScreen(before);graphState.offsetX+=event.offsetX-after.x;graphState.offsetY+=event.offsetY-after.y;drawGraph()}}
function renderGraph(graph,{append=false}={}){if(!append){resetGraphState()}mergeGraphData(graph);if(graphState.animation){cancelAnimationFrame(graphState.animation)}drawGraph();graphState.animation=requestAnimationFrame(stepSimulation)}
async function fetchGraph(params){const response=await fetch(`/api/v1/graph?${params.toString()}`,{headers:authHeaders()}),body=await response.json();if(!response.ok){throw new Error(`${body.detail?.error||body.error||'error'}: ${body.detail?.reason||body.reason||'request failed'}`)}return body}
async function loadGraph(){const status=q('#graph-status');status.textContent='Loading graph...';const params=new URLSearchParams({namespace:namespaceInput.value,limit:'80'});if(graphSearchInput.value){params.set('search',graphSearchInput.value)}try{const body=await fetchGraph(params);status.textContent=`${body.nodes.length} entities · ${body.edges.length} relations`;renderGraph(body)}catch(error){status.textContent=error.message}}
async function expandNode(entityId){const status=q('#graph-status');status.textContent='Expanding neighborhood...';const params=new URLSearchParams({namespace:namespaceInput.value,entity_id:entityId,limit:'80'});try{const body=await fetchGraph(params);mergeGraphData(body);status.textContent=`${graphState.nodes.size} entities · ${graphState.edges.size} relations loaded`;drawGraph();selectNode(entityId)}catch(error){status.textContent=error.message}}
q('#save-collection').addEventListener('click',async()=>{await fetch('/api/v1/collections',{method:'POST',headers:authHeaders({'Content-Type':'application/json'}),body:JSON.stringify({namespace:namespaceInput.value,name:collectionInput.value,retention_days:retentionInput.value?Number(retentionInput.value):null})});await refreshDocuments();await loadMetrics()});
q('#ingest').addEventListener('click',async()=>{const file=fileInput.files[0],status=q('#ingest-status');if(!file){status.textContent='Choose a file first.';return}status.textContent='Ingesting...';const response=await fetch('/api/v1/ingest',{method:'POST',headers:authHeaders({'Content-Type':'application/json'}),body:JSON.stringify({source_type:sourceType(file.name),content:await fileContent(file),namespace:namespaceInput.value,collection_name:collectionInput.value,source_filename:file.name,metadata:{}})}),body=await response.json();status.textContent=response.ok?`${body.status}: ${body.chunk_count} chunk(s)`: `${body.detail?.error||body.error||'error'}: ${body.detail?.reason||body.reason||'request failed'}`;if(response.ok){await refreshDocuments()}});
q('#ask').addEventListener('click',async()=>{const status=q('#query-status');status.textContent='Asking...';const response=await fetch('/api/v1/query',{method:'POST',headers:authHeaders({'Content-Type':'application/json'}),body:JSON.stringify({query:questionInput.value,namespace:namespaceInput.value})}),body=await response.json();if(!response.ok){status.textContent=`${body.detail?.error||body.error||'error'}: ${body.detail?.reason||body.reason||'request failed'}`;await loadMetrics();return}status.textContent=`trace ${body.trace_id} • ${body.latency_ms.toFixed(1)} ms`;q('#answer').textContent=body.answer;q('#citations').innerHTML=body.citations.map(c=>`<div class="citation"><strong>[${c.index}] ${c.source_filename}</strong><br>${c.snippet}<br>score: ${c.score.toFixed(3)}</div>`).join('');await loadMetrics()});
q('#refresh-documents').addEventListener('click',refreshDocuments);q('#refresh-graph').addEventListener('click',loadGraph);q('#reset-graph').addEventListener('click',()=>{graphSearchInput.value='';loadGraph()});document.querySelectorAll('.tab').forEach(tab=>tab.addEventListener('click',()=>{document.querySelectorAll('.tab,.panel').forEach(node=>node.classList.remove('active'));tab.classList.add('active');q(`#${tab.dataset.tab}`).classList.add('active');if(tab.dataset.tab==='graph'){loadGraph()}else{loadMetrics()}}));refreshDocuments();loadMetrics();
q('#delete-collection-files').addEventListener('click',async()=>{if(!cleanupCollectionInput.value){q('#cleanup-status').textContent='Enter a collection name first.';return}await cleanupDocuments({collection_name:cleanupCollectionInput.value})});
q('#delete-old-files').addEventListener('click',async()=>{if(!cleanupAgeInput.value){q('#cleanup-status').textContent='Enter an age in days first.';return}await cleanupDocuments({older_than_days:Number(cleanupAgeInput.value)})});
</script>
</body></html>"""
