"""Generate readable detention records and statistical reports with ReportLab."""
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleFR', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=14))
    styles.add(ParagraphStyle(name='SubFR', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10, textColor=colors.grey))
    styles.add(ParagraphStyle(name='BodyFR', parent=styles['Normal'], alignment=TA_LEFT, fontSize=10, leading=14))
    styles.add(ParagraphStyle(name='LabelFR', parent=styles['BodyFR'], fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='TableFR', parent=styles['BodyFR'], fontSize=8, leading=11, splitLongWords=True))
    styles.add(ParagraphStyle(name='HeaderFR', parent=styles['TableFR'], fontName='Helvetica-Bold', textColor=colors.white))
    styles.add(ParagraphStyle(name='DemoFR', parent=styles['SubFR'], fontName='Helvetica-Bold', textColor=colors.HexColor('#9A3412')))
    return styles


def _paragraph(value, style):
    # ReportLab Paragraph parses XML; names and verdicts must remain plain text.
    text = '' if value is None else str(value)
    return Paragraph(escape(text).replace('\n', '<br/>'), style)


def _demo_notice(styles):
    if getattr(settings, 'DEMO_MODE', False):
        return [_paragraph('DÉMONSTRATION — Données entièrement fictives', styles['DemoFR']), Spacer(1, 0.25 * cm)]
    return []


def _page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#64748B'))
    if getattr(settings, 'DEMO_MODE', False):
        canvas.drawString(doc.leftMargin, 0.6 * cm, 'DÉMO — DONNÉES FICTIVES')
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 0.6 * cm, f'SGP Makala | Page {doc.page}')
    canvas.restoreState()


def _photo_path(detenu):
    filename = str(detenu.photo or '')
    if not filename:
        return None
    photo_root = (Path(settings.MEDIA_ROOT) / 'photos').resolve()
    path = (photo_root / filename).resolve()
    if path.parent != photo_root or not path.is_file():
        return None
    return path


def _photo(detenu, styles):
    path = _photo_path(detenu)
    if path:
        try:
            return Image(str(path), width=3.2 * cm, height=3.2 * cm, kind='proportional', hAlign='RIGHT', lazy=0)
        except (OSError, ValueError):
            # An old or damaged upload must not prevent the record from exporting.
            pass
    return _paragraph('Photo non disponible', styles['SubFR'])


def _detail_table(rows, width, styles):
    data = [[_paragraph(label, styles['LabelFR']), _paragraph(value, styles['BodyFR'])] for label, value in rows]
    table = Table(data, colWidths=[4.8 * cm, width - 4.8 * cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F1F5F9')),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return table


def _local_datetime(value):
    return timezone.localtime(value).strftime('%d/%m/%Y %H:%M') if value else 'Non renseignée'


def _related_sections(detenu, width, styles):
    story = [_paragraph('Documents judiciaires', styles['Heading2'])]
    documents = list(detenu.documents.all())
    if not documents:
        story.append(_paragraph('Aucun document judiciaire enregistré.', styles['BodyFR']))
    for document in documents:
        story.extend([
            _paragraph(document.titre, styles['Heading3']),
            _detail_table([
                ['Type de document', document.get_type_doc_display()],
                ['Date de dépôt', _local_datetime(document.created_at)],
                ['Taille', f'{document.taille_ko} Ko'],
                ['Déposé par', document.uploade_par.full_name],
            ], width, styles),
        ])
        if document.description:
            story.extend([Spacer(1, 0.2 * cm), _paragraph(document.description, styles['BodyFR'])])
        story.append(Spacer(1, 0.3 * cm))

    story.append(_paragraph('Historique des visites', styles['Heading2']))
    visites = list(detenu.visites.all())
    if not visites:
        story.append(_paragraph('Aucune visite enregistrée.', styles['BodyFR']))
    for visite in visites:
        heure_fin = visite.heure_fin.strftime('%H:%M') if visite.heure_fin else 'Non renseignée'
        story.extend([
            _paragraph(f'{visite.date_visite:%d/%m/%Y} — {visite.visiteur_full_name}', styles['Heading3']),
            _detail_table([
                ['Visiteur', visite.visiteur_full_name],
                ['Lien de parenté', visite.lien_parente],
                ['Horaires', f'{visite.heure_debut:%H:%M} — {heure_fin}'],
                ['Statut', visite.get_statut_display()],
                ["Pièce d'identité", f'{visite.type_piece_identite} — {visite.numero_piece}'],
                ['Téléphone', visite.telephone or 'Non renseigné'],
                ['Enregistrée par', visite.enregistre_par.full_name],
            ], width, styles),
        ])
        if visite.objet_visite:
            story.extend([Spacer(1, 0.2 * cm), _paragraph('Objet de la visite', styles['LabelFR']), _paragraph(visite.objet_visite, styles['BodyFR'])])
        if visite.effets_apportes:
            story.extend([_paragraph('Effets apportés', styles['LabelFR']), _paragraph(visite.effets_apportes, styles['BodyFR'])])
        story.append(Spacer(1, 0.3 * cm))

    story.append(_paragraph('Historique des transferts', styles['Heading2']))
    transferts = list(detenu.transferts.all())
    if not transferts:
        story.append(_paragraph('Aucun transfert enregistré.', styles['BodyFR']))
    for transfert in transferts:
        story.extend([
            _paragraph(f'{transfert.date_transfert:%d/%m/%Y} — {transfert.get_statut_display()}', styles['Heading3']),
            _detail_table([
                ['Provenance', transfert.etablissement_provenance],
                ['Destination', transfert.etablissement_destination],
                ['Statut', transfert.get_statut_display()],
                ['Escorte', transfert.escorte_agents or 'Non renseignée'],
                ['Autorisé par', transfert.autorise_par.full_name],
            ], width, styles),
            Spacer(1, 0.2 * cm),
            _paragraph('Motif du transfert', styles['LabelFR']),
            _paragraph(transfert.motif_transfert, styles['BodyFR']),
        ])
        if transfert.notes:
            story.extend([_paragraph('Notes', styles['LabelFR']), _paragraph(transfert.notes, styles['BodyFR'])])
        story.append(Spacer(1, 0.3 * cm))
    return story


def fiche_ecrou_pdf(detenu):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm)
    styles = _styles()
    story = [
        _paragraph('RÉPUBLIQUE DÉMOCRATIQUE DU CONGO', styles['SubFR']),
        _paragraph("Prison Centrale de Makala — Fiche d'Écrou", styles['TitleFR']),
        *_demo_notice(styles),
        Spacer(1, 0.3 * cm),
    ]
    identity = Table([
        [_paragraph(detenu.full_name, styles['Heading2']), _photo(detenu, styles)],
    ], colWidths=[doc.width - 3.6 * cm, 3.6 * cm])
    identity.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.extend([identity, Spacer(1, 0.3 * cm), _paragraph('Identité et situation judiciaire', styles['Heading2'])])
    data = [
        ['Matricule', detenu.matricule],
        ['Nom complet', detenu.full_name],
        ['Date / lieu naissance', f'{detenu.date_naissance:%d/%m/%Y} — {detenu.lieu_naissance}'],
        ['Genre / Nationalité', f'{detenu.get_genre_display()} / {detenu.nationalite}'],
        ['État civil', detenu.get_etat_civil_display()],
        ['Adresse', detenu.adresse or 'Non renseignée'],
        ['Statut judiciaire', detenu.get_statut_judiciaire_display()],
        ['Dangerosité', detenu.get_niveau_dangerosite_display()],
        ["Date d'écrou", timezone.localtime(detenu.date_ecrou).strftime('%d/%m/%Y %H:%M')],
        ['Libération prévue', detenu.date_liberation_prevue.strftime('%d/%m/%Y') if detenu.date_liberation_prevue else '—'],
    ]
    if detenu.date_liberation_effective:
        data.append(['Libération effective', _local_datetime(detenu.date_liberation_effective)])
    story.extend([
        _detail_table(data, doc.width, styles),
        Spacer(1, 0.3 * cm),
        _paragraph('Affectation pénitentiaire', styles['Heading2']),
    ])
    affectation_active = detenu.statut_judiciaire in ('prevenu', 'condamne')
    if detenu.cellule:
        if not affectation_active:
            story.extend([
                _paragraph('Aucune affectation active.', styles['BodyFR']),
                _paragraph('Référence de cellule conservée', styles['Heading3']),
            ])
        cellule_rows = [
            ['Cellule', detenu.cellule.code_cellule],
            ['Pavillon', detenu.cellule.pavillon],
            ['Bloc', detenu.cellule.bloc],
            ['Statut de la cellule', detenu.cellule.get_statut_display()],
            ['Capacité maximale', f'{detenu.cellule.capacite_max} place(s)'],
        ]
        if affectation_active:
            cellule_rows.append(['Occupation réelle', f'{detenu.cellule.occupation} / {detenu.cellule.capacite_max} place(s)'])
        story.append(_detail_table(cellule_rows, doc.width, styles))
        if affectation_active and detenu.cellule.description:
            story.extend([
                Spacer(1, 0.2 * cm),
                _paragraph('Description de la cellule', styles['Heading3']),
                _paragraph(detenu.cellule.description, styles['BodyFR']),
            ])
    else:
        message = 'Aucune cellule actuellement affectée.' if affectation_active else 'Aucune affectation active.'
        story.append(_paragraph(message, styles['BodyFR']))
    story.extend([
        Spacer(1, 0.3 * cm),
        _paragraph("Motif d'inculpation", styles['Heading3']),
        _paragraph(detenu.motif_inculpation, styles['BodyFR']),
        Spacer(1, 0.4 * cm),
        _paragraph('Historique des jugements', styles['Heading2']),
    ])
    jugements = list(detenu.jugements.all())
    if not jugements:
        story.append(_paragraph('Aucun jugement enregistré.', styles['BodyFR']))
    for jugement in jugements:
        story.append(_paragraph(
            f'{jugement.date_jugement:%d/%m/%Y} — Dossier {jugement.numero_dossier}', styles['Heading3'],
        ))
        peine = f'{jugement.peine_ans} an(s), {jugement.peine_mois} mois ; amende : {jugement.peine_amende} USD'
        story.extend([
            _detail_table([
                ['Tribunal', jugement.tribunal],
                ['Décision', jugement.get_type_decision_display()],
                ['Peine prononcée', peine],
                ['Juge', jugement.juge_nom or '—'],
                ['Enregistré par', jugement.created_by.full_name],
            ], doc.width, styles),
            Spacer(1, 0.2 * cm),
            _paragraph('Résumé du verdict', styles['LabelFR']),
            _paragraph(jugement.resume_verdict, styles['BodyFR']),
            Spacer(1, 0.3 * cm),
        ])
    story.extend(_related_sections(detenu, doc.width, styles))
    story.extend([
        _paragraph('Suivi administratif du dossier', styles['Heading2']),
        _detail_table([
            ['Dossier créé par', f'{detenu.created_by.full_name} — {detenu.created_by.matricule}'],
            ['Date de création', _local_datetime(detenu.created_at)],
            ['Dernière mise à jour', _local_datetime(detenu.updated_at)],
        ], doc.width, styles),
        Spacer(1, 0.3 * cm),
    ])
    story.append(_paragraph(
        f'Document généré le {timezone.localtime().strftime("%d/%m/%Y %H:%M")} — SGP Makala', styles['SubFR'],
    ))
    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="fiche_{detenu.matricule}.pdf"'
    return response


def rapport_global_pdf(stats_rows, kpis):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=1.2 * cm, rightMargin=1.2 * cm, topMargin=1.2 * cm, bottomMargin=1.2 * cm,
    )
    styles = _styles()
    story = [
        _paragraph('Prison Centrale de Makala — Rapport Statistique Général', styles['TitleFR']),
        *_demo_notice(styles),
        _paragraph(timezone.localtime().strftime('%d/%m/%Y %H:%M'), styles['SubFR']),
        Spacer(1, 0.4 * cm),
        _paragraph(
            f"Effectif : {kpis['total']} | Prévenus : {kpis['prevenus']} | "
            f"Condamnés : {kpis['condamnes']} | Occupation : {kpis['occupation']}%", styles['BodyFR'],
        ),
        Spacer(1, 0.4 * cm),
    ]
    header = ['Matricule', 'Nom', 'Statut', 'Dangerosité', 'Cellule', 'Date écrou']
    data = [[_paragraph(value, styles['HeaderFR']) for value in header]]
    data.extend([[_paragraph(value, styles['TableFR']) for value in row] for row in stats_rows])
    # Fixed shares of the printable width prevent long names from widening the page.
    table = Table(data, repeatRows=1, colWidths=[doc.width * share for share in (0.16, 0.30, 0.12, 0.12, 0.18, 0.12)])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="rapport_sgp_makala.pdf"'
    return response
