# projet_cimetiere/cemeterre_backend/finance/utils.py

def format_and_validate_phone(phone: str, expected_operator: str = None):
    """
    Nettoie et valide un numéro de téléphone congolais.
    Accepte les formats : 0612345678 (11 chiffres avec 242) ou 06123456789 (12 chiffres avec 242)
    """
    # 1. Nettoyage : enlever les espaces, tirets, points et le signe +
    clean_phone = str(phone).replace(" ", "").replace("-", "").replace(".", "").replace("+", "")
    
    # 2. Ajout automatique de l'indicatif 242 si l'utilisateur a commencé par 0
    if clean_phone.startswith("06") or clean_phone.startswith("05"):
        clean_phone = "242" + clean_phone
        
    # 3. Vérification de la longueur (242 + 8 ou 9 chiffres = 11 ou 12 caractères)
    if len(clean_phone) not in [11, 12]:
        raise ValueError(f"Numéro invalide. Le numéro doit contenir 11 ou 12 chiffres (ex: 242061234567). Reçu : {clean_phone} ({len(clean_phone)} chiffres)")
        
    # 4. Vérification du préfixe opérateur
    if expected_operator == "mtn" and not clean_phone.startswith("24206"):
        raise ValueError("Ce numéro ne semble pas être un numéro MTN (doit commencer par 06 ou 24206).")
        
    if expected_operator == "airtel" and not clean_phone.startswith("24205"):
        raise ValueError("Ce numéro ne semble pas être un numéro Airtel (doit commencer par 05 ou 24205).")
        
    # 5. Vérification que ce ne sont que des chiffres
    if not clean_phone.isdigit():
        raise ValueError("Le numéro ne doit contenir que des chiffres.")
        
    return clean_phone

# Dans finance/models.py (ou un fichier utils)
from django.db.models import Max
from django.utils import timezone

def generate_facture_numero() -> str:
    """Génère un numéro de facture séquentiel : FACT-YYYY-XXXX"""
    annee = timezone.now().year
    # Trouve le dernier numéro de l'année en cours
    last_facture = Facture.objects.filter(numero__startswith=f"FACT-{annee}-").aggregate(Max('numero'))
    last_numero = last_facture['numero__max']
    
    if last_numero:
        # Extrait le numéro (ex: "FACT-2026-0042" -> 42) et ajoute 1
        dernier_chiffre = int(last_numero.split('-')[-1])
        nouveau_chiffre = dernier_chiffre + 1
    else:
        nouveau_chiffre = 1
        
    return f"FACT-{annee}-{nouveau_chiffre:04d}"