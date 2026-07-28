"""
cemetery/geometry_service.py — Service de calcul géométrique pour le cimetière.
Utilise la bibliothèque Shapely pour les opérations géométriques complexes.
"""
import math
from typing import List, Dict, Optional
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union


class GeometryService:
    """Service pour les calculs géométriques liés au cimetière."""
    
    # Constante : 1 degré de latitude ≈ 111 111 mètres
    METERS_PER_DEGREE_LAT = 111111.0
    
    @staticmethod
    def calculate_polygon_area(coords: List[List[float]]) -> float:
        """
        Calcule la surface d'un polygone en m² à partir de coordonnées GPS.
        Args:
            coords: Liste de [latitude, longitude] définissant le polygone
        Returns:
            Surface en mètres carrés
        """
        if not coords or len(coords) < 3:
            return 0.0
        
        # Convertir les coordonnées GPS en mètres (projection locale simplifiée)
        origin_lat = coords[0][0]
        origin_lng = coords[0][1]
        
        meters_per_degree_lng = GeometryService.METERS_PER_DEGREE_LAT * math.cos(math.radians(origin_lat))
        
        coords_meters = []
        for lat, lng in coords:
            x = (lng - origin_lng) * meters_per_degree_lng
            y = (lat - origin_lat) * GeometryService.METERS_PER_DEGREE_LAT
            coords_meters.append((x, y))
        
        polygon = Polygon(coords_meters)
        return abs(polygon.area)
    
    @staticmethod
    def calculate_cemetery_bounds(
        center_lat: float, 
        center_lng: float, 
        length: float, 
        width: float
    ) -> Dict[str, float]:
        """
        Calcule les limites (bounds) du cimetière à partir du centre et des dimensions.
        Returns:
            Dict avec north, south, east, west
        """
        delta_lat = (width / 2) / GeometryService.METERS_PER_DEGREE_LAT
        delta_lng = (length / 2) / (GeometryService.METERS_PER_DEGREE_LAT * math.cos(math.radians(center_lat)))
        
        return {
            "north": center_lat + delta_lat,
            "south": center_lat - delta_lat,
            "east": center_lng + delta_lng,
            "west": center_lng - delta_lng,
        }
    
    @staticmethod
    def create_cemetery_polygon(bounds: Dict[str, float]) -> Polygon:
        """Crée un polygone représentant le cimetière à partir de ses bounds."""
        return box(
            bounds["west"],
            bounds["south"],
            bounds["east"],
            bounds["north"]
        )
    
    @staticmethod
    def create_allee_polygon_meters(
        coordinates: List[List[float]], 
        width: float
    ) -> Optional[Polygon]:
        """
        Crée un polygone représentant une allée à partir de son tracé et de sa largeur.
        Le résultat est en mètres (coordonnées relatives à l'origine).
        """
        if not coordinates or len(coordinates) < 2:
            return None
        
        origin_lat = coordinates[0][0]
        origin_lng = coordinates[0][1]
        meters_per_degree_lng = GeometryService.METERS_PER_DEGREE_LAT * math.cos(math.radians(origin_lat))
        
        # Convertir en coordonnées mètres
        coords_meters = []
        for lat, lng in coordinates:
            x = (lng - origin_lng) * meters_per_degree_lng
            y = (lat - origin_lat) * GeometryService.METERS_PER_DEGREE_LAT
            coords_meters.append((x, y))
        
        line = LineString(coords_meters)
        # Buffer de la moitié de la largeur de chaque côté
        allee_polygon = line.buffer(width / 2, cap_style=2)  # cap_style=2 = extrémités plates
        
        return allee_polygon
    
    @staticmethod
    def split_cemetery_by_allees(
        cemetery_polygon: Polygon,
        allee_polygons: List[Polygon]
    ) -> List[Polygon]:
        """
        Découpe le polygone du cimetière par les allées pour obtenir les sections.
        Returns:
            Liste des polygones représentant les sections exploitables
        """
        if not allee_polygons:
            return [cemetery_polygon]
        
        allees_union = unary_union(allee_polygons)
        sections_polygon = cemetery_polygon.difference(allees_union)
        
        if sections_polygon.is_empty:
            return []
        
        if sections_polygon.geom_type == 'MultiPolygon':
            return [p for p in sections_polygon.geoms if p.area > 1]  # Ignorer les trop petits
        elif sections_polygon.geom_type == 'Polygon':
            return [sections_polygon]
        return []
    
    @staticmethod
    def polygon_to_coords(polygon: Polygon, origin_lat: float, origin_lng: float) -> List[List[float]]:
        """
        Convertit un polygone Shapely (en mètres) en coordonnées GPS.
        Returns:
            Liste de [lat, lng]
        """
        coords = []
        meters_per_degree_lng = GeometryService.METERS_PER_DEGREE_LAT * math.cos(math.radians(origin_lat))
        
        for x, y in polygon.exterior.coords:
            lat = origin_lat + (y / GeometryService.METERS_PER_DEGREE_LAT)
            lng = origin_lng + (x / meters_per_degree_lng)
            coords.append([lat, lng])
        
        return coords
    
    @staticmethod
    def calculate_grave_capacity(
        section_area: float,
        grave_length: float,
        grave_width: float,
        espacement: float
    ) -> int:
        """
        Calcule le nombre de caveaux possibles dans une section.
        """
        if section_area <= 0:
            return 0
        
        grave_area = (grave_length + espacement) * (grave_width + espacement)
        if grave_area <= 0:
            return 0
        
        return int(section_area / grave_area)
    
    @staticmethod
    def generate_section_name(order: int) -> str:
        """Génère un nom de section automatique (Section 1, Section 2, ...)."""
        return f"Section {order}"