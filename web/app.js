// ===== Front complet =====

const ENDPOINT = '/api/aba/run'; // endpoint backend fixe

// === Sélecteurs DOM ===
const elInput   = document.getElementById('inputJson');
const elFile    = document.getElementById('fileInput');
const elBtnEx   = document.getElementById('btnLoadExample');
const elBtnCalc = document.getElementById('btnCalc');
const elStatus  = document.getElementById('status');

const elSummary = document.getElementById('summary');
const elArgs    = document.getElementById('arguments');
const elAtks    = document.getElementById('attacks');

const optNonCirc = document.getElementById('optNonCirc');
const optAtomic  = document.getElementById('optAtomic');
const optPrefs   = document.getElementById('optPrefs');

// ---------- PARSEUR : format prof ou JSON ----------
function parseInputToJson(text) {
  const t = (text || '').trim();
  if (!t) throw new Error('Entrée vide.');
  const first = t[0];
  if (first === '{' || first === '[') return JSON.parse(t);
  return parseABAPlain(t);
}

function parseABAPlain(src) {
  const lines = src.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
  const out = {
    literals: [],
    assumptions: [],
    contraries: {},
    rules: [],
    preferences: {}
  };
  const lits = new Set();
  let prefString = null;

  const listFromBrackets = (s) =>
    s.replace(/^\[/, '').replace(/\]$/, '')
     .split(',').map(x => x.trim()).filter(Boolean);

  for (const line of lines) {
    let m;

    // L: [...]
    m = line.match(/^L\s*:\s*\[(.+)\]\s*$/i);
    if (m) { listFromBrackets(m[1]).forEach(x => lits.add(x)); continue; }

    // A: [...]
    m = line.match(/^A\s*:\s*\[(.+)\]\s*$/i);
    if (m) { const arr = listFromBrackets(m[1]); out.assumptions = arr; arr.forEach(x => lits.add(x)); continue; }

    // C(a): r
    m = line.match(/^C\s*\(\s*([A-Za-z0-9_]+)\s*\)\s*:\s*([A-Za-z0-9_]+)\s*$/i);
    if (m) { out.contraries[m[1]] = m[2]; lits.add(m[1]); lits.add(m[2]); continue; }

    // [r1]: p <- q,a
    m = line.match(/^\s*\[[^\]]*\]\s*:\s*([A-Za-z0-9_]+)\s*<-\s*(.*)\s*$/);
    if (m) {
      const head = m[1];
      const bodyStr = m[2] || '';
      const body = bodyStr.trim() === '' ? [] :
                   bodyStr.split(',').map(x => x.trim()).filter(Boolean);
      out.rules.push({ head, body });
      lits.add(head); body.forEach(x => lits.add(x));
      continue;
    }

    // PREF: a > b
    m = line.match(/^PREF\s*:\s*(.+)\s*$/i);
    if (m) { prefString = m[1].trim(); continue; }
  }

  if (out.literals.length === 0) out.literals = Array.from(lits);
  out.preferences = prefString ?? {};

  return out;
}

// === Exemple texte ===
const SAMPLE_TEXT =
`L: [a,b,c,q,p,r,s,t]
A: [a,b,c]
C(a): r
C(b): s
C(c): t
[r1]: p <- q,a
[r2]: q <-
[r3]: r <- b,c
[r4]: t <- p,c
[r5]: s <- t
PREF: a > b`;

// === Gestion des fichiers et bouton exemple ===
elFile.addEventListener('change', async (ev) => {
  const file = ev.target.files?.[0];
  if(!file) return;
  elInput.value = await file.text();
});

elBtnEx.addEventListener('click', () => { elInput.value = SAMPLE_TEXT; });

// === Calculer (envoie au backend) ===
elBtnCalc.addEventListener('click', async () => {
  clearOutputs();

  let payload;
  try { payload = parseInputToJson(elInput.value); }
  catch(e) { setStatus('Entrée invalide — ' + e.message, 'warn'); return; }

  payload.__options = {
    do_non_circular: optNonCirc.checked,
    do_atomic: optAtomic.checked,
    use_preferences: optPrefs.checked
  };


  try {
    const res = await fetch(ENDPOINT, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    if(!res.ok){ throw new Error(`HTTP ${res.status}`); }
    const out = await res.json();
    renderAll(out);
  } catch(err) {
    console.error(err);
    setStatus('Erreur backend : ' + err.message, 'danger');
  }
});

// === Helpers UI ===
function setStatus(text, kind='info'){
  const cls = { ok:'badge ok', warn:'badge warn', danger:'badge danger', info:'badge info' };
  elStatus.innerHTML = `<span class="${cls[kind]||cls.info}">${text}</span>`;
}

function clearOutputs(){
  elSummary.innerHTML = '';
  elArgs.innerHTML = '';
  elAtks.innerHTML = '';
  const g2d = document.getElementById('graph2d');
  if (g2d) g2d.innerHTML = '';
  if (__cy) { __cy.destroy(); __cy = null; }
  setStatus('');
}

function escapeHtml(s){
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#039;');
}

// === Tableaux ===
function renderSummary(j){
  const L = (j.literals||[]).join(', ');
  const A = (j.assumptions||[]).join(', ');
  const C = Object.entries(j.contraries||{}).map(([a,c])=>`C(${a})=${c}`).join(', ');
  const P = j.preferences ? JSON.stringify(j.preferences) : '—';
  elSummary.innerHTML = `
    <table class="table">
      <thead><tr><th>Élément</th><th>Valeur</th></tr></thead>
      <tbody>
        <tr><td>Littéraux (L)</td><td>${escapeHtml(L)}</td></tr>
        <tr><td>Assumptions (A)</td><td>${escapeHtml(A)}</td></tr>
        <tr><td>Contraires</td><td>${escapeHtml(C)}</td></tr>
        <tr><td>Préférences</td><td><code>${escapeHtml(P)}</code></td></tr>
      </tbody>
    </table>`;
}

function renderArguments(j){
  const rows = (j.arguments||[]).map(a=>{
    const sup = `{${(a.assumptions||[]).join(', ')}}`;
    return `<tr>
      <td>a${a.id+1}</td><td><code>${escapeHtml(sup)}</code></td>
      <td>⊢</td><td><strong>${escapeHtml(a.conclusion)}</strong></td>
    </tr>`;
  }).join('');
  elArgs.innerHTML = `
    <table class="table">
      <thead><tr><th>ID</th><th>Support</th><th></th><th>Conclusion</th></tr></thead>
      <tbody>${rows || `<tr><td colspan="4">—</td></tr>`}</tbody>
    </table>`;
}

function renderAttacks(j){
  const id2 = new Map((j.arguments||[]).map(a=>[a.id, a]));
  const rows = (j.attacks||[]).map(t=>{
    const A = id2.get(t.attacker), B = id2.get(t.target);
    const supA = `{${(A?.assumptions||[]).join(', ')}}`;
    const supB = `{${(B?.assumptions||[]).join(', ')}}`;
    const kind = t.kind === 'reverse'
      ? `<span class="badge danger">reverse</span>`
      : `<span class="badge info">normal</span>`;
    return `<tr>
      <td>${kind}</td>
      <td>a${t.attacker+1}: <code>${escapeHtml(supA)}</code> ⊢ <strong>${escapeHtml(A?.conclusion||'?')}</strong></td>
      <td>→</td>
      <td>a${t.target+1}: <code>${escapeHtml(supB)}</code> ⊢ <strong>${escapeHtml(B?.conclusion||'?')}</strong></td>
      <td>cible <code>${escapeHtml(t.witness||'')}</code></td>
    </tr>`;
  }).join('');
  elAtks.innerHTML = `
    <table class="table">
      <thead><tr><th>Type</th><th>Attaquant</th><th></th><th>Cible</th><th>Témoin</th></tr></thead>
      <tbody>${rows || `<tr><td colspan="5">—</td></tr>`}</tbody>
    </table>`;
}

// === Graphe Cytoscape 2D ===
let __cy = null;
const BTN = {
  zoomIn:  document.getElementById('btnZoomIn'),
  zoomOut: document.getElementById('btnZoomOut'),
  fit:     document.getElementById('btnFit'),
  rotL:    document.getElementById('btnRotateL'),
  rotR:    document.getElementById('btnRotateR'),
  relayout:document.getElementById('btnRelayout')
};

function rotateGraph(deg=15){
  if(!__cy) return;
  const rad = (deg*Math.PI)/180;
  const bb = __cy.elements().boundingBox();
  const cx = (bb.x1+bb.x2)/2, cy=(bb.y1+bb.y2)/2;
  const cos=Math.cos(rad), sin=Math.sin(rad);
  __cy.startBatch();
  __cy.nodes().positions(n=>{
    const p=n.position(), dx=p.x-cx, dy=p.y-cy;
    return { x:cx+dx*cos-dy*sin, y:cy+dx*sin+dy*cos };
  });
  __cy.endBatch();
  __cy.layout({ name:'preset', fit:false }).run();
}

function renderGraph2D(j){
  const container = document.getElementById('graph2d');
  if(!container) return;

  const nodes = (j.arguments||[]).map(a=>({
    data:{
      id:'n'+a.id,
      short:`a${a.id+1}`,
      full:`a${a.id+1}: {${(a.assumptions||[]).join(', ')}} ⊢ ${a.conclusion}`
    }
  }));
  const edges = (j.attacks||[]).map((t,i)=>({
    data:{
      id:'e'+i, source:'n'+t.attacker, target:'n'+t.target,
      kind:t.kind||'normal'
    }
  }));

  __cy = cytoscape({
    container,
    elements:{nodes,edges},
    wheelSensitivity:0.2,
    style:[
      { selector:'node', style:{
          'background-color':'#6fb5ff','label':'data(short)',
          'color':'#eaf3ff','font-size':13,'font-weight':'600',
          'text-valign':'center','text-halign':'center',
          'text-outline-width':2,'text-outline-color':'#1f2a44',
          'width':26,'height':26,'border-width':2,'border-color':'#1f2a44'
      }},
      { selector:'edge[kind="normal"]', style:{
          'curve-style':'bezier','line-color':'#2874A6','width':2.2,
          'target-arrow-shape':'triangle','target-arrow-color':'#2874A6',
          'arrow-scale':1.1,'label':'data(label)','font-size':11,'color':'#cfe3ff',
          'text-background-color':'#0e1524','text-background-opacity':1,
          'text-background-padding':2,'text-rotation':'autorotate'
      }},
      { selector:'edge[kind="reverse"]', style:{
          'curve-style':'bezier','line-color':'#E74C3C','line-style':'dashed','width':2.2,
          'target-arrow-shape':'triangle','target-arrow-color':'#E74C3C',
          'arrow-scale':1.1,'label':'data(label)','font-size':11,'color':'#ffd8d3',
          'text-background-color':'#0e1524','text-background-opacity':1,
          'text-background-padding':2,'text-rotation':'autorotate'
      }},
      { selector:'.faded', style:{'opacity':0.15} }
    ],
    layout:{ name:'cose', animate:true, fit:true, padding:30,
      nodeRepulsion:6000, idealEdgeLength:140, edgeElasticity:80, gravity:0.25 }
  });

  // Tooltips
  __cy.nodes().forEach(n=>{
    const ref=n.popperRef();
    const tip=tippy(document.createElement('div'),{
      getReferenceClientRect:ref.getBoundingClientRect,
      content:n.data('full'), theme:'light', arrow:true,
      placement:'top', trigger:'manual', hideOnClick:false, interactive:false
    });
    n.data('tippy',tip);
  });


  // Hover highlight
  __cy.on('mouseover','node',evt=>{
    const n=evt.target; n.data('tippy')?.show();
    const neigh=n.closedNeighborhood();
    __cy.elements().addClass('faded'); neigh.removeClass('faded');
  });
  __cy.on('mouseout','node',evt=>{
    evt.target.data('tippy')?.hide();
    __cy.elements().removeClass('faded');
  });

  __cy.layout({
    name:'cose', animate:true, fit:true, padding:30,
    nodeRepulsion:6000, idealEdgeLength:140, edgeElasticity:80, gravity:0.25
  }).run();

  attachGraphControls();
}

function attachGraphControls(){
  if(!__cy) return;
  BTN.zoomIn.onclick  = ()=>__cy.animate({zoom:__cy.zoom()*1.2},{duration:200});
  BTN.zoomOut.onclick = ()=>__cy.animate({zoom:__cy.zoom()/1.2},{duration:200});
  BTN.fit.onclick     = ()=>__cy.fit(__cy.elements(),40);
  BTN.rotL.onclick    = ()=>rotateGraph(-15);
  BTN.rotR.onclick    = ()=>rotateGraph(15);
  BTN.relayout.onclick= ()=>__cy.layout({
    name:'cose', animate:true, fit:true, padding:30,
    nodeRepulsion:6000, idealEdgeLength:140, edgeElasticity:80, gravity:0.25
  }).run();
}

// === Rendu global ===
function renderAll(j){
  renderSummary(j);
  renderArguments(j);
  renderAttacks(j);
  renderGraph2D(j);
}
