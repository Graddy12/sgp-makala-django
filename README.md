# SGP Makala (Django)

Système Numérique de Gestion Pénitentiaire — Prison Centrale de Makala (RDC).  
Recréation Django du projet PHP original, avec **SQLite**.

## Stack

- Django 5 + SQLite
- Bootstrap 5 / Chart.js / ReportLab (PDF)
- Auth RBAC (5 rôles)
- WhiteNoise (static) — prêt Vercel

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
python manage.py runserver
```

Ouvrir http://127.0.0.1:8000/

**Compte admin par défaut** (modifiable dans `.env`) :

- Email : `admin@makala.cd`
- Mot de passe : `Admin@Makala2026`

## Modules

Dashboard, Détenus, Cellules, Jugements, Transferts, Visites, Documents, Rapports PDF, Audit, Users, Backup SQLite.

## Déploiement (GitHub → Vercel)

1. Pousser le dossier `SGP_DJANGO` (ou le repo racine) sur GitHub.
2. Importer le projet sur [Vercel](https://vercel.com) (framework Python).
3. Variables d'environnement : `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, `SGP_ADMIN_*`.
4. **Limites Vercel** : filesystem éphémère (uploads/SQLite non persistants). Pour la prod réelle, brancher Postgres (Neon) + stockage objet (S3/R2).

## Structure

```
SGP_DJANGO/
  accounts/   # User custom + auth
  prison/     # Détenus, cellules, jugements, transferts, visites, documents
  core/       # Dashboard, audit, PDF, backup, media
  templates/  static/  media/
  config/     # settings, urls, wsgi
```
