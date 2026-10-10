"""Load the committed demonstration dataset without resetting edited records."""
import json
import shutil
import textwrap
from collections import Counter
from datetime import datetime, time, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from accounts.models import Role, User
from core.models import AuditLog, Notification
from prison.models import (
    Cellule, Detenu, DocumentJudiciaire, Jugement, Transfert, Visite,
)


COLLECTIONS = (
    'users', 'cells', 'detenus', 'jugements', 'transferts', 'visites',
    'documents', 'audit', 'notifications',
)


class Command(BaseCommand):
    help = 'Charge les dossiers fictifs de démonstration et restaure les fichiers manquants.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Vérifie le JSON et affiche les volumes sans modifier la base.')

    def handle(self, *args, **options):
        dataset_path = Path(settings.BASE_DIR) / 'demo' / 'seed.json'
        try:
            data = json.loads(dataset_path.read_text(encoding='utf-8'))
            self._validate_dataset(data)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise CommandError(f'Jeu de démonstration invalide : {exc}') from exc
        if options['dry_run']:
            self.stdout.write('Données entièrement fictives : ' + ', '.join(f'{name}={len(data[name])}' for name in COLLECTIONS))
            return

        admin = User.objects.filter(email=settings.SGP_ADMIN_EMAIL, role=Role.ADMIN).first()
        if admin is None:
            admin = User.objects.filter(role=Role.ADMIN).order_by('pk').first()
        if admin is None:
            raise CommandError('Créez le compte administrateur avec bootstrap_admin avant seed_demo.')

        self.today = timezone.localdate()
        self.created = Counter()
        self.restored = Counter()
        self.missing_portraits = set()
        with transaction.atomic():
            staff = self._users(data['users'])
            creator = staff.get('DEMO-USR-GRE', admin)
            visits_agent = staff.get('DEMO-USR-VIS', admin)
            director = staff.get('DEMO-USR-DIR', admin)
            cells = self._cells(data['cells'])
            detainees = self._detenus(data['detenus'], cells, creator)
            self._judgments(data['jugements'], detainees, creator)
            self._transfers(data['transferts'], detainees, director)
            self._visits(data['visites'], detainees, visits_agent)
            self._documents(data['documents'], detainees, creator)
            self._audit(data['audit'], creator)
            self._notifications(data['notifications'])

        totals = ', '.join(f'{name}={self.created[name]}' for name in COLLECTIONS)
        self.stdout.write(self.style.SUCCESS(f'Démonstration fictive prête. Nouveaux enregistrements : {totals}.'))
        self.stdout.write(f'Fichiers restaurés : portraits={self.restored["portraits"]}, PDF={self.restored["documents"]}. Les dossiers existants sont conservés.')
        if self.missing_portraits:
            self.stdout.write(self.style.WARNING(f'{len(self.missing_portraits)} portraits sources absents. Relancez seed_demo après ajout dans static/demo/portraits/.'))

    @staticmethod
    def _validate_dataset(data):
        if data.get('version') != 1 or data.get('fictional') is not True:
            raise ValueError('Version 1 et fictional=true requis.')
        for name in COLLECTIONS:
            if not isinstance(data.get(name), list):
                raise ValueError(f'Collection {name} manquante.')
            ids = [row['id'] for row in data[name]]
            if len(set(ids)) != len(ids) or any(not isinstance(pk, int) or not 900000 < pk < 910000 for pk in ids):
                raise ValueError(f'Identifiants stables invalides dans {name}.')
        cells = {row['code_cellule']: row for row in data['cells']}
        people = {row['matricule']: row for row in data['detenus']}
        if len(cells) != len(data['cells']) or len(people) != len(data['detenus']):
            raise ValueError('Clés de cellule ou matricules dupliqués.')
        occupations = Counter()
        for row in data['detenus']:
            if not row['matricule'].startswith('DEMO-'):
                raise ValueError('Matricule de démonstration requis.')
            birthday = datetime.strptime(row['date_naissance'], '%Y-%m-%d').date()
            today = timezone.localdate()
            age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
            if age < 18:
                raise ValueError('Les identités de démonstration doivent être adultes.')
            cell = row.get('cellule_code')
            if cell and cell not in cells:
                raise ValueError(f'Cellule inconnue : {cell}.')
            if cell and row['statut_judiciaire'] in ('prevenu', 'condamne'):
                occupations[cell] += 1
        for code, occupation in occupations.items():
            if occupation > cells[code]['capacite_max'] or cells[code]['statut'] == 'maintenance':
                raise ValueError(f'Capacité incohérente pour {code}.')
        for collection in ('jugements', 'transferts', 'visites', 'documents'):
            for row in data[collection]:
                if row['detenu'] not in people:
                    raise ValueError(f'Détenu inconnu dans {collection}.')
        for row in data['documents']:
            filename = row['fichier_path']
            if Path(filename).name != filename or not filename.startswith('demo_') or not filename.endswith('.pdf'):
                raise ValueError('Nom PDF de démonstration invalide.')

    def _date(self, offset):
        return self.today + timedelta(days=offset)

    def _datetime(self, offset):
        return timezone.make_aware(datetime.combine(self._date(offset), time(10, 0)))

    def _users(self, rows):
        staff = {}
        for row in rows:
            defaults = dict(row)
            pk = defaults.pop('id')
            matricule = defaults['matricule']
            # These are display accounts only. No reusable/public login is seeded.
            defaults.update(password='!', is_staff=False, is_superuser=False)
            user, created = User.objects.get_or_create(pk=pk, defaults=defaults)
            self.created['users'] += created
            staff[matricule] = user
        return staff

    def _cells(self, rows):
        cells = {}
        for row in rows:
            defaults = dict(row)
            pk = defaults.pop('id')
            code = defaults['code_cellule']
            cell, created = Cellule.objects.get_or_create(pk=pk, defaults=defaults)
            self.created['cells'] += created
            cells[code] = cell
        return cells

    def _detenus(self, rows, cells, creator):
        detainees = {}
        for row in rows:
            defaults = dict(row)
            pk = defaults.pop('id')
            matricule = defaults['matricule']
            cell_code = defaults.pop('cellule_code', None)
            defaults['cellule'] = cells.get(cell_code)
            defaults['date_ecrou'] = self._datetime(defaults.pop('date_ecrou_offset'))
            for field in ('date_liberation_prevue', 'date_liberation_effective'):
                offset = defaults.pop(field + '_offset', None)
                if offset is not None:
                    defaults[field] = self._datetime(offset) if field.endswith('effective') else self._date(offset)
            defaults['created_by'] = creator
            person, created = Detenu.objects.get_or_create(pk=pk, defaults=defaults)
            self.created['detenus'] += created
            if created:
                Detenu.objects.filter(pk=person.pk).update(created_at=defaults['date_ecrou'])
            # Restore a committed portrait only while it remains the selected photo.
            if person.photo == row['photo']:
                self._portrait(person.photo)
            detainees[matricule] = person
        return detainees

    def _portrait(self, filename):
        destination = Path(settings.MEDIA_ROOT) / 'photos' / filename
        if destination.exists():
            return
        source = Path(settings.BASE_DIR) / 'static' / 'demo' / 'portraits' / filename.removeprefix('demo_')
        if not source.is_file():
            self.missing_portraits.add(source.name)
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        self.restored['portraits'] += 1

    def _judgments(self, rows, detainees, creator):
        for row in rows:
            defaults = dict(row)
            pk = defaults.pop('id')
            person = detainees[defaults.pop('detenu')]
            defaults['detenu'] = person
            defaults['date_jugement'] = self._date(defaults.pop('date_jugement_offset'))
            defaults['created_by'] = creator
            _, created = Jugement.objects.get_or_create(pk=pk, defaults=defaults)
            self.created['jugements'] += created

    def _transfers(self, rows, detainees, director):
        for row in rows:
            defaults = dict(row)
            pk = defaults.pop('id')
            person = detainees[defaults.pop('detenu')]
            defaults['detenu'] = person
            defaults['date_transfert'] = self._date(defaults.pop('date_transfert_offset'))
            defaults['autorise_par'] = director
            _, created = Transfert.objects.get_or_create(pk=pk, defaults=defaults)
            self.created['transferts'] += created

    def _visits(self, rows, detainees, visits_agent):
        for row in rows:
            defaults = dict(row)
            pk = defaults.pop('id')
            person = detainees[defaults.pop('detenu')]
            defaults['detenu'] = person
            defaults['date_visite'] = self._date(defaults.pop('date_visite_offset'))
            defaults['enregistre_par'] = visits_agent
            _, created = Visite.objects.get_or_create(pk=pk, defaults=defaults)
            self.created['visites'] += created

    def _documents(self, rows, detainees, creator):
        for row in rows:
            defaults = dict(row)
            pk = defaults.pop('id')
            person = detainees[defaults.pop('detenu')]
            defaults['detenu'] = person
            filename = defaults['fichier_path']
            defaults['uploade_par'] = creator
            doc, created = DocumentJudiciaire.objects.get_or_create(pk=pk, defaults=defaults)
            self.created['documents'] += created
            if doc.fichier_path != filename:
                continue
            destination = Path(settings.MEDIA_ROOT) / 'documents' / filename
            if not destination.exists():
                self._pdf(destination, person, doc)
                self.restored['documents'] += 1
            if created:
                doc.taille_ko = max(1, (destination.stat().st_size + 1023) // 1024)
                doc.save(update_fields=['taille_ko'])

    @staticmethod
    def _pdf(destination, person, document):
        destination.parent.mkdir(parents=True, exist_ok=True)
        pdf = canvas.Canvas(str(destination), pagesize=A4, invariant=1)
        width, height = A4
        pdf.setTitle(document.titre)
        pdf.setAuthor('SGP Makala - démonstration fictive')
        pdf.saveState()
        pdf.translate(width / 2, height / 2)
        pdf.rotate(35)
        pdf.setFillColor(colors.HexColor('#E2E8F0'))
        pdf.setFont('Helvetica-Bold', 42)
        pdf.drawCentredString(0, 0, 'SPECIMEN FICTIF')
        pdf.restoreState()
        pdf.setFillColor(colors.HexColor('#0F172A'))
        pdf.setFont('Helvetica-Bold', 18)
        pdf.drawString(42, height - 58, 'SGP MAKALA | DÉMONSTRATION')
        pdf.setFont('Helvetica-Bold', 12)
        pdf.drawString(42, height - 87, 'DOCUMENT FICTIF - SANS VALEUR JURIDIQUE')
        text = pdf.beginText(42, height - 128)
        text.setFont('Helvetica', 11)
        text.setLeading(19)
        for line in [
            document.titre, '', f'Identité simulée : {person.full_name}',
            f'Référence de démonstration : {person.matricule}',
            f'Nature : {document.get_type_doc_display()}', '',
            document.description or 'Pièce pédagogique fictive.', '',
            'Les noms, faits, pièces et décisions contenus dans cet exemple sont inventés.',
            'Ce spécimen sert uniquement à illustrer le classement, la consultation',
            'et le téléchargement des dossiers pendant la soutenance.', '',
            'Aucune signature, aucun sceau officiel et aucun acte judiciaire réel.',
        ]:
            for wrapped in textwrap.wrap(line, width=80) or ['']:
                text.textLine(wrapped)
        pdf.drawText(text)
        pdf.setFillColor(colors.HexColor('#64748B'))
        pdf.setFont('Helvetica', 9)
        pdf.drawCentredString(width / 2, 35, 'DONNÉES FICTIVES | Prototype pédagogique SGP Makala')
        pdf.showPage()
        pdf.save()

    def _audit(self, rows, creator):
        for row in rows:
            defaults = dict(row)
            pk = defaults.pop('id')
            offset = defaults.pop('created_at_offset')
            defaults.update(user=creator, user_nom=creator.full_name, role=creator.role, ip_address='127.0.0.1', user_agent='SGP demo seed (fictional)')
            entry, created = AuditLog.objects.get_or_create(pk=pk, defaults=defaults)
            self.created['audit'] += created
            if created:
                AuditLog.objects.filter(pk=entry.pk).update(created_at=self._datetime(offset))

    def _notifications(self, rows):
        for row in rows:
            defaults = dict(row)
            pk = defaults.pop('id')
            _, created = Notification.objects.get_or_create(pk=pk, defaults=defaults)
            self.created['notifications'] += created
