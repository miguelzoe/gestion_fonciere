from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import geopandas as gpd
import json
import os
import random
from pathlib import Path

app = Flask(__name__)
CORS(app)

# Configuration du dossier contenant les fichiers shapefile
SHAPEFILE_DIR = "./shapefiles"  # Ajustez selon votre structure
SHAPEFILE_NAME = "FINBiyemassi"  # Nom de base de vos fichiers

def get_shapefile_path():
    """Retourne le chemin complet du fichier .shp"""
    return os.path.join(SHAPEFILE_DIR, f"{SHAPEFILE_NAME}.shp")

@app.route('/')
def index():
    """Documentation de l'API"""
    return jsonify({
        "api": "ArcGIS Shapefile API",
        "version": "1.0",
        "endpoints": {
            "/api/info": "Informations sur le shapefile",
            "/api/geojson": "Récupérer toutes les données en GeoJSON",
            "/api/features": "Liste des entités avec pagination",
            "/api/features/sample": "Récupérer un échantillon de 3 parcelles",
            "/api/features/<id>": "Récupérer une entité spécifique",
            "/api/bounds": "Limites géographiques du shapefile",
            "/api/attributes": "Liste des attributs disponibles",
            "/api/search": "Rechercher des entités (query params)",
            "/api/export/geojson": "Exporter en GeoJSON",
            "/api/map": "Visualiser la carte interactive",
            "/api/largest": "Récupérer les 3 plus grandes parcelles",
            "/api/parcelles/with-status": "Parcelles avec statuts fiscaux pour l'admin"
        }
    })

@app.route('/api/info')
def get_info():
    """Informations générales sur le shapefile"""
    try:
        gdf = gpd.read_file(get_shapefile_path())
        
        return jsonify({
            "success": True,
            "data": {
                "name": SHAPEFILE_NAME,
                "total_features": len(gdf),
                "crs": str(gdf.crs),
                "geometry_type": gdf.geometry.type.unique().tolist(),
                "columns": gdf.columns.tolist(),
                "bounds": {
                    "minx": float(gdf.total_bounds[0]),
                    "miny": float(gdf.total_bounds[1]),
                    "maxx": float(gdf.total_bounds[2]),
                    "maxy": float(gdf.total_bounds[3])
                }
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/geojson')
def get_geojson():
    """Récupérer toutes les données en format GeoJSON"""
    try:
        gdf = gpd.read_file(get_shapefile_path())
        
        # Convertir en WGS84 (EPSG:4326) pour la compatibilité web
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
        
        # Convertir en GeoJSON
        geojson = json.loads(gdf.to_json())
        
        return jsonify({
            "success": True,
            "type": "FeatureCollection",
            "features": geojson['features'],
            "total_features": len(geojson['features'])
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/features')
def get_features():
    """Liste des entités avec pagination"""
    try:
        # Paramètres de pagination
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        gdf = gpd.read_file(get_shapefile_path())
        
        # Convertir en WGS84
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
        
        # Calculer les indices de pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        # Extraire la page demandée
        gdf_page = gdf.iloc[start_idx:end_idx]
        
        # Convertir en GeoJSON
        geojson = json.loads(gdf_page.to_json())
        
        return jsonify({
            "success": True,
            "page": page,
            "per_page": per_page,
            "total_features": len(gdf),
            "total_pages": (len(gdf) + per_page - 1) // per_page,
            "features": geojson['features']
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/features/sample')
def get_sample_features():
    """Récupérer un échantillon de 3 parcelles"""
    try:
        gdf = gpd.read_file(get_shapefile_path())
        
        # Convertir en WGS84
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
        
        # Limiter à 3 parcelles maximum
        sample_size = min(3, len(gdf))
        gdf_sample = gdf.head(sample_size)
        
        # Convertir en GeoJSON
        geojson = json.loads(gdf_sample.to_json())
        
        return jsonify({
            "success": True,
            "total_features": len(gdf),
            "sample_size": sample_size,
            "features": geojson['features']
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/features/<int:feature_id>')
def get_feature(feature_id):
    """Récupérer une entité spécifique par ID"""
    try:
        gdf = gpd.read_file(get_shapefile_path())
        
        if feature_id < 0 or feature_id >= len(gdf):
            return jsonify({"success": False, "error": "Feature not found"}), 404
        
        # Convertir en WGS84
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
        
        # Extraire l'entité
        feature = gdf.iloc[feature_id:feature_id+1]
        geojson = json.loads(feature.to_json())
        
        return jsonify({
            "success": True,
            "feature": geojson['features'][0]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/bounds')
def get_bounds():
    """Récupérer les limites géographiques"""
    try:
        gdf = gpd.read_file(get_shapefile_path())
        
        # Convertir en WGS84
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
        
        bounds = gdf.total_bounds
        
        return jsonify({
            "success": True,
            "bounds": {
                "southwest": [float(bounds[1]), float(bounds[0])],  # [lat, lng]
                "northeast": [float(bounds[3]), float(bounds[2])],
                "center": [
                    float((bounds[1] + bounds[3]) / 2),
                    float((bounds[0] + bounds[2]) / 2)
                ]
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/attributes')
def get_attributes():
    """Liste des attributs disponibles"""
    try:
        gdf = gpd.read_file(get_shapefile_path())
        
        attributes = {}
        for col in gdf.columns:
            if col != 'geometry':
                # Gérer les valeurs NaN pour la sérialisation JSON
                sample_values = gdf[col].head(3).fillna('N/A').tolist()
                attributes[col] = {
                    "type": str(gdf[col].dtype),
                    "sample_values": sample_values
                }
        
        return jsonify({
            "success": True,
            "attributes": attributes
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/search')
def search_features():
    """Rechercher des entités"""
    try:
        gdf = gpd.read_file(get_shapefile_path())
        
        # Convertir en WGS84
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
        
        # Récupérer les paramètres de recherche
        query_params = request.args.to_dict()
        
        # Filtrer selon les paramètres
        filtered_gdf = gdf
        for key, value in query_params.items():
            if key in gdf.columns:
                # Gérer les valeurs NaN pour la recherche
                filtered_gdf = filtered_gdf[filtered_gdf[key].astype(str).str.contains(value, case=False, na=False)]
        
        # Convertir en GeoJSON
        geojson = json.loads(filtered_gdf.to_json())
        
        return jsonify({
            "success": True,
            "total_results": len(filtered_gdf),
            "features": geojson['features']
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/largest')
def get_largest_parcels():
    """Récupérer les 3 plus grandes parcelles par superficie"""
    try:
        gdf = gpd.read_file(get_shapefile_path())
        
        # Convertir en WGS84
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
        
        # Calculer la superficie de chaque parcelle en mètres carrés
        # Créer une copie pour éviter les avertissements
        gdf_working = gdf.copy()
        gdf_working['area_m2'] = gdf_working.geometry.area
        
        # Trier par superficie décroissante et prendre les 3 premières
        largest_parcels = gdf_working.nlargest(3, 'area_m2')
        
        # Convertir en GeoJSON
        geojson = json.loads(largest_parcels.to_json())
        
        # Préparer les données de réponse avec les superficies
        features_with_area = []
        for i, feature in enumerate(geojson['features']):
            area_m2 = largest_parcels.iloc[i]['area_m2']
            area_ha = area_m2 / 10000  # Conversion en hectares
            
            # Ajouter l'information de superficie aux propriétés
            feature['properties']['area_m2'] = round(area_m2, 2)
            feature['properties']['area_ha'] = round(area_ha, 2)
            feature['properties']['rank'] = i + 1
            
            features_with_area.append(feature)
        
        return jsonify({
            "success": True,
            "total_features": len(gdf),
            "largest_parcels": features_with_area,
            "area_summary": {
                "max_area_m2": round(largest_parcels['area_m2'].max(), 2),
                "max_area_ha": round(largest_parcels['area_m2'].max() / 10000, 2),
                "min_area_m2": round(largest_parcels['area_m2'].min(), 2),
                "min_area_ha": round(largest_parcels['area_m2'].min() / 10000, 2),
                "average_area_m2": round(largest_parcels['area_m2'].mean(), 2),
                "average_area_ha": round(largest_parcels['area_m2'].mean() / 10000, 2)
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/parcelles/with-status')
def get_parcelles_with_status():
    """Récupérer les parcelles avec statuts fiscaux simulés pour l'administration"""
    try:
        gdf = gpd.read_file(get_shapefile_path())
        
        # Convertir en WGS84
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
        
        # Ajouter des données fiscales simulées pour la démo
        parcelles_with_status = []
        
        for idx, row in gdf.iterrows():
            # Utiliser des attributs existants pour générer des données cohérentes
            parcelle_id = idx
            
            # Récupérer les attributs existants avec des valeurs par défaut
            numero_parcelle = row.get('NUMERO', f'PARC_{idx:04d}') if 'NUMERO' in row else f'PARC_{idx:04d}'
            proprietaire = row.get('NOM', f'Propriétaire {idx}') if 'NOM' in row else f'Propriétaire {idx}'
            adresse = row.get('ADRESSE', 'Biyem-Assi, Yaoundé') if 'ADRESSE' in row else 'Biyem-Assi, Yaoundé'
            
            # Calculer la superficie à partir de la géométrie (en m²)
            superficie = round(row.geometry.area, 2)
            
            # Générer des données fiscales réalistes basées sur la superficie
            # Impôt annuel proportionnel à la superficie (entre 100 et 1000 FCFA/m²)
            prix_m2 = random.uniform(100, 1000)
            impot_annuel = round(superficie * prix_m2 / 1000) * 1000  # Arrondi à 1000 FCFA près
            
            # Déterminer le statut fiscal basé sur des probabilités réalistes
            rand_val = random.random()
            if rand_val < 0.4:  # 40% à jour
                statut = "a_jour"
                montant_du = 0
            elif rand_val < 0.75:  # 35% en retard
                statut = "en_retard"
                # Doit entre 1 et 6 mois d'impôt
                mois_retard = random.randint(1, 6)
                montant_du = round((impot_annuel / 12) * mois_retard)
            else:  # 25% impayé
                statut = "impaye"
                # Doit plus d'un an d'impôt
                annees_impayees = random.randint(1, 3)
                montant_du = impot_annuel * annees_impayees
            
            # Calculer le centre de la parcelle pour la carte
            centroid = row.geometry.centroid
            latitude = round(centroid.y, 6)
            longitude = round(centroid.x, 6)
            
            parcelle_data = {
                "id": str(parcelle_id),
                "numero": str(numero_parcelle),
                "proprietaireNom": str(proprietaire),
                "adresse": str(adresse),
                "superficie": superficie,
                "impotAnnuel": int(impot_annuel),
                "montantDu": int(montant_du),
                "statut": statut,
                "latitude": latitude,
                "longitude": longitude,
                "geometry": json.loads(gpd.GeoSeries([row.geometry]).to_json())['features'][0]['geometry']
            }
            
            parcelles_with_status.append(parcelle_data)
        
        # Calculer les statistiques globales
        total_parcelles = len(parcelles_with_status)
        parcelles_a_jour = len([p for p in parcelles_with_status if p['statut'] == 'a_jour'])
        parcelles_en_retard = len([p for p in parcelles_with_status if p['statut'] == 'en_retard'])
        parcelles_impayees = len([p for p in parcelles_with_status if p['statut'] == 'impaye'])
        total_revenu = sum(p['impotAnnuel'] for p in parcelles_with_status)
        total_du = sum(p['montantDu'] for p in parcelles_with_status)
        
        return jsonify({
            "success": True,
            "total": total_parcelles,
            "stats": {
                "parcellesAJour": parcelles_a_jour,
                "parcellesEnRetard": parcelles_en_retard,
                "parcellesImpayees": parcelles_impayees,
                "totalRevenu": total_revenu,
                "totalDu": total_du,
                "tauxConformite": round((parcelles_a_jour / total_parcelles) * 100, 1) if total_parcelles > 0 else 0
            },
            "parcelles": parcelles_with_status
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/export/geojson')
def export_geojson():
    """Exporter les données en fichier GeoJSON"""
    try:
        gdf = gpd.read_file(get_shapefile_path())
        
        # Convertir en WGS84
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
        
        # Créer un fichier temporaire
        output_path = f"/tmp/{SHAPEFILE_NAME}.geojson"
        gdf.to_file(output_path, driver='GeoJSON')
        
        return send_file(
            output_path,
            mimetype='application/json',
            as_attachment=True,
            download_name=f"{SHAPEFILE_NAME}.geojson"
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/map')
def show_map():
    """Visualiser la carte interactive"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Carte ArcGIS - Biyem-Assi</title>
        <meta charset="utf-8" />
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            body { margin: 0; padding: 0; }
            #map { width: 100%; height: 100vh; }
            .info { padding: 10px; background: white; border-radius: 5px; }
            .legend { 
                position: absolute; 
                bottom: 20px; 
                right: 20px; 
                background: white; 
                padding: 10px; 
                border-radius: 5px;
                box-shadow: 0 0 10px rgba(0,0,0,0.2);
            }
        </style>
    </head>
    <body>
        <div id="map"></div>
        <div class="legend">
            <h4>Légende - Biyem-Assi</h4>
            <div><span style="color: #3388ff">■</span> Toutes les parcelles</div>
            <div><span style="color: #ff0000">■</span> 3 plus grandes parcelles</div>
        </div>
        <script>
            var map = L.map('map').setView([3.8480, 11.5021], 13);
            
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);
            
            // Charger toutes les parcelles
            fetch('/api/geojson')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        var allParcels = L.geoJSON(data.features, {
                            onEachFeature: function(feature, layer) {
                                var popup = '<div class="info"><h3>Parcelle ' + (feature.properties.NUMERO || feature.properties.numero || 'N/A') + '</h3>';
                                for (var key in feature.properties) {
                                    if (key !== 'geometry') {
                                        popup += '<b>' + key + ':</b> ' + feature.properties[key] + '<br>';
                                    }
                                }
                                popup += '</div>';
                                layer.bindPopup(popup);
                            },
                            style: {
                                color: '#3388ff',
                                weight: 1,
                                fillOpacity: 0.2
                            }
                        }).addTo(map);
                        
                        // Charger les 3 plus grandes parcelles
                        fetch('/api/largest')
                            .then(response => response.json())
                            .then(largestData => {
                                if (largestData.success) {
                                    var largestParcels = L.geoJSON(largestData.largest_parcels, {
                                        onEachFeature: function(feature, layer) {
                                            var popup = '<div class="info"><h3>Parcelle ' + feature.properties.rank + ' plus grande</h3>';
                                            popup += '<b>Superficie:</b> ' + feature.properties.area_ha + ' ha (' + feature.properties.area_m2 + ' m²)<br>';
                                            for (var key in feature.properties) {
                                                if (key !== 'area_m2' && key !== 'area_ha' && key !== 'rank' && key !== 'geometry') {
                                                    popup += '<b>' + key + ':</b> ' + feature.properties[key] + '<br>';
                                                }
                                            }
                                            popup += '</div>';
                                            layer.bindPopup(popup);
                                        },
                                        style: {
                                            color: '#ff0000',
                                            weight: 3,
                                            fillColor: '#ff0000',
                                            fillOpacity: 0.4
                                        }
                                    }).addTo(map);
                                    
                                    // Ajuster la vue pour montrer toutes les parcelles
                                    var allBounds = allParcels.getBounds();
                                    map.fitBounds(allBounds);
                                }
                            })
                            .catch(error => console.error('Erreur:', error));
                    }
                })
                .catch(error => console.error('Erreur:', error));
        </script>
    </body>
    </html>
    """
    return html

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)