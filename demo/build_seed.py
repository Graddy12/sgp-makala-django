"""Rebuild the fictional, deterministic dataset committed as seed.json.

Run from any directory with ``python demo/build_seed.py``. This script writes JSON
only; it never connects to a database and contains no passwords or real records.
"""
import json
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def build():
    data = {
        'version': 1,
        'fictional': True,
        'description': 'Jeu de soutenance : identités, affaires, agents et documents entièrement fictifs.',
        'users': [], 'cells': [], 'detenus': [], 'jugements': [],
        'transferts': [], 'visites': [], 'documents': [], 'audit': [],
        'notifications': [],
    }
    staff = [
        ('DIR', 'MUSENGA', 'Albert', 'directeur'),
        ('GRE', 'KATENDE', 'Clarisse', 'greffier'),
        ('GRE2', 'MBALA', 'Thierry', 'greffier'),
        ('AG1', 'KAZADI', 'Samuel', 'agent_penitentiaire'),
        ('AG2', 'LOKOMBE', 'Rachel', 'agent_penitentiaire'),
        ('AG3', 'NKOKO', 'Henri', 'agent_penitentiaire'),
        ('VIS', 'BASILA', 'Esther', 'responsable_visites'),
        ('VIS2', 'MAVUNGU', 'Roger', 'responsable_visites'),
    ]
    for code, nom, prenom, role in staff:
        data['users'].append({
            'matricule': f'DEMO-USR-{code}', 'email': f'{code.lower()}@demo.invalid',
            'nom': nom, 'prenom': prenom, 'role': role, 'statut': 'actif',
        })

    for i in range(1, 21):
        if i <= 14:
            pavillon, bloc = ('Pavillon 1 - Hommes' if i <= 7 else 'Pavillon 2 - Hommes'), ('Bloc A' if i <= 7 else 'Bloc B')
            capacite = {1: 7, 3: 6, 4: 6}.get(i, 8)
        elif i <= 18:
            pavillon, bloc, capacite = 'Pavillon 9 - Femmes', 'Bloc F', (6 if i == 15 else 7)
        elif i == 19:
            pavillon, bloc, capacite = 'Pavillon 11 - Isolement', 'Bloc I', 2
        else:
            pavillon, bloc, capacite = 'Pavillon 3 - Réserve', 'Bloc C', 8
        data['cells'].append({
            'code_cellule': f'DEMO-P01-C{i:02d}', 'pavillon': pavillon,
            'bloc': bloc, 'capacite_max': capacite,
            'statut': ('isolement' if i == 19 else 'maintenance' if i == 20 else 'disponible'),
            'description': 'Cellule fictive de démonstration. ' + ('Travaux de peinture planifiés.' if i == 20 else 'Affectation pédagogique et suivi de capacité.'),
        })

    noms = ['KASONGO', 'MUKENDI', 'ILUNGA', 'MBUYI', 'KABONGO', 'TUMBA', 'KALALA', 'NSIMBA', 'MAVUNGU', 'LUKUSA', 'TSHIMANGA', 'BASILA', 'KATENDE', 'NKOSI', 'MUSENGA', 'KAZADI', 'LOKOMBE', 'MBALA', 'KISIMBA', 'NKOKO']
    postnoms = ['MUSALA', 'KALONJI', 'MUTOMBO', 'BADI', 'LUSAMBA', 'KIBALA', 'TONGO', 'SENGA', 'MALU', 'NDALA', 'KAMBA', 'LOKELE']
    male_names = ['David', 'Samuel', 'Alain', 'Michel', 'Serge', 'Jean', 'Thierry', 'Pascal', 'Henri', 'Roger', 'Albert', 'Eric', 'Daniel', 'Luc', 'Emmanuel', 'Paul']
    female_names = ['Clarisse', 'Esther', 'Rachel', 'Nadine', 'Caroline', 'Monique', 'Chantal', 'Lucie', 'Cécile', 'Alice', 'Madeleine', 'Judith']
    communes = ['Lemba', 'Matete', 'Ngaba', 'Kintambo', 'Ngaliema', 'Kalamu', 'Bandalungwa', 'Limete']
    motifs = ['Vol simple', 'Abus de confiance', 'Escroquerie', 'Dégradation de biens', 'Faux en écriture', 'Recel', 'Coups et blessures']
    men_index = women_index = 0
    for i in range(1, 121):
        is_female = i % 5 == 0
        status = ('prevenu' if i % 5 < 3 else 'condamne') if i <= 108 else ('transfere' if i <= 114 else 'libere' if i <= 118 else 'archive')
        active = i <= 108
        cell = None
        if active and i <= 2:
            cell = 19
        elif active and is_female:
            cell = 15 + women_index % 4
            women_index += 1
        elif active:
            cell = 1 + men_index % 14
            men_index += 1
        portrait_number = (i // 5 if is_female else i - i // 5) % 8 + 1
        person = {
            'matricule': f'DEMO-DET-{i:04d}',
            'nom': noms[(i - 1) % len(noms)],
            'postnom': postnoms[((i - 1) // len(noms) + i) % len(postnoms)],
            'prenom': (female_names[(i // 5 - 1) % len(female_names)] if is_female else male_names[(i - 1) % len(male_names)]),
            'date_naissance': (date(1974, 1, 1) + timedelta(days=(i * 179) % 11500)).isoformat(),
            'lieu_naissance': ['Kinshasa', 'Matadi', 'Kikwit', 'Kananga', 'Mbuji-Mayi', 'Kisangani'][i % 6],
            'genre': 'F' if is_female else 'M', 'nationalite': 'Congolaise (RDC)',
            'etat_civil': ['celibataire', 'marie', 'divorce', 'veuf'][i % 4],
            'adresse': f'Avenue fictive {i}, {communes[i % 8]}, Kinshasa',
            'photo': f'demo_portrait_{"f" if is_female else "m"}_{portrait_number:02d}.jpg',
            'statut_judiciaire': status,
            'niveau_dangerosite': ('critique' if i <= 2 else ['faible', 'faible', 'moyen', 'moyen', 'eleve'][i % 5]),
            'date_ecrou_offset': -(90 + i * 3),
            'motif_inculpation': f'{motifs[i % len(motifs)]} — scénario entièrement fictif pour la démonstration.',
            'cellule_code': f'DEMO-P01-C{cell:02d}' if cell else None,
        }
        if status == 'condamne':
            person['date_liberation_prevue_offset'] = 365 + i * 7
        if status in ('libere', 'archive'):
            person['date_liberation_effective_offset'] = -(i - 107)
        data['detenus'].append(person)

        if status in ('condamne', 'libere'):
            judgment = {
                'detenu': person['matricule'], 'numero_dossier': f'DEMO-RP-{i:04d}',
                'tribunal': ['TGI Kinshasa / Kalamu (simulation)', 'TGI Kinshasa / Gombe (simulation)', 'Tribunal de paix de Lemba (simulation)'][i % 3],
                'date_jugement_offset': -(30 + i),
                'type_decision': 'condamnation' if status == 'condamne' else 'acquittement',
                'peine_ans': 2 + i % 4 if status == 'condamne' else 0,
                'peine_mois': 3 if status == 'condamne' and i % 2 else 0,
                'peine_amende': str(100 + i * 5) if status == 'condamne' else '0',
                'resume_verdict': 'Décision simulée sans valeur juridique, utilisée uniquement pour la soutenance.',
                'juge_nom': f'Magistrat fictif {i % 5 + 1}',
            }
            # Match the model's sentence calculation to the displayed release date.
            if status == 'condamne':
                person['date_liberation_prevue_offset'] = judgment['date_jugement_offset'] + judgment['peine_ans'] * 365 + judgment['peine_mois'] * 30
            data['jugements'].append(judgment)

        data['documents'].append({
            'detenu': person['matricule'], 'titre': f'Mandat simulé — {person["matricule"]}',
            'type_doc': 'mandat_depot', 'fichier_path': f'demo_mandat_{i:04d}.pdf',
            'description': 'Pièce fictive, sans signature ni valeur juridique.',
        })
        if status in ('condamne', 'libere'):
            data['documents'].append({
                'detenu': person['matricule'], 'titre': f'Décision simulée — {person["matricule"]}',
                'type_doc': 'jugement', 'fichier_path': f'demo_jugement_{i:04d}.pdf',
                'description': 'Copie pédagogique fictive, sans valeur juridique.',
            })
        if i % 10 == 0:
            data['documents'].append({
                'detenu': person['matricule'], 'titre': f'Fiche de suivi simulée — {person["matricule"]}',
                'type_doc': 'fiche_medicale', 'fichier_path': f'demo_suivi_{i:04d}.pdf',
                'description': 'Suivi administratif fictif. Aucune donnée médicale réelle.',
            })

        if active:
            for v in range(2):
                visit_offset = -(i % 24 + 1) if v == 0 else (i % 12)
                visit_status = 'terminee' if v == 0 else ['demande', 'autorisee', 'autorisee', 'refusee', 'annulee'][i % 5]
                data['visites'].append({
                    'detenu': person['matricule'], 'numero_piece': f'DEMO-VIS-{i:04d}-{v + 1}',
                    'nom_visiteur': noms[(i + 7) % len(noms)],
                    'prenom_visiteur': female_names[i % len(female_names)] if i % 2 else male_names[(i + 2) % len(male_names)],
                    'lien_parente': ['Conjoint(e)', 'Frère / sœur', 'Parent', 'Avocat (simulation)'][i % 4],
                    'type_piece_identite': 'Pièce fictive de démonstration',
                    'date_visite_offset': visit_offset,
                    'heure_debut': f'{9 + i % 6:02d}:00:00',
                    'heure_fin': f'{9 + i % 6:02d}:30:00' if v == 0 else None,
                    'statut': visit_status, 'objet_visite': 'Entretien familial simulé',
                    'effets_apportes': 'Kit administratif fictif' if v == 0 else '',
                })

        data['audit'].append({
            'action': 'DEMO_CREATION_DETENU', 'module': 'DETENUS',
            'description': f'[DEMO-{i:04d}] Enregistrement fictif de {person["matricule"]}.',
            'created_at_offset': person['date_ecrou_offset'],
        })

    # Four planned, two cancelled, six completed movements; completed people are inactive.
    for n, i in enumerate([12, 24, 36, 48, 60, 72, 109, 110, 111, 112, 113, 114], 1):
        status = 'planifie' if n <= 4 else 'annule' if n <= 6 else 'effectue'
        data['transferts'].append({
            'detenu': f'DEMO-DET-{i:04d}',
            'etablissement_provenance': 'Prison Centrale de Makala (simulation)',
            'etablissement_destination': ['Centre de Luzumu (simulation)', 'Établissement de Matadi (simulation)', 'Centre de Kikwit (simulation)'][n % 3],
            'motif_transfert': 'Rapprochement familial ou réorganisation — scénario fictif.',
            'date_transfert_offset': (n + 1) if status == 'planifie' else -(n + 2),
            'statut': status, 'escorte_agents': 'Équipe de démonstration DEMO-AG1 / DEMO-AG2',
            'notes': f'DEMO-TRANSFERT-{n:04d} — mouvement entièrement fictif.',
        })

    for n, (action, module, message) in enumerate([
        ('DEMO_INITIALISATION', 'SYSTEME', 'Jeu de démonstration chargé : 120 identités adultes fictives.'),
        ('DEMO_PLANIFICATION', 'TRANSFERTS', 'Quatre transferts fictifs planifiés.'),
        ('DEMO_ARCHIVAGE', 'DOCUMENTS', 'Pièces PDF fictives mises à disposition.'),
        ('DEMO_VALIDATION_VISITE', 'VISITES', 'Planning de visites simulées préparé.'),
        ('DEMO_EXPORT', 'RAPPORTS', 'Exemple pédagogique de rapport statistique.'),
        ('DEMO_MAINTENANCE', 'CELLULES', 'Cellule DEMO-P01-C20 placée en maintenance.'),
    ]):
        data['audit'].append({
            'action': action, 'module': module, 'description': '[DEMO] ' + message,
            'created_at_offset': -n,
        })
    data['notifications'] = [
        {'titre': 'Démonstration : registre prêt', 'message': '120 dossiers entièrement fictifs disponibles. Les photos sont des portraits générés.', 'type': 'success'},
        {'titre': 'Démonstration : visites à confirmer', 'message': 'Consultez les demandes simulées dans le registre des visites.', 'type': 'info'},
        {'titre': 'Démonstration : travaux planifiés', 'message': 'La cellule DEMO-P01-C20 est indisponible pour maintenance simulée.', 'type': 'warning'},
    ]
    counts = {}
    for detenu in data['detenus']:
        if detenu['cellule_code']:
            counts[detenu['cellule_code']] = counts.get(detenu['cellule_code'], 0) + 1
    for cell in data['cells']:
        if cell['statut'] == 'disponible' and counts.get(cell['code_cellule'], 0) >= cell['capacite_max']:
            cell['statut'] = 'pleine'
    # As with Django fixtures, stable primary keys preserve even edited business
    # identifiers. This reserved range belongs to this demo dataset only.
    for collection in ('users', 'cells', 'detenus', 'jugements', 'transferts', 'visites', 'documents', 'audit', 'notifications'):
        for number, row in enumerate(data[collection], 900001):
            row['id'] = number
    return data


if __name__ == '__main__':
    dataset = build()
    (ROOT / 'seed.json').write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Jeu fictif écrit dans demo/seed.json : ' + ', '.join(f'{name}={len(dataset[name])}' for name in ('users', 'cells', 'detenus', 'jugements', 'visites', 'transferts', 'documents', 'audit')))
