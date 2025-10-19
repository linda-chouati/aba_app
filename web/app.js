// =============================
// Styles inline (injection JS) => psk prob avec l import du fichier css
// =============================
(function injectStyles(){
  const css = `
  /* ====== Tables jolies ====== */
  .table-lite{
    width:100%;
    border-collapse:separate;border-spacing:0;
    font-size:14px;
    border:1px solid #e6eaf2;border-radius:12px;overflow:hidden;background:#fff;
  }
  .table-lite thead th{
    position:sticky;top:0;z-index:1;
    background:#f3f7ff;color:#243b6b;text-align:left;
    font-weight:700;padding:12px;border-bottom:1px solid #e6eaf2;
  }
  .table-lite tbody td{
    padding:11px 12px;border-bottom:1px solid #eef2f7;vertical-align:middle;
  }
  .table-lite tbody tr:nth-child(odd){background:#fafcff;}
  .table-lite tbody tr:hover{background:#f2f7ff;}
  .table-lite th:first-child,.table-lite td:first-child{padding-left:14px;}
  .table-lite th:last-child,.table-lite td:last-child{padding-right:14px;}
  /* colonnes formules lisibles */
  #arguments table td:nth-child(1){font-weight:600;}
  #arguments table td:nth-child(2),
  #arguments table td:nth-child(4),
  #attacks table td:nth-child(2),
  #attacks table td:nth-child(4){font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;}
  /* ====== Badges ====== */
  .badge{display:inline-block;padding:.22rem .6rem;border-radius:999px;font-size:.78rem;font-weight:800;letter-spacing:.2px}
  .badge-normal{background:#e9f7ef;color:#12824c;border:1px solid #cbead8}
  .badge-reverse{background:#ffeff0;color:#c0352a;border:1px solid #f6c8cc}
  /* ====== Graph toolbar ====== */
  .graph-toolbar{display:flex;align-items:center;gap:8px;margin-top:10px}
  .graph-toolbar .sep{width:1px;height:20px;background:#e6eaf2}
  .graph-toolbar button{
    padding:6px 10px;border:1px solid #d9e2ef;background:#fff;color:#1f2a44;
    border-radius:8px;cursor:pointer;box-shadow:0 2px 10px rgba(15,23,42,.05);transition:all .18s ease
  }
  .graph-toolbar button:hover{background:#f0f5ff;color:#2b77e7}
  `;
  const s = document.createElement('style');
  s.id = 'inline-aba-style';
  s.textContent = css;
  document.head.appendChild(s);
})();

// =============================
// Configuration
// =============================
const ENDPOINT = '/api/aba/run';

const elInput    = document.getElementById('inputJson');
const elFile     = document.getElementById('fileInput');
const elBtnEx    = document.getElementById('btnLoadExample');
const elBtnCalc  = document.getElementById('btnCalc');
const elStatus   = document.getElementById('status');

const elArgs     = document.getElementById('arguments');
const elAtks     = document.getElementById('attacks');

// tableau dédié si présent dans le HTML
const tblWrap  = document.getElementById('attacksTable');
const tblBody  = document.getElementById('attacksTbody');

const optNonCirc = document.getElementById('optNonCirc');
const optAtomic  = document.getElementById('optAtomic');
const optPrefs   = document.getElementById('optPrefs');

// Toolbar graphe
const BTN = {
  zoomIn:  document.getElementById('btnZoomIn'),
  zoomOut: document.getElementById('btnZoomOut'),
  fit:     document.getElementById('btnFit'),
  rotL:    document.getElementById('btnRotateL'),
  rotR:    document.getElementById('btnRotateR'),
  relayout:document.getElementById('btnRelayout'),
};

// =============================
// Exemple par défaut
// =============================
const SAMPLE_TEXT = `L: [a,b,c,q,p,r,s,t]
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

// =============================
// Entrées
// =============================
elFile.addEventListener('change', async (ev) => {
  const file = ev.target.files?.[0];
  if (file) elInput.value = await file.text();
});

elBtnEx.addEventListener('click', () => {
  elInput.value = SAMPLE_TEXT;
});

function tryParseJSON(text) { try { return JSON.parse(text); } catch { return null; } }
function normalizeInput() {
  const raw = elInput.value.trim();
  const asJSON = tryParseJSON(raw);
  return { rawText: raw, jsonMaybe: asJSON };
}

// =============================
// Appel backend
// =============================
async function runAba() {
  const { rawText, jsonMaybe } = normalizeInput();

  const use_prefs    = !!optPrefs.checked;
  const non_circular = !!optNonCirc.checked;
  const atomic       = !!optAtomic.checked;

  const payload = {
    input: jsonMaybe ? JSON.stringify(jsonMaybe) : rawText,
    __options: {
      do_non_circular: non_circular,
      do_atomic: atomic,
      use_preferences: use_prefs,
    },
  };

  setStatus('Calcul en cours…');

  try {
    const resp = await fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      const txt = await resp.text().catch(()=> '');
      setStatus(`Erreur ${resp.status}: ${txt || resp.statusText}`);
      return;
    }

    const out = await resp.json();
    setStatus('Terminé');

    const view = buildViewModel(out);
    renderAll(view);
  } catch (e) {
    setStatus(`Erreur réseau : ${e?.message ?? e}`);
  }
}

// =============================
// Adaptation backend -> vue
// =============================
/**
 * Backend:
 * - arguments:    [{id:int, conclusion:str, assumptions:[...]}]
 * - attacks:      [{attacker:int, target:int, kind:'normal'|'reverse'|'both'}]
 * - attacks_sets: [{X:[...], Y:[...], kind:'normal'|'reverse'|'both'}]
 */
function buildViewModel(j) {
  const args = Array.isArray(j?.arguments) ? j.arguments : [];
  const atks = Array.isArray(j?.attacks) ? j.attacks : [];
  const atksSets = Array.isArray(j?.attacks_sets) ? j.attacks_sets : [];
  const opts = j?._options ?? {};

  // id -> argument
  const id2arg = new Map(args.map(a => [a.id, a]));

  // Graphe (attaques entre arguments)
  const nodes = args.map(a => ({ data: { id: String(a.id), label: String(a.conclusion) } }));
  const edges = atks.map(e => ({ data: { source: String(e.attacker), target: String(e.target) } }));

  // Liste arguments
  const argList = args.map(a => ({
    id: a.id,
    conclusion: a.conclusion,
    assumptions: Array.isArray(a.assumptions) ? a.assumptions : [],
  }));

  // Liste attaques simples (both -> affiché en normal pour ce tableau)
  const atkList = atks.map(e => ({
    attacker: e.attacker,
    target: e.target,
    kind: String(e.kind || 'normal').toLowerCase(), // normal | reverse | both
  }));

  // Préférences: transformer attacks_sets en lignes affichables (DUPE 'both')
  function setKey(xs) { return JSON.stringify([...new Set(xs)].sort()); }
  const supIndex = new Map();
  for (const a of args) {
    const key = setKey(a.assumptions || []);
    if (!supIndex.has(key)) supIndex.set(key, a);
  }
  function labelForSet(xs) {
    const key = setKey(xs || []);
    const arg = supIndex.get(key);
    const setTxt = xs && xs.length ? `{${xs.join(', ')}}` : '∅';
    if (arg) return `a${arg.id + 1}: ${setTxt} ⊢ ${arg.conclusion}`;
    return setTxt;
  }

  const prefRows = [];
  for (const t of atksSets) {
    const kind = String(t.kind || 'normal').toLowerCase();
    const row = { kind, labelX: labelForSet(t.X || []), labelY: labelForSet(t.Y || []) };
    if (kind === 'both') {
      prefRows.push({ ...row, kind: 'normal' });
      prefRows.push({ ...row, kind: 'reverse' });
    } else {
      prefRows.push(row);
    }
  }

  return {
    argList,
    atkList,
    prefRows,                 // lignes “préférences” SANS le 'both'
    graph: { nodes, edges },
    id2arg,
    opts,
  };
}

// =============================
// Rendu
// =============================
function setStatus(msg) { elStatus.textContent = msg; }

// Arguments (table)
function renderArguments(view) {
  const list = view?.argList || [];
  const rows = list.map(a => {
    const name = `a${a.id + 1}`;
    const supp = a.assumptions?.length ? `{${a.assumptions.join(', ')}}` : '∅';
    const concl = a.conclusion || '?';
    return `<tr><td>${name}</td><td>${supp}</td><td>⊢</td><td><strong>${concl}</strong></td></tr>`;
  }).join('');

  elArgs.innerHTML =
    `<table class="table-lite">
       <thead><tr><th>ID</th><th>Support</th><th></th><th>Conclusion</th></tr></thead>
       <tbody>${rows}</tbody>
     </table>`;
}

// Attaques entre arguments (table)
function renderAttacksSimple(view) {
  elAtks.innerHTML = '';
  const id2arg = view.id2arg;
  const items = (view?.atkList || []).map(e => {
    const A = id2arg.get(e.attacker);
    const B = id2arg.get(e.target);
    const nameA = A ? `a${A.id + 1}` : `[${e.attacker}]`;
    const nameB = B ? `a${B.id + 1}` : `[${e.target}]`;
    const suppA = A ? (A.assumptions.length ? `{${A.assumptions.join(', ')}}` : '∅') : '';
    const suppB = B ? (B.assumptions.length ? `{${B.assumptions.join(', ')}}` : '∅') : '';
    const conclA = A ? A.conclusion : '?';
    const conclB = B ? B.conclusion : '?';
    const kind = e.kind === 'both' ? 'normal' : e.kind; // pas de both en affichage
    const badge = `<span class="badge badge-${kind}">${kind}</span>`;
    return `<tr>
      <td>${badge}</td>
      <td>${nameA}: ${suppA} ⊢ ${conclA}</td>
      <td>→</td>
      <td>${nameB}: ${suppB} ⊢ ${conclB}</td>
    </tr>`;
  }).join('');

  elAtks.innerHTML =
    `<table class="table-lite">
       <thead><tr><th>Type</th><th>Attaquant</th><th></th><th>Cible</th></tr></thead>
       <tbody>${items}</tbody>
     </table>`;
}

// Attaques en mode Préférences (table, without 'both' : déjà dupliqué)
function renderAttacksPrefs(view) {
  if (!(tblWrap && tblBody)) {
    // fallback : table inline si pas de bloc dédié
    const rows = (view?.prefRows || []).map(t => {
      const badge = `<span class="badge badge-${t.kind}">${t.kind}</span>`;
      return `<tr><td>${badge}</td><td>${t.labelX}</td><td>→</td><td>${t.labelY}</td></tr>`;
    }).join('');
    elAtks.innerHTML =
      `<table class="table-lite">
         <thead><tr><th>Type</th><th>Attaquant</th><th></th><th>Cible</th></tr></thead>
         <tbody>${rows}</tbody>
       </table>`;
    return;
  }
  // version avec conteneur dédié
  tblWrap.style.display = '';
  tblBody.innerHTML = '';
  for (const t of (view?.prefRows || [])) {
    const tr = document.createElement('tr');
    tr.innerHTML =
      `<td><span class="badge badge-${t.kind}">${t.kind}</span></td>
       <td>${t.labelX}</td>
       <td>→</td>
       <td>${t.labelY}</td>`;
    tblBody.appendChild(tr);
  }
}

function renderAttacks(view) {
  if (view?.opts?.use_preferences && (view.prefRows?.length || 0) > 0) {
    if (tblWrap) elAtks.innerHTML = ''; // on bascule vers le bloc dédié s'il existe
    renderAttacksPrefs(view);
  } else {
    if (tblWrap) tblWrap.style.display = 'none';
    renderAttacksSimple(view);
  }
}

// =============================
// Graphe Cytoscape (toolbar OK)
// =============================
let __cy = null;

function renderGraph2D(view) {
  const el = document.getElementById('graph2d');
  el.innerHTML = ''; // reset

  const nodes = view?.graph?.nodes || [];
  const edges = view?.graph?.edges || [];

  __cy = cytoscape({
    container: el,
    elements: { nodes, edges },
    style: [
      {
        selector: 'node',
        style: {
          'label': 'data(label)',
          'text-valign': 'center',
          'text-halign': 'center',
          'width': 'label',
          'height': 'label',
          'padding': '8px',
          'shape': 'round-rectangle',
          'border-width': 1,
          'background-color': '#9aa0a6',
          'color': '#111',
          'border-color': '#444'
        }
      },
      {
        selector: 'edge',
        style: {
          'curve-style': 'bezier',
          'target-arrow-shape': 'triangle',
          'arrow-scale': 1.2,
          'width': 1,
          'line-color': '#b0b4b9',
          'target-arrow-color': '#b0b4b9'
        }
      }
    ],
    layout: { name: 'cose', animate: true, fit: true, padding: 30 }
  });

  // Toolbar handlers
  BTN.zoomIn.onclick  = () => __cy && __cy.zoom(__cy.zoom() * 1.2);
  BTN.zoomOut.onclick = () => __cy && __cy.zoom(__cy.zoom() / 1.2);
  BTN.fit.onclick     = () => __cy && __cy.fit();

  BTN.rotL.onclick    = () => rotateGraph(-15);
  BTN.rotR.onclick    = () => rotateGraph(15);
  BTN.relayout.onclick= () => {
    if (!__cy) return;
    __cy.layout({ name: 'cose', animate: true, fit: true, padding: 30 }).run();
  };

  // Rotation autour du centre des nœuds
  function rotateGraph(deg) {
    if (!__cy) return;
    const rad = (deg * Math.PI) / 180;

    // centre (moyenne des positions)
    let sumX = 0, sumY = 0, n = 0;
    __cy.nodes().forEach(node => { const p = node.position(); sumX += p.x; sumY += p.y; n++; });
    if (n === 0) return;
    const cx = sumX / n, cy = sumY / n;

    const newPos = {};
    __cy.nodes().forEach(node => {
      const p = node.position();
      const dx = p.x - cx, dy = p.y - cy;
      const x =  dx * Math.cos(rad) - dy * Math.sin(rad) + cx;
      const y =  dx * Math.sin(rad) + dy * Math.cos(rad) + cy;
      newPos[node.id()] = { x, y };
    });

    __cy.nodes().positions(n => newPos[n.id()]);
  }
}

function renderAll(view) {
  renderArguments(view);
  renderAttacks(view);
  renderGraph2D(view);
}

// =============================
// Bouton "Calculer"
// =============================
elBtnCalc.addEventListener('click', () => {
  runAba().catch(e => setStatus(`❌ ${e?.message ?? e}`));
});
