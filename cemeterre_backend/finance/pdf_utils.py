"""
finance/pdf_utils.py — Génération de facture PDF.

Cahier des charges 2.4 :
  "Facturation : Génération automatique de facture PDF et envoi par
   email sécurisé."

Utilise reportlab (pur Python, aucune dépendance système comme
WeasyPrint/wkhtmltopdf qui posent souvent problème sous Windows).
"""

from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER


def generate_facture_pdf(facture) -> bytes:
    """
    Génère le PDF d'une facture à partir de l'instance Facture (modèle
    finance.models.Facture). Retourne les octets du PDF, prêts à être
    joints à un email ou renvoyés en HttpResponse.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=20 * mm, bottomMargin=20 * mm,
        leftMargin=20 * mm, rightMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleCustom", parent=styles["Title"], alignment=TA_CENTER, fontSize=18,
    )
    right_style = ParagraphStyle("Right", parent=styles["Normal"], alignment=TA_RIGHT)

    elements = []

    elements.append(Paragraph("Cimetière Connect", title_style))
    elements.append(Paragraph("Facture de concession funéraire", styles["Heading3"]))
    elements.append(Spacer(1, 10 * mm))

    reservation = facture.reservation
    grave = reservation.grave if reservation else None
    client = facture.client

    infos_data = [
        ["Numéro de facture", facture.numero],
        ["Date d'émission", facture.created_at.strftime("%d/%m/%Y")],
        ["Date d'échéance", facture.date_echeance.strftime("%d/%m/%Y") if facture.date_echeance else "-"],
        ["Client", f"{client.first_name} {client.last_name}".strip() or client.username],
        ["Email client", client.email],
        ["Caveau", grave.code if grave else "-"],
    ]
    if reservation:
        defunt = f"{reservation.deceased_first_name} {reservation.deceased_last_name}".strip()
        if defunt:
            infos_data.append(["Défunt", defunt])

    infos_table = Table(infos_data, colWidths=[60 * mm, 100 * mm])
    infos_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#496042")),
    ]))
    elements.append(infos_table)
    elements.append(Spacer(1, 12 * mm))

    montant_data = [
        ["Description", "Montant (FCFA)"],
        ["Concession funéraire", f"{facture.montant_total:,.0f}".replace(",", " ")],
        ["Total", f"{facture.montant_total:,.0f}".replace(",", " ")],
    ]
    montant_table = Table(montant_data, colWidths=[110 * mm, 50 * mm])
    montant_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#496042")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E2D9")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(montant_table)
    elements.append(Spacer(1, 15 * mm))

    elements.append(Paragraph(
        f"Statut : {facture.statut.replace('_', ' ').capitalize()}",
        styles["Normal"],
    ))
    elements.append(Spacer(1, 5 * mm))
    elements.append(Paragraph(
        "Merci de bien vouloir régler cette facture avant la date d'échéance indiquée. "
        "Pour toute question, veuillez contacter l'administration du cimetière.",
        styles["Normal"],
    ))

    doc.build(elements)
    return buffer.getvalue()