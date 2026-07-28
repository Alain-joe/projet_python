"""
projet_cimetiere/cemeterre_backend/cemetery/pdf_utils.py
Génération du contrat de concession funéraire (modèle juridique).
Conforme CDC §2.5 : Documents légaux avec clauses et signatures.
CORRECTION : Affichage dynamique du type de concession (trentenaire, cinquantenaire, etc.)
"""

from io import BytesIO
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
    PageBreak, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT


def generate_concession_contrat_pdf(concession) -> bytes:
    """
    Génère un contrat de concession funéraire juridique complet.
    Inclut : en-tête, identification, clauses, signatures.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=25 * mm, bottomMargin=25 * mm,
        leftMargin=20 * mm, rightMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'ContractTitle', parent=styles['Title'],
        fontSize=18, alignment=TA_CENTER, spaceAfter=6*mm,
        textColor=colors.HexColor("#1A2B4C")
    )
    subtitle_style = ParagraphStyle(
        'ContractSubtitle', parent=styles['Normal'],
        fontSize=11, alignment=TA_CENTER, spaceAfter=10*mm,
        textColor=colors.HexColor("#496042")
    )
    section_style = ParagraphStyle(
        'SectionTitle', parent=styles['Heading2'],
        fontSize=13, spaceBefore=8*mm, spaceAfter=4*mm,
        textColor=colors.HexColor("#1A2B4C"),
        borderWidth=1, borderColor=colors.HexColor("#496042"),
        borderPadding=4
    )
    clause_style = ParagraphStyle(
        'Clause', parent=styles['Normal'],
        fontSize=10, alignment=TA_JUSTIFY, spaceAfter=3*mm,
        leftIndent=5*mm
    )
    info_style = ParagraphStyle(
        'Info', parent=styles['Normal'],
        fontSize=10, spaceAfter=2*mm
    )

    elements = []

    # ==================================================================
    # EN-TÊTE
    # ==================================================================
    elements.append(Paragraph("RÉPUBLIQUE DU CONGO", ParagraphStyle('Header', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10)))
    elements.append(Paragraph("Union - Travail - Progrès", ParagraphStyle('Header2', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9, textColor=colors.grey)))
    elements.append(Spacer(1, 8*mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#496042")))
    elements.append(Spacer(1, 5*mm))
    
    elements.append(Paragraph("CONTRAT DE CONCESSION FUNÉRAIRE", title_style))
    elements.append(Paragraph("N° CONC-" + str(concession.id).zfill(6), subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#496042")))
    elements.append(Spacer(1, 8*mm))

    # ==================================================================
    # ENTRE LES SOUSSIGNÉS
    # ==================================================================
    elements.append(Paragraph("ENTRE LES SOUSSIGNÉS", section_style))
    
    elements.append(Paragraph("<b>Le Cimetière Municipal</b>, représenté par son Directeur,", info_style))
    elements.append(Paragraph("• Adresse : Mpita, Pointe-Noire", info_style))
    elements.append(Paragraph("• Téléphone : +242 06 910 37 15", info_style))
    elements.append(Paragraph("• Email : contact@cimetiere-pn.cg", info_style))
    elements.append(Spacer(1, 4*mm))
    
    elements.append(Paragraph("Ci-après dénommé <b>« le Concédant »</b>", info_style))
    elements.append(Spacer(1, 6*mm))
    
    elements.append(Paragraph("<b>ET</b>", ParagraphStyle('ET', parent=styles['Normal'], alignment=TA_CENTER, fontSize=11)))
    elements.append(Spacer(1, 6*mm))
    
    user = concession.user
    elements.append(Paragraph(f"<b>M./Mme {user.first_name or ''} {user.last_name or user.username}</b>", info_style))
    elements.append(Paragraph(f"• Email : {user.email or 'Non renseigné'}", info_style))
    elements.append(Paragraph(f"• Téléphone : {getattr(user, 'phone', 'Non renseigné') or 'Non renseigné'}", info_style))
    elements.append(Spacer(1, 4*mm))
    
    elements.append(Paragraph("Ci-après dénommé <b>« le Concessionnaire »</b>", info_style))
    elements.append(Spacer(1, 8*mm))

    # ==================================================================
    # IL A ÉTÉ CONVENU CE QUI SUIT
    # ==================================================================
    elements.append(Paragraph("IL A ÉTÉ CONVENU CE QUI SUIT", section_style))

    # ARTICLE 1 - OBJET
    elements.append(Paragraph("<b>ARTICLE 1 — OBJET DU CONTRAT</b>", info_style))
    elements.append(Paragraph(
        "Le présent contrat a pour objet l'attribution au Concessionnaire d'un droit d'usage sur un emplacement "
        "funéraire (caveau) sis dans le Cimetière Municipal de Pointe-Noire, conformément à la réglementation "
        "funéraire en vigueur.",
        clause_style
    ))

    # ARTICLE 2 - DESCRIPTION
    elements.append(Paragraph("<b>ARTICLE 2 — DESCRIPTION DE LA CONCESSION</b>", info_style))
    
    grave = concession.grave
    section_name = grave.section.name if grave.section else "Non renseignée"
    
    # ✅ CORRECTION : Utilisation de get_type_concession_display() pour afficher "Trentenaire (30 ans)" etc.
    desc_data = [
        ["Code du caveau", grave.code],
        ["Section", section_name],
        ["Type de concession", concession.get_type_concession_display()],
        ["Durée", f"{concession.duree_annees} ans" if concession.duree_annees else "Perpétuelle"],
        ["Date de début", concession.date_debut.strftime("%d/%m/%Y")],
        ["Date de fin", concession.date_fin.strftime("%d/%m/%Y") if concession.date_fin else "Perpétuelle"],
        ["Montant réglé", f"{concession.montant:,.0f} FCFA".replace(",", " ")],
        ["Nombre de renouvellements", str(concession.renewed_count)],
    ]
    
    desc_table = Table(desc_data, colWidths=[70*mm, 90*mm])
    desc_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#F5F3EE")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(desc_table)
    elements.append(Spacer(1, 6*mm))

    # ARTICLE 3 - OBLIGATIONS
    elements.append(Paragraph("<b>ARTICLE 3 — OBLIGATIONS DU CONCESSIONNAIRE</b>", info_style))
    elements.append(Paragraph("Le Concessionnaire s'engage à :", clause_style))
    obligations = [
        "Respecter le règlement intérieur du cimetière ;",
        "Assurer l'entretien régulier de la sépulture ;",
        "Ne pas céder ou transférer la concession sans autorisation écrite du Concédant ;",
        "Payer les redevances annuelles d'entretien le cas échéant ;",
        "Informer le Concédant de tout changement d'adresse."
    ]
    for i, obs in enumerate(obligations, 1):
        elements.append(Paragraph(f"{i}. {obs}", clause_style))
    elements.append(Spacer(1, 4*mm))

    # ARTICLE 4 - DROITS
    elements.append(Paragraph("<b>ARTICLE 4 — DROITS DU CONCESSIONNAIRE</b>", info_style))
    elements.append(Paragraph("Le Concessionnaire bénéficie des droits suivants :", clause_style))
    droits = [
        "Droit d'inhumation dans le caveau attribué ;",
        "Droit de renouvellement de la concession avant son expiration ;",
        "Droit de demander la résiliation avec restitution proportionnelle ;",
        "Droit de visite et d'entretien de la sépulture aux heures d'ouverture."
    ]
    for i, drt in enumerate(droits, 1):
        elements.append(Paragraph(f"{i}. {drt}", clause_style))
    elements.append(Spacer(1, 4*mm))

    # ARTICLE 5 - RENOUVELLEMENT
    elements.append(Paragraph("<b>ARTICLE 5 — RENOUVELLEMENT</b>", info_style))
    elements.append(Paragraph(
        "La concession temporaire peut être renouvelée pour une durée identique ou différente (5, 10, 15 ans "
        "ou durée personnalisée). Le prix du renouvellement est identique au prix initial. Le renouvellement "
        "doit être demandé avant la date d'expiration. À défaut, la concession sera considérée comme expirée "
        "et le caveau pourra être réattribué après une procédure légale.",
        clause_style
    ))
    elements.append(Spacer(1, 4*mm))

    # ARTICLE 6 - RÉSILIATION
    elements.append(Paragraph("<b>ARTICLE 6 — RÉSILIATION</b>", info_style))
    elements.append(Paragraph(
        "La concession peut être résiliée : (a) à la demande du Concessionnaire ; (b) par décision administrative "
        "en cas de non-respect des obligations ; (c) suite à une exhumation. En cas de résiliation, le caveau "
        "est libéré et remis à la disposition du Cimetière.",
        clause_style
    ))
    elements.append(Spacer(1, 4*mm))

    # ARTICLE 7 - ARCHIVAGE
    elements.append(Paragraph("<b>ARTICLE 7 — ARCHIVAGE ET CONSERVATION</b>", info_style))
    elements.append(Paragraph(
        "Conformément aux obligations légales, le présent contrat et tous les documents associés seront conservés "
        "par le Concédant pour une durée minimale de 50 ans. Le Concessionnaire recevra une copie du présent contrat.",
        clause_style
    ))
    elements.append(Spacer(1, 8*mm))

    # ==================================================================
    # SIGNATURES
    # ==================================================================
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#496042")))
    elements.append(Spacer(1, 6*mm))
    elements.append(Paragraph("SIGNATURES", section_style))
    elements.append(Spacer(1, 4*mm))
    
    elements.append(Paragraph("Fait à Pointe-Noire, le " + timezone.now().strftime("%d/%m/%Y"), info_style))
    elements.append(Spacer(1, 15*mm))
    
    sig_data = [
        ["Le Concédant (Directeur)", "Le Concessionnaire"],
        ["", ""],
        ["", ""],
        ["", ""],
        ["Signature et cachet", "Signature précédée de « Lu et approuvé »"],
    ]
    sig_table = Table(sig_data, colWidths=[80*mm, 80*mm])
    sig_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor("#496042")),
    ]))
    elements.append(sig_table)
    
    elements.append(Spacer(1, 10*mm))
    elements.append(Paragraph(
        f"Contrat N° CONC-{concession.id:06d} — Généré le {timezone.now().strftime('%d/%m/%Y à %H:%M')}",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.grey)
    ))

    doc.build(elements)
    return buffer.getvalue()