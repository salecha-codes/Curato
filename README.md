# Curato AI — E-commerce Customer Recommendation System

This is the final Python project. The website and API run through Flask, and the recommendations are calculated by the Python model files in `backend/models/`.

## Machine-learning techniques

- `backend/models/popularity.py` — Bayesian weighted popularity ranking.
- `backend/models/collaborative.py` — user-based collaborative filtering with cosine similarity.
- `backend/models/svd.py` — model-based collaborative filtering using truncated SVD.
- `backend/models/engine.py` — trains the three models, excludes products already rated by the customer, and returns ranked recommendations.

## Run the project

Install Python 3.10 or newer. Open a terminal in this folder:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

macOS or Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:8000`.

## What to show during the presentation

1. Open `backend/models/popularity.py` and explain the weighted-rating formula.
2. Open `backend/models/collaborative.py` and explain cosine similarity and the top 20 similar customers.
3. Open `backend/models/svd.py` and explain the centered customer–product matrix and latent factors.
4. Open `backend/models/engine.py` and show how all three approaches are selected and ranked.
5. Open `backend/app.py` and show how the website calls the Python models through API routes.

The bundled data is synthetic teaching data: 120 customers, 60 products and 2,640 ratings. Runtime feedback and imported datasets are stored inside `runtime/`, which Git ignores.

## Git collaboration

Create a branch before editing:

```bash
git pull origin main
git checkout -b feature/short-description
```

Commit and push:

```bash
git add .
git commit -m "Describe the change"
git push -u origin feature/short-description
```

Then create a pull request on GitHub. Do not commit directly to `main`.
