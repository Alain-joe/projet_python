# projet_cimetiere/cemeterre_backend/cemeterre_backend/map_views.py

from django.http import HttpResponse, JsonResponse
from cemetery.models import Grave
import json

# 🎨 Code couleur conforme au cahier des charges
STATUS_COLORS = {
    "available":  "#2E7D32",  # Vert - Disponible
    "reserved":   "#F57C00",  # Orange - Réservé/En attente
    "occupied":   "#C62828",  # Rouge - Occupé/Validé
    "unusable":   "#757575",  # Gris - Non exploitable
}

STATUS_LABELS = {
    "available":  "Disponible",
    "reserved":   "Réservé",
    "occupied":   "Occupé",
    "unusable":   "Non exploitable",
}


def carte_view(request):
    """Page HTML de la carte Leaflet avec chargement AJAX des caveaux (performance < 2s)"""
    html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Carte Interactive du Cimetière</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
<style>
    html, body, #map { height: 100%; margin: 0; padding: 0; }
    .legend {
        background: white;
        padding: 10px 14px;
        border-radius: 6px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        font-family: Arial, sans-serif;
        font-size: 13px;
        line-height: 1.8;
    }
    .legend i {
        width: 14px; height: 14px;
        display: inline-block;
        margin-right: 6px;
        border-radius: 50%;
        border: 2px solid #fff;
        box-shadow: 0 0 2px rgba(0,0,0,0.5);
    }
    .filters {
        position: absolute;
        top: 10px;
        right: 10px;
        z-index: 1000;
        background: white;
        padding: 10px;
        border-radius: 6px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        font-family: Arial, sans-serif;
    }
    .filters label { margin-right: 10px; cursor: pointer; }
    .stats {
        position: absolute;
        bottom: 10px;
        left: 10px;
        z-index: 1000;
        background: white;
        padding: 10px 14px;
        border-radius: 6px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        font-family: Arial, sans-serif;
        font-size: 13px;
    }
</style>
</head>
<body>
<div id="map"></div>

<div class="filters">
    <strong>Filtres :</strong>
    <label><input type="checkbox" class="status-filter" value="available" checked> 
        <span style="color:#2E7D32">●</span> Disponibles</label>
    <label><input type="checkbox" class="status-filter" value="reserved" checked> 
        <span style="color:#F57C00">●</span> Réservés</label>
    <label><input type="checkbox" class="status-filter" value="occupied" checked> 
        <span style="color:#C62828">●</span> Occupés</label>
    <label><input type="checkbox" class="status-filter" value="unusable" checked> 
        <span style="color:#757575">●</span> Non exploitables</label>
</div>

<div class="stats" id="stats">Chargement...</div>

<script>
    const STATUS_COLORS = {
        available: "#2E7D32",
        reserved:  "#F57C00",
        occupied:  "#C62828",
        unusable:  "#757575"
    };
    const STATUS_LABELS = {
        available: "Disponible",
        reserved:  "Réservé",
        occupied:  "Occupé",
        unusable:  "Non exploitable"
    };

    // Initialisation de la carte (Pointe-Noire par défaut)
    const map = L.map('map').setView([-4.7989, 11.8636], 16);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap'
    }).addTo(map);

    // Cluster pour performance (milliers de marqueurs)
    const markers = L.markerClusterGroup({
        maxClusterRadius: 40,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false
    });
    map.addLayer(markers);

    let allFeatures = [];
    let currentMarkers = {};

    // Légende
    const legend = L.control({position: 'bottomright'});
    legend.onAdd = function() {
        const div = L.DomUtil.create('div', 'legend');
        div.innerHTML = '<strong>Statut des caveaux</strong><br>' +
            '<i style="background:#2E7D32"></i> Disponible<br>' +
            '<i style="background:#F57C00"></i> Réservé<br>' +
            '<i style="background:#C62828"></i> Occupé<br>' +
            '<i style="background:#757575"></i> Non exploitable';
        return div;
    };
    legend.addTo(map);

    // Chargement AJAX des caveaux (GeoJSON)
    async function loadGraves() {
        try {
            const response = await fetch('/api/cemetery/graves-map');
            const data = await response.json();
            allFeatures = data.features || [];
            renderMarkers();
            updateStats();
        } catch (e) {
            console.error("Erreur chargement carte:", e);
            document.getElementById('stats').innerText = "Erreur de chargement";
        }
    }

    // Affichage des marqueurs selon filtres
    function renderMarkers() {
        markers.clearLayers();
        currentMarkers = {};
        const activeFilters = Array.from(document.querySelectorAll('.status-filter:checked'))
            .map(cb => cb.value);

        allFeatures.forEach(f => {
            if (!activeFilters.includes(f.properties.status)) return;
            const [lng, lat] = f.geometry.coordinates;
            const color = STATUS_COLORS[f.properties.status] || "#757575";
            const label = STATUS_LABELS[f.properties.status] || "Inconnu";
            
            const marker = L.circleMarker([lat, lng], {
                radius: 9,
                fillColor: color,
                color: "#fff",
                weight: 2,
                opacity: 1,
                fillOpacity: 0.9
            });
            marker.bindPopup(
                `<b>Caveau ${f.properties.code}</b><br>` +
                `Statut: <span style="color:${color};font-weight:bold">${label}</span><br>` +
                `Prix: ${f.properties.price || '-'} FC`
            );
            markers.addLayer(marker);
            currentMarkers[f.properties.id] = marker;
        });
    }

    // Statistiques
    function updateStats() {
        const counts = { available: 0, reserved: 0, occupied: 0, unusable: 0, total: allFeatures.length };
        allFeatures.forEach(f => { if (counts[f.properties.status] !== undefined) counts[f.properties.status]++; });
        const rate = counts.total > 0 ? ((counts.occupied / counts.total) * 100).toFixed(1) : 0;
        document.getElementById('stats').innerHTML = 
            `<strong>Total:</strong> ${counts.total} | ` +
            `<span style="color:#2E7D32">Disponibles: ${counts.available}</span> | ` +
            `<span style="color:#F57C00">Réservés: ${counts.reserved}</span> | ` +
            `<span style="color:#C62828">Occupés: ${counts.occupied}</span> | ` +
            `<strong>Taux occupation: ${rate}%</strong>`;
    }

    // Événements filtres
    document.querySelectorAll('.status-filter').forEach(cb => {
        cb.addEventListener('change', () => { renderMarkers(); updateStats(); });
    });

    // Lancement
    loadGraves();
</script>
</body>
</html>"""
    return HttpResponse(html, content_type="text/html; charset=utf-8")


def graves_geojson(request):
    """API GeoJSON des caveaux pour la carte (optimisé < 2s)"""
    cemetery_id = request.GET.get("cemetery_id")
    graves = Grave.objects.filter(location__isnull=False)
    if cemetery_id:
        graves = graves.filter(section__cemetery_id=cemetery_id)

    features = []
    for g in graves:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [g.location.x, g.location.y]
            },
            "properties": {
                "id": g.id,
                "code": g.code,
                "status": g.status,
                "price": str(g.price) if g.price else None,
                "section": g.section.name if g.section else None,
            }
        })
    return JsonResponse({
        "type": "FeatureCollection",
        "features": features
    })