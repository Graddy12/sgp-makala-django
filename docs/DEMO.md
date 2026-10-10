# Préparer la démonstration SGP Makala

Le jeu livré contient **120 identités adultes entièrement fictives**, 20 cellules
(144 places théoriques, dont 8 en maintenance : 136 utilisables), 47 jugements simulés, 216 visites, 12 transferts, 179 pièces PDF
et 126 entrées de journal pédagogique. Les portraits sont générés et représentent
des personnages inventés. Ils sont répartis entre les dossiers de démonstration.

Sur Render Free, SQLite et les fichiers ajoutés à l'exécution restent temporaires.
Les données de départ sont donc conservées dans Git sous `demo/seed.json`, les
portraits sous `static/demo/portraits/`, et les pièces PDF sont recréées au besoin.
Le démarrage de l'application peut reconstituer un registre complet après une
perte du disque. Cette restauration concerne le jeu de départ : les saisies
effectuées pendant une démonstration ne deviennent pas permanentes.

## Chargement manuel

Après avoir configuré le compte administrateur avec les variables `SGP_ADMIN_*` :

```sh
python manage.py migrate --noinput
python manage.py bootstrap_admin
python manage.py seed_demo
```

`seed_demo --dry-run` valide le fichier JSON et affiche les volumes sans écrire
dans la base. Un deuxième chargement ne crée aucun doublon et ne réinitialise
ni le mot de passe administrateur, ni les dossiers déjà modifiés, ni les statuts
des visites ou transferts. Il restaure uniquement les portraits et PDF de départ
manquants. Les huit agents fictifs affichés dans l'administration ont un mot de
passe inutilisable ; utilisez le compte administrateur configuré dans Render.

Les dates d'écrou, jugement, visite et transfert sont exprimées dans le JSON en
nombre de jours par rapport au premier chargement du dossier. Les nouveaux jeux
affichent ainsi des visites et transferts récents. Les dates des dossiers présents
en base sont conservées lors des chargements suivants.

## Enrôlement le jour J

Le fichier prêt à importer est `demo/enrollment_day_j.json`. Il contient une
identité fictive adulte et une affectation disposant de places dans le jeu initial.
L'import dans le registre permet de prévisualiser les informations avant la
création. La date d'écrou et le matricule sont attribués au moment de la création.
Vérifiez la disponibilité de la cellule si vous avez effectué d'autres essais.

Parcours conseillé : tableau de bord, recherche d'un dossier, consultation de sa
photo et de ses pièces, ajout depuis le JSON, visite, jugement, puis export PDF.
Une nouvelle saisie subsiste tant que le disque de l'instance demeure disponible.
Gardez ce JSON dans le projet pour pouvoir refaire l'enrôlement après redémarrage.

## Modifier les exemples

`python demo/build_seed.py` reconstruit le JSON de départ de façon déterministe,
sans toucher à la base. Chaque collection réserve les identifiants 900001 à
909999, comme une fixture Django. Ces identifiants stables évitent les doublons
même après modification d'un matricule, d'une référence ou d'un nom de pièce.
Ne réutilisez pas cette plage pour un autre jeu importé. Les fichiers PDF portent clairement
la mention « DOCUMENT FICTIF — SANS VALEUR JURIDIQUE ».
