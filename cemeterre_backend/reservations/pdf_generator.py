from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import cm
import io
from django.utils import timezone


def generate_invoice(reservation):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Titre
    elements.append(Paragraph("FACTURE DE RÉSERVATION", styles['Title']))
    elements.append(Spacer(1, 0.5 * cm))

    # Infos facture
    elements.append(Paragraph(f"Date : {timezone.now().strftime('%d/%m/%Y')}", styles['Normal']))
    elements.append(Paragraph(f"N° Réservation : {reservation.id}", styles['Normal']))
    elements.append(Spacer(1, 0.5 * cm))

    # Infos client
    elements.append(Paragraph("INFORMATIONS CLIENT", styles['Heading2']))
    client_data = [
        ['Nom', f"{reservation.user.last_name} {reservation.user.first_name}"],
        ['Email', reservation.user.email],
        ['Téléphone', reservation.user.phone or '-'],
    ]
    client_table = Table(client_data, colWidths=[5 * cm, 10 * cm])
    client_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(client_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Infos défunt
    elements.append(Paragraph("INFORMATIONS DÉFUNT", styles['Heading2']))
    defunt_data = [
        ['Nom', f"{reservation.deceased_last_name or '-'} {reservation.deceased_first_name or '-'}"],
        ['Date de naissance', str(reservation.deceased_birth_date or '-')],
        ['Date de décès', str(reservation.deceased_death_date or '-')],
    ]
    defunt_table = Table(defunt_data, colWidths=[5 * cm, 10 * cm])
    defunt_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(defunt_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Infos caveau
    elements.append(Paragraph("CAVEAU RÉSERVÉ", styles['Heading2']))
    grave_data = [
        ['Code caveau', reservation.grave.code],
        ['Section', reservation.grave.section.name],
        ['Cimetière', reservation.grave.section.cemetery.name],
        ['Statut', reservation.get_status_display()],
    ]
    grave_table = Table(grave_data, colWidths=[5 * cm, 10 * cm])
    grave_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(grave_table)
    elements.append(Spacer(1, 1 * cm))

    # Pied de page
    elements.append(Paragraph("Merci pour votre confiance.", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)
    return buffer