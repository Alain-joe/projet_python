"""
finance/api_pdf_endpoint.py — Extrait à fusionner dans ton finance/api.py existant.

Ajoute l'endpoint GET /finance/factures/{facture_id}/pdf, déjà référencé
dans core/api.py (Endpoints.facture_pdf), pour permettre à l'admin ou au
client de retélécharger une facture à tout moment (pas seulement au
moment de la validation).
"""

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError

from .models import Facture
from .pdf_utils import generate_facture_pdf
from core.permissions import require_role


# À ajouter dans ton router `finance/api.py` existant (celui qui contient
# déjà /finance/factures et /finance/factures/{id}/payer) :

# @router.get("/factures/{facture_id}/pdf")
# @require_role("admin", "secretariat", "client")
def download_facture_pdf(request, facture_id: int):
    facture = get_object_or_404(Facture, id=facture_id)

    # Un client ne peut télécharger que ses propres factures.
    if request.auth.role == "client" and facture.client_id != request.auth.id:
        raise HttpError(403, "Vous n'avez pas accès à cette facture.")

    pdf_bytes = generate_facture_pdf(facture)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="facture_{facture.numero}.pdf"'
    return response