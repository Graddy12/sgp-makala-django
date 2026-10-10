# SGP Makala (Django)

Système Numérique de Gestion Pénitentiaire — Prison Centrale de Makala (RDC).  
Recréation Django du projet PHP original, avec **SQLite**.

## Stack

- Django 5 + SQLite
- Bootstrap 5 / Chart.js / ReportLab (PDF)
- Auth RBAC (5 rôles)
- WhiteNoise (static) — prêt Render

## Démarrage local

```bash
cd SGP_DJANGO
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py bootstrap_admin
python manage.py seed_demo
python manage.py runserver
```

Ouvrir http://127.0.0.1:8000/

**Compte admin par défaut** (modifiable dans `.env`) :

- Email : `admin@makala.cd`
- Mot de passe : `Admin@Makala2026`

## Modules

Dashboard, Détenus, Cellules, Jugements, Transferts, Visites, Documents, Rapports PDF, Audit, Users, Backup SQLite.

## Déploiement (GitHub → Render)

1. Pousser les changements sur GitHub.
2. Dans Render, choisir **New → Blueprint**, puis sélectionner ce dépôt. Render lira `render.yaml` et créera le service Web gratuit.
3. Le Blueprint génère `SECRET_KEY` et `SGP_ADMIN_PASSWORD`. Après le premier déploiement, consulter la valeur de `SGP_ADMIN_PASSWORD` dans les variables du service pour se connecter avec `SGP_ADMIN_EMAIL`.

Le service suit `Graddy12/SGP_MAKALA`, branche `main`, avec `autoDeployTrigger: commit`. `scripts/start.sh` exécute les migrations, crée l’administrateur si nécessaire et charge les données fictives si `DEMO_MODE=True`, avant de lancer Gunicorn. Le chargement conserve les modifications existantes et recrée le jeu de démonstration si SQLite a disparu. Les anciens services utilisant encore la précédente commande de démarrage disposent du même chargement dans WSGI sur Render.

Le fichier YAML décrit la configuration souhaitée. Vérifier aussi dans **Render → sgp-makala → Settings** que le dépôt connecté est `Graddy12/SGP_MAKALA`, la branche `main`, et **Auto-Deploy = On Commit**. Une modification du YAML seule ne prouve pas la synchronisation d’un service créé manuellement. `/health/` indique la révision réellement servie.

Le [guide de démo](docs/DEMO.md) présente les données, le parcours de présentation et le JSON d’enrôlement du jour J. Activer `DEMO_MODE=True` dans `.env` pour afficher l’import JSON localement. Dans le registre, **Importer JSON** permet de prévisualiser l’exemple, puis de confirmer l’écrou avec sa photo. Les 16 portraits sont des adultes fictifs générés par IA; leur [prompt et provenance](static/demo/portraits/PROMPT.md) sont inclus. Ne pas appliquer le seed à une base de production.

**Important :** le service gratuit Render utilise un disque éphémère. La base SQLite et les documents téléversés peuvent être perdus lors d'un redémarrage ou d'un nouveau déploiement. Cette configuration est réservée aux essais avec des données fictives, pas aux données pénitentiaires réelles. Une mise en production nécessite une base PostgreSQL et un stockage persistant des documents.

## Structure

```
SGP_DJANGO/
  accounts/   # User custom + auth
  prison/     # Détenus, cellules, jugements, transferts, visites, documents
  core/       # Dashboard, audit, PDF, backup, media
  templates/  static/  media/
  config/     # settings, urls, wsgi
```
