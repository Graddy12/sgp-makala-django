"""PDF generation with ReportLab (fiche écrou + rapport global)."""
from io import BytesIO

from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleFR', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=14))
    styles.add(ParagraphStyle(name='SubFR', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10, textColor=colors.grey))
    styles.add(ParagraphStyle(name='BodyFR', parent=styles['Normal'], alignment=TA_LEFT, fontSize=10, leading=14))
    return styles


def fiche_ecrou_pdf(detenu):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm)
    styles = _styles()
    story = [
        Paragraph('RÉPUBLIQUE DÉMOCRATIQUE DU CONGO', styles['SubFR']),
        Paragraph('Prison Centrale de Makala — Fiche d\'Écrou', styles['TitleFR']),
        Spacer(1, 0.5 * cm),
    ]
    data = [
        ['Matricule', detenu.matricule],
        ['Nom complet', detenu.full_name],
        ['Date / lieu naissance', f'{detenu.date_naissance} — {detenu.lieu_naissance}'],
        ['Genre / Nationalité', f'{detenu.get_genre_display()} / {detenu.nationalite}'],
        ['État civil', detenu.get_etat_civil_display()],
        ['Statut judiciaire', detenu.get_statut_judiciaire_display()],
        ['Dangerosité', detenu.get_niveau_dangerosite_display()],
        ['Date d\'écrou', timezone.localtime(detenu.date_ecrou).strftime('%d/%m/%Y %H:%M')],
        ['Cellule', detenu.cellule.code_cellule if detenu.cellule else '—'],
        ['Motif d\'inculpation', detenu.motif_inculpation],
        ['Libération prévue', str(detenu.date_liberation_prevue or '—')],
    ]
    table = Table(data, colWidths=[5 * cm, 12 * cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F1F5F9')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(
        f'Document généré le {timezone.localtime().strftime("%d/%m/%Y %H:%M")} — SGP Makala',
        styles['SubFR'],
    ))
    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
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
        Paragraph('Prison Centrale de Makala — Rapport Statistique Général', styles['TitleFR']),
        Paragraph(timezone.localtime().strftime('%d/%m/%Y %H:%M'), styles['SubFR']),
        Spacer(1, 0.4 * cm),
        Paragraph(
            f"Effectif: {kpis['total']} | Prévenus: {kpis['prevenus']} | "
            f"Condamnés: {kpis['condamnes']} | Occupation: {kpis['occupation']}%",
            styles['BodyFR'],
        ),
        Spacer(1, 0.4 * cm),
    ]
    header = ['Matricule', 'Nom', 'Statut', 'Dangerosité', 'Cellule', 'Date écrou']
    data = [header] + stats_rows
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="rapport_sgp_makala.pdf"'
    return response
