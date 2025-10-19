# ABA+ Framework — Générateur d’arguments (FastAPI)

Une petite application **ABA / ABA+** qui :

- lit une définition d’ABA en **texte** ou **JSON** ;
- **génère** tous les arguments (support ⊢ conclusion) ;
- **calcule** les attaques entre arguments ;
- gère en option : **préférences (ABA+)**, mode **non-circulaire**, mode **atomique** ;
- expose une **API FastAPI** et un **front** très simple (HTML/JS/CSS).

---

## Fonctionnalités

- **Parsing** de définitions ABA en _texte_ ou en _JSON_ structuré.
- **Génération d’arguments** par application des règles ; stockage du support et de la conclusion.
- **Attaques** : détection et typage (_normal_ vs _reverse_ en ABA+).
- **Options** :
  - _Non-circulaire_ : enlève les arguments qui dépendent d’eux-mêmes ;
  - _Atomique_ : impose des conclusions atomiques dans les règles ;
  - _Préférences (ABA+)_ : active les attaques _reverse_ selon les préférences.
- **Front** : zone de saisie + tableaux **Arguments** / **Attaques** + **graphe** interactif (Cytoscape).

---

## Structure du dépôt

```
.
├── app.py               # Entrée FastAPI (API + statiques)
├── requirements.txt     # Dépendances Python
├── data/                # Exemples de définitions (pour tests)
├── src/                 # Cœur Python
│   ├── aba_core.py
│   ├── aba_attacks.py
│   ├── aba_transform.py
│   ├── utils.py         # parse_any, parse_preferences, etc.
│   └── ...
├── tests/               # Pytest (exemples du cours, régressions)
└── web/                 # Front minimal
    ├── index.html
    ├── app.js
    └── style.css
```

---

## Prérequis

- **Python 3.11+** (3.12 recommandé)
- **pip** et (optionnel) **virtualenv**

Dépendances Python minimales (déjà listées) :

```
fastapi==0.115.0
uvicorn==0.30.6
```

> Pour exécuter les tests : `pytest` (ajoutez `pytest` à `requirements.txt` si besoin).

---

## Installation (local)

```bash
# 1) Cloner le dépôt
git clone https://github.com/linda-chouati/aba_app.git
cd https://github.com/linda-chouati/aba_app.git

# 2) Créer et activer un environnement virtuel
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3) Installer les dépendances
pip install -r requirements.txt
```

> Si vous n’avez pas de `requirements.txt`, créez-le avec :
>
> ```
> fastapi==0.115.0
> uvicorn==0.30.6
> pytest==7.4.4
> ```

---

## Lancer l’appli en ligne

Tester l'application en ligne depuis : https://aba-app-bj37.onrender.com/

---

## Lancer l’appli en local

Depuis la racine du projet (là où se trouve `app.py`) :

```bash
uvicorn app:app --reload --port 8000
```

- API dispo sur: `http://127.0.0.1:8000`
- Front (statiques): `http://127.0.0.1:8000/` (sert `web/index.html`)

---

## Tests

```bash
pytest -q
```

Les tests valident la génération d’arguments et le comptage/type des attaques (quelques exemples du cours).
