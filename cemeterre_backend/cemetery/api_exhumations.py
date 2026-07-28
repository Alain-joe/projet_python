"""
cemetery/api_exhumations.py
API complète pour la gestion des exhumations.
CORRECTION : Ajout des imports RejectExhumationIn et CompleteExhumationIn
"""
from ninja import Router
from ninja_jwt.authentication import JWTAuth
from ninja.errors import HttpError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.http import HttpResponse
from django.contrib.auth import get_user_model

from .models import Exhumation, Grave, Inhumation 
# ✅ CORRECTION : Ajout des nouveaux schémas dans l'import
from .schemas import ExhumationIn, ExhumationOut, RejectExhumationIn, CompleteExhumationIn
from users.models import User
from core.permissions import require_role
from core.audit import log_action

def jwt_auth_or_query_param(request):
    try:
        user = JWTAuth().authenticate(request)
        if user:
            return user
    except Exception:
        pass
    
    token = request.GET.get("token")
    if token:
        try:
            from ninja_jwt.tokens import AccessToken
            valid_token = AccessToken(token)
            User = get_user_model()
            return User.objects.get(id=valid_token["user_id"])
        except Exception:
            raise HttpError(401, "Token invalide ou expiré.")
    raise HttpError(401, "Non authentifié.")

router = Router(auth=JWTAuth(), tags=["Exhumations"])

def clean_text_for_pdf(text):
    if not text: return "N/A"
    text = str(text)
    accents = {'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e', 'à': 'a', 'â': 'a', 'î': 'i', 'ï': 'i', 'ô': 'o', 'ù': 'u', 'û': 'u', 'ç': 'c', 'É': 'E', 'È': 'E', 'Ê': 'E', 'À': 'A', 'Î': 'I', 'Ô': 'O', 'Ù': 'U', 'Û': 'U', 'Ç': 'C'}
    for acc, non_acc in accents.items():
        text = text.replace(acc, non_acc)
    return text[:70] 

@router.get("/exhumations", response=list[ExhumationOut])
@require_role("admin", "secretariat", "agent")
def list_exhumations(request, status: str = None):
    queryset = Exhumation.objects.all().select_related("grave", "demandeur", "inhumation", "validated_by")
    if status:
        queryset = queryset.filter(status=status)
    return queryset.order_by("-created_at")

@router.get("/exhumations/{exhumation_id}", response=ExhumationOut)
def get_exhumation(request, exhumation_id: int):
    return get_object_or_404(Exhumation, id=exhumation_id)

@router.post("/exhumations", response=ExhumationOut)
@require_role("admin", "agent", "client")
def create_exhumation(request, data: ExhumationIn):
    inhumation = get_object_or_404(Inhumation, id=data.inhumation_id)
    demandeur_id = data.demandeur_id or request.auth.id
    demandeur = get_object_or_404(User, id=demandeur_id)

    if inhumation.grave.status != "occupied":
        raise HttpError(400, "Ce caveau n'est pas occupé, exhumation impossible")

    exhumation = Exhumation.objects.create(
        inhumation=inhumation,
        grave=inhumation.grave,
        demandeur=demandeur,
        motif=data.motif,
        date_prevue=data.date_prevue,
        status="pending"
    )
    log_action(request.auth, "create", "Exhumation", exhumation.id, f"Demande pour {inhumation.grave.code}")
    return exhumation

@router.put("/exhumations/{exhumation_id}/validate")
@require_role("admin", "secretariat")
def validate_exhumation(request, exhumation_id: int, data: dict = None):
    exhumation = get_object_or_404(Exhumation, id=exhumation_id)
    if exhumation.status != "pending":
        raise HttpError(400, f"Cette demande est déjà {exhumation.get_status_display()}")

    exhumation.status = "approved"
    exhumation.validated_by = request.auth
    exhumation.save(update_fields=["status", "validated_by"])
    log_action(request.auth, "update", "Exhumation", exhumation.id, "Validée par admin")
    return {"message": "Demande d'exhumation validée."}


# ✅ CORRECTION : Utilise maintenant RejectExhumationIn
@router.put("/exhumations/{exhumation_id}/reject")
@require_role("admin", "secretariat")
def reject_exhumation(request, exhumation_id: int, data: RejectExhumationIn):
    """Rejeter une demande d'exhumation avec motif obligatoire."""
    exhumation = get_object_or_404(Exhumation, id=exhumation_id)

    if exhumation.status != "pending":
        raise HttpError(400, f"Cette demande est déjà {exhumation.get_status_display()}")
    
    print("DEBUG REJECT DATA:", data.dict())  # <-- Tu verras les données ici
    
    if not data.motif_rejet or not data.motif_rejet.strip():
        raise HttpError(400, "Le motif du rejet est obligatoire")

    exhumation.status = "rejected"
    exhumation.motif_rejet = data.motif_rejet.strip()
    exhumation.validated_by = request.auth
    exhumation.save(update_fields=["status", "motif_rejet", "validated_by"])

    log_action(request.auth, "update", "Exhumation", exhumation.id, f"Rejetée : {data.motif_rejet}")
    return {"message": "Demande d'exhumation rejetée."}


# ✅ CORRECTION : Utilise maintenant CompleteExhumationIn
@router.put("/exhumations/{exhumation_id}/complete")
@require_role("admin", "agent")
def complete_exhumation(request, exhumation_id: int, data: CompleteExhumationIn):
    """Marquer une exhumation comme effectuée avec la date réelle."""
    exhumation = get_object_or_404(Exhumation, id=exhumation_id)

    if exhumation.status != "approved":
        raise HttpError(400, "L'exhumation doit d'abord être validée")
    
    print("DEBUG COMPLETE DATA:", data.dict())  # <-- Tu verras les données ici
    
    if not data.date_exhumation or not data.date_exhumation.strip():
        raise HttpError(400, "La date réelle d'exhumation est obligatoire")

    exhumation.status = "completed"
    exhumation.date_exhumation = data.date_exhumation.strip()
    if data.observations:
        exhumation.observations = data.observations.strip()
    exhumation.validated_by = request.auth
    exhumation.save()

    # 1. Libérer le caveau
    grave = exhumation.grave
    grave.status = "available"
    grave.last_status_change = timezone.now()
    grave.save(update_fields=["status", "last_status_change"])

    # 2. Résiliation automatique de la concession associée
    if exhumation.inhumation and exhumation.inhumation.concession:
        concession = exhumation.inhumation.concession
        if concession.status == "active":
            concession.status = "resiliee"
            concession.save(update_fields=["status"])

    log_action(request.auth, "status_change", "Exhumation", exhumation.id, f"Effectuée - Caveau {grave.code} libéré")
    return {"message": "Exhumation clôturée. Caveau libéré."}


@router.get("/exhumations/{exhumation_id}/pv/download", auth=jwt_auth_or_query_param)
@require_role("admin", "secretariat")
def download_pv_pdf(request, exhumation_id: int):
    exhumation = get_object_or_404(Exhumation.objects.select_related("grave", "demandeur", "validated_by"), id=exhumation_id)
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="PV_Exhumation_{exhumation.id:06d}.pdf"'
    pdf_content = f"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<</Font<</F1<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>>>>>/Contents 4 0 R>>endobj
4 0 obj<</Length 500>>stream
BT /F1 22 Tf 50 700 Td (PROCES-VERBAL D'EXHUMATION) Tj
0 -60 Td /F1 14 Tf (Reference : PV-{exhumation.id:06d}) Tj
0 -50 Td (Caveau : {clean_text_for_pdf(exhumation.grave.code)}) Tj
0 -30 Td (Demandeur : {clean_text_for_pdf(exhumation.demandeur.username)}) Tj
0 -30 Td (Motif : {clean_text_for_pdf(exhumation.motif)}) Tj
0 -30 Td (Date prevue : {exhumation.date_prevue}) Tj
0 -30 Td (Date reelle : {exhumation.date_exhumation or 'Non renseignee'}) Tj
0 -30 Td (Statut : {clean_text_for_pdf(exhumation.get_status_display())}) Tj
0 -30 Td (Valide par : {clean_text_for_pdf(exhumation.validated_by.username if exhumation.validated_by else 'N/A')}) Tj
0 -30 Td (Observations : {clean_text_for_pdf(exhumation.observations)}) Tj
ET
endstream endobj
xref 0 5
0000000000 65535 f
0000000010 00000 n
0000000053 00000 n
0000000102 00000 n
0000000250 00000 n
trailer<</Size 5/Root 1 0 R>>
startxref
800
%%EOF"""
    response.write(pdf_content.encode('latin-1', errors='replace'))
    return response

@router.get("/exhumations/{exhumation_id}/autorisation/download", auth=jwt_auth_or_query_param)
@require_role("admin", "secretariat")
def download_autorisation_pdf(request, exhumation_id: int):
    exhumation = get_object_or_404(Exhumation.objects.select_related("grave__section__cemetery", "demandeur"), id=exhumation_id)
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Autorisation_Exhumation_{exhumation.id:06d}.pdf"'
    pdf_content = f"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<</Font<</F1<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>>>>>/Contents 4 0 R>>endobj
4 0 obj<</Length 500>>stream
BT /F1 24 Tf 50 700 Td (AUTORISATION D'EXHUMATION) Tj
0 -60 Td /F1 14 Tf (Reference : EXH-{exhumation.id:06d}) Tj
0 -50 Td (Caveau concerne : {clean_text_for_pdf(exhumation.grave.code)}) Tj
0 -30 Td (Section : {clean_text_for_pdf(exhumation.grave.section.name)}) Tj
0 -30 Td (Cimetiere : {clean_text_for_pdf(exhumation.grave.section.cemetery.name)}) Tj
0 -40 Td (Demandeur : {clean_text_for_pdf(exhumation.demandeur.username)}) Tj
0 -30 Td (Motif : {clean_text_for_pdf(exhumation.motif)}) Tj
0 -40 Td (Date prevue : {exhumation.date_prevue}) Tj
0 -30 Td (Statut : {clean_text_for_pdf(exhumation.get_status_display())}) Tj
0 -40 Td /F1 12 Tf (Valide par l'administration) Tj
ET
endstream endobj
xref 0 5
0000000000 65535 f
0000000010 00000 n
0000000053 00000 n
0000000102 00000 n
0000000250 00000 n
trailer<</Size 5/Root 1 0 R>>
startxref
800
%%EOF"""
    response.write(pdf_content.encode('latin-1', errors='replace'))
    return response