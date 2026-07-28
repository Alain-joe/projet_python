# projet_cimetiere/cemeterre_backend/cemetery/geocoding.py

import requests


def get_coordinates_from_address(address: str, city: str = ""):
    """
    Convertit une adresse en (latitude, longitude) via OpenStreetMap (Nominatim).
    100% Gratuit, sans clé API, sans carte bancaire.
    
    Args:
        address: L'adresse complète (ex: "Avenue de l'Indépendance")
        city: La ville (ex: "Pointe-Noire")
    
    Returns:
        Tuple (latitude, longitude) ou (None, None) si échec
    """
    full_address = f"{address}, {city}" if city else address
    
    url = "https://nominatim.openstreetmap.org/search"
    
    params = {
        "q": full_address,
        "format": "json",
        "limit": 1
    }
    
    # Nominatim exige un User-Agent identifiable
    headers = {
        "User-Agent": "GestionCimetiereGI2/1.0 (joealain242@gmail.com)"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data and len(data) > 0:
            # Nominatim retourne lat/lng en chaînes de caractères
            lat = float(data[0]["lat"])
            lng = float(data[0]["lon"])
            print(f"✅ Géocodage réussi: {full_address} → ({lat}, {lng})")
            return lat, lng
        else:
            print(f"⚠️ Adresse non trouvée: {full_address}")
            return None, None
            
    except Exception as e:
        print(f"❌ Erreur de géocodage (Nominatim): {e}")
        return None, None


def get_address_from_coordinates(lat: float, lng: float):
    """
    Convertit des coordonnées GPS en adresse (géocodage inverse).
    Utile pour afficher l'adresse d'un caveau.
    """
    url = "https://nominatim.openstreetmap.org/reverse"
    
    params = {
        "lat": lat,
        "lon": lng,
        "format": "json"
    }
    
    headers = {
        "User-Agent": "GestionCimetiereGI2/1.0 (joealain242@gmail.com)"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data and "display_name" in data:
            return data["display_name"]
        return None
        
    except Exception as e:
        print(f"❌ Erreur géocodage inverse: {e}")
        return None