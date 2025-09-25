// ---- CONFIG ----
const API_BASE = "https://aba-app-bj37.onrender.com"; // <- remplace si besoin

let lastPayload = null;
let lastResult = null;


document.addEventListener("DOMContentLoaded", () => {
  // En-tête
  document.getElementById("api").textContent = API_BASE;
  document.getElementById("docs").href = API_BASE + "/docs";
  pingHealth();

  // Boutons
  document.getElementById("add-contrary").addEventListener("click", addContraryRow);
  document.getElementById("add-rule").addEventListener("click", addRuleRow);
  document.getElementById("btn-run").addEventListener("click", runABA);
  document.getElementById("btn-sample").addEventListener("click", loadSampleAll);
  document.getElementById("btn-clear").addEventListener("click", clearAll);

  // Option d afficahge pour le json
  document.getElementById("btn-toggle-preview").addEventListener("click", togglePreview);   
  document.getElementById("btn-toggle-result").addEventListener("click", toggleResult);


  // Démarrage : une ligne vide
  if (document.querySelectorAll("#contraries-body tr").length === 0) addContraryRow();
  if (document.querySelectorAll("#rules-body tr").length === 0) addRuleRow();
});

// ---- Utilitaires ----
function splitCSV(s) {
  return (s || "")
    .split(",")
    .map(t => t.trim())
    .filter(Boolean);
}

async function pingHealth(){
  const el = document.getElementById("health");
  try {
    const r = await fetch(API_BASE + "/health", {cache:"no-store"});
    el.textContent = r.ok ? "OK" : "HS";
    el.className = r.ok ? "badge-ok" : "badge-err";
  } catch {
    el.textContent = "HS";
    el.className = "badge-err";
  }
}

// ---- Gestion des lignes dynamiques ----
function addContraryRow(a="", c="") {
  const tbody = document.getElementById("contraries-body");
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td><input type="text" class="inp-contrary-a" placeholder="a" value="${a}"></td>
    <td><input type="text" class="inp-contrary-c" placeholder="r" value="${c}"></td>
    <td class="actions"><button class="secondary btn-del">Suppr</button></td>
  `;
  tr.querySelector(".btn-del").addEventListener("click", () => tr.remove());
  tbody.appendChild(tr);
}

function addRuleRow(head="", body="") {
  const tbody = document.getElementById("rules-body");
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td><input type="text" class="inp-rule-head" placeholder="p" value="${head}"></td>
    <td><input type="text" class="inp-rule-body" placeholder="q,a  (laisser vide pour un fait)" value="${body}"></td>
    <td class="actions"><button class="secondary btn-del">Suppr</button></td>
  `;
  tr.querySelector(".btn-del").addEventListener("click", () => tr.remove());
  tbody.appendChild(tr);
}

// ---- Lecture du formulaire -> JSON ----
function collectPayload() {
  const literals = splitCSV(document.getElementById("literals").value);
  const assumptions = splitCSV(document.getElementById("assumptions").value);

  // Contraires
  const contraries = {};
  document.querySelectorAll("#contraries-body tr").forEach(tr => {
    const a = tr.querySelector(".inp-contrary-a").value.trim();
    const c = tr.querySelector(".inp-contrary-c").value.trim();
    if (a && c) contraries[a] = c;
  });

  // Règles
  const rules = [];
  document.querySelectorAll("#rules-body tr").forEach(tr => {
    const head = tr.querySelector(".inp-rule-head").value.trim();
    const body = tr.querySelector(".inp-rule-body").value.trim();
    if (!head) return;
    const bodyArr = splitCSV(body);
    rules.push({ head, body: bodyArr });
  });

  // Préférences
  const prefText = document.getElementById("pref").value.trim();
  const preferences = prefText ? prefText : {};

  const payload = { literals, assumptions, contraries, rules, preferences };
  return payload;
}

function updatePreview(payload){
  document.getElementById("preview").textContent = JSON.stringify(payload, null, 2);
}

// ---- Actions principales ----
async function runABA(){
  const out = document.getElementById("out");
  const status = document.getElementById("status-msg");
  out.textContent = "Calcul en cours…";
  status.textContent = "Envoi au backend…";

  const payload = collectPayload();
  updatePreview(payload);

  // Ping pour réveiller Render
  try { await fetch(API_BASE + "/health", {cache:"no-store"}); } catch {}

  try {
    const res = await fetch(API_BASE + "/run", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    });
    const text = await res.text();
    let data;
    try { data = JSON.parse(text); } catch { data = { raw: text }; }

    if (!res.ok) {
      out.textContent = "Erreur HTTP " + res.status + ": " + (data.detail || text);
      status.textContent = "Erreur.";
      return;
    }
    out.textContent = JSON.stringify(data, null, 2);
    renderSummary(data);
    status.textContent = "OK.";
  } catch (e) {
    out.textContent = "Erreur réseau/CORS : " + e.message;
    status.textContent = "Erreur réseau.";
  }
}

function clearAll(){
  document.getElementById("literals").value = "";
  document.getElementById("assumptions").value = "";
  document.getElementById("pref").value = "";
  document.getElementById("contraries-body").innerHTML = "";
  document.getElementById("rules-body").innerHTML = "";
  addContraryRow();
  addRuleRow();
  document.getElementById("preview").textContent = "—";
  document.getElementById("out").textContent = "Résultats ici…";
  document.getElementById("summary").innerHTML = '<span class="small">Lance un run pour voir les arguments et attaques.</span>';
  document.getElementById("status-msg").textContent = "";
}

// ---- Exemple complet ----
function loadSampleAll(){
  document.getElementById("literals").value = "a,b,c,q,p,r,s,t";
  document.getElementById("assumptions").value = "a,b,c";
  document.getElementById("pref").value = "a > b";

  const contr = [
    ["a","r"],
    ["b","s"],
    ["c","t"],
  ];
  const rules = [
    ["p","q,a"],
    ["q",""],
    ["r","b,c"],
    ["t","p,c"],
    ["s","t"]
  ];

  document.getElementById("contraries-body").innerHTML = "";
  contr.forEach(([a,c]) => addContraryRow(a,c));

  document.getElementById("rules-body").innerHTML = "";
  rules.forEach(([h,b]) => addRuleRow(h,b));

  const p = collectPayload();
  updatePreview(p);
}

// ---- Résumé lisible ----
function renderSummary(data){
  const root = document.getElementById("summary");
  const args = data.arguments || [];
  const atks = data.attacks || [];

  const argRows = args.map(a => `
    <tr>
      <td class="small">A${a.id}</td>
      <td><code>${a.conclusion}</code></td>
      <td>${(a.assumptions||[]).map(x=>`<code>${x}</code>`).join(", ") || "<span class='small'>∅</span>"}</td>
    </tr>
  `).join("");

  const atkRows = atks.map(x => `
    <tr>
      <td>${x.kind === "reverse" ? "↺ reverse" : "→ normal"}</td>
      <td class="small">A${x.attacker}</td>
      <td class="small">A${x.target}</td>
      <td>vise <code>${x.witness}</code></td>
    </tr>
  `).join("");

  root.innerHTML = `
    <div>
      <div class="row" style="gap:10px;margin:6px 0 12px;">
        <span>Arguments: <b>${args.length}</b></span>
        <span>Attaques: <b>${atks.length}</b></span>
      </div>
      <h4>Arguments</h4>
      <table class="grid-table">
        <thead><tr><th>ID</th><th>Conclusion</th><th>Hypothèses</th></tr></thead>
        <tbody>${argRows || "<tr><td colspan='3' class='small'>Aucun</td></tr>"}</tbody>
      </table>

      <h4 style="margin-top:16px;">Attaques</h4>
      <table class="grid-table">
        <thead><tr><th>Type</th><th>Attaquant</th><th>Cible</th><th>Détail</th></tr></thead>
        <tbody>${atkRows || "<tr><td colspan='4' class='small'>Aucune</td></tr>"}</tbody>
      </table>
    </div>
  `;
}


// pour afficher les json 
function togglePreview(){
  const sec = document.getElementById("preview-section");
  const btn = document.getElementById("btn-toggle-preview");
  const card = btn.closest(".card");
  
  if (sec.classList.contains("hidden")) {
    if (!lastPayload) {
      lastPayload = collectPayload();
    }
    document.getElementById("preview").textContent = JSON.stringify(lastPayload, null, 2);
    sec.classList.remove("hidden");
    btn.textContent = "Masquer";
    card.classList.add("toggle-open");
  } else {
    sec.classList.add("hidden");
    btn.textContent = "Afficher";
    card.classList.remove("toggle-open");
  }
}

function toggleResult(){
  const sec = document.getElementById("result-section");
  const btn = document.getElementById("btn-toggle-result");
  const card = btn.closest(".card");
  
  if (sec.classList.contains("hidden")) {
    if (lastResult) {
      const out = document.getElementById("out");
      out.textContent = JSON.stringify(lastResult, null, 2);
    }
    sec.classList.remove("hidden");
    btn.textContent = "Masquer";
    card.classList.add("toggle-open");
  } else {
    sec.classList.add("hidden");
    btn.textContent = "Afficher";
    card.classList.remove("toggle-open");
  }
}
