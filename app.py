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
SHAPEFILE_DIR = "./shapefiles"
SHAPEFILE_NAME = "FINBiyemassi"

def get_shapefile_path():
    """Retourne le chemin complet du fichier .shp"""
    return os.path.join(SHAPEFILE_DIR, f"{SHAPEFILE_NAME}.shp")

def load_geodataframe():
    """Charge le shapefile de manière sécurisée"""
    try:
        gdf = gpd.read_file(get_shapefile_path())
        
        # Filtrer les géométries NULL si elles existent
        if gdf.geometry.isna().any():
            gdf = gdf[gdf.geometry.notna()].copy()
        
        return gdf
    except Exception as e:
        raise Exception(f"Erreur lors du chargement du shapefile: {str(e)}")

def convert_to_wgs84(gdf):
    """Convertir en WGS84 (EPSG:4326) de manière sécurisée"""
    try:
        # Créer une copie pour éviter les modifications
        gdf_copy = gdf.copy()
        
        # Convertir vers WGS84 (le CRS est déjà défini dans votre shapefile)
        if gdf_copy.crs and gdf_copy.crs.to_epsg() != 4326:
            gdf_copy = gdf_copy.to_crs(epsg=4326)
        
        return gdf_copy
    except Exception as e:
        raise Exception(f"Erreur lors de la conversion en WGS84: {str(e)}")

@app.route('/')
def index():
    """Documentation de l'API"""
    return jsonify({
        "api": "ArcGIS Shapefile API - Biyem-Assi",
        "version": "1.0",
        "shapefile": SHAPEFILE_NAME,
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
        gdf = load_geodataframe()
        
        return jsonify({
            "success": True,
            "data": {
                "name": SHAPEFILE_NAME,
                "total_features": len(gdf),
                "crs": str(gdf.crs),
                "crs_epsg": gdf.crs.to_epsg() if gdf.crs else None,
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
        return jsonify({
            "success": False, 
            "error": str(e)
        }), 500

@app.route('/api/geojson')
def get_geojson():
    """Récupérer toutes les données en format GeoJSON"""
    try:
        gdf = load_geodataframe()
        gdf = convert_to_wgs84(gdf)
        
        # Convertir en GeoJSON
        geojson = json.loads(gdf.to_json())
        
        return jsonify({
            "success": True,
            "type": "FeatureCollection",
            "features": geojson['features'],
            "total_features": len(geojson['features'])
        })
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": str(e)
        }), 500

@app.route('/api/features')
def get_features():
    """Liste des entités avec pagination"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        gdf = load_geodataframe()
        gdf = convert_to_wgs84(gdf)
        
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
        gdf = load_geodataframe()
        gdf = convert_to_wgs84(gdf)
        
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
        gdf = load_geodataframe()
        
        if feature_id < 0 or feature_id >= len(gdf):
            return jsonify({"success": False, "error": "Feature not found"}), 404
        
        gdf = convert_to_wgs84(gdf)
        
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
        gdf = load_geodataframe()
        gdf = convert_to_wgs84(gdf)
        
        bounds = gdf.total_bounds
        
        return jsonify({
            "success": True,
            "bounds": {
                "southwest": [float(bounds[1]), float(bounds[0])],
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
        gdf = load_geodataframe()
        
        attributes = {}
        for col in gdf.columns:
            if col != 'geometry':
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
        gdf = load_geodataframe()
        gdf = convert_to_wgs84(gdf)
        
        # Récupérer les paramètres de recherche
        query_params = request.args.to_dict()
        
        # Filtrer selon les paramètres
        filtered_gdf = gdf
        for key, value in query_params.items():
            if key in gdf.columns:
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
        gdf = load_geodataframe()
        
        # Calculer la superficie dans le CRS d'origine (UTM) pour avoir des mètres carrés
        gdf_calc = gdf.copy()
        gdf_calc['area_m2'] = gdf_calc.geometry.area
        
        # Trier et prendre les 3 plus grandes
        largest_indices = gdf_calc.nlargest(3, 'area_m2').index
        
        # Convertir en WGS84 pour l'affichage
        gdf_display = convert_to_wgs84(gdf.loc[largest_indices].copy())
        gdf_display['area_m2'] = gdf_calc.loc[largest_indices, 'area_m2'].values
        
        # Convertir en GeoJSON
        geojson = json.loads(gdf_display.to_json())
        
        # Préparer les données de réponse
        features_with_area = []
        for i, feature in enumerate(geojson['features']):
            area_m2 = gdf_display.iloc[i]['area_m2']
            area_ha = area_m2 / 10000
            
            feature['properties']['area_m2'] = round(float(area_m2), 2)
            feature['properties']['area_ha'] = round(float(area_ha), 4)
            feature['properties']['rank'] = i + 1
            
            features_with_area.append(feature)
        
        return jsonify({
            "success": True,
            "total_features": len(gdf),
            "largest_parcels": features_with_area,
            "area_summary": {
                "max_area_m2": round(float(gdf_display['area_m2'].max()), 2),
                "max_area_ha": round(float(gdf_display['area_m2'].max() / 10000), 4),
                "min_area_m2": round(float(gdf_display['area_m2'].min()), 2),
                "min_area_ha": round(float(gdf_display['area_m2'].min() / 10000), 4),
                "average_area_m2": round(float(gdf_display['area_m2'].mean()), 2),
                "average_area_ha": round(float(gdf_display['area_m2'].mean() / 10000), 4)
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/parcelles/with-status')
def get_parcelles_with_status():
    """Récupérer les parcelles avec statuts fiscaux simulés"""
    try:
        gdf = load_geodataframe()
        
        # Calculer les superficies dans le CRS d'origine (UTM)
        superficies = gdf.geometry.area
        
        # Convertir en WGS84 pour les coordonnées
        gdf_wgs84 = convert_to_wgs84(gdf)
        
        parcelles_with_status = []
        
        for idx in range(len(gdf)):
            row = gdf_wgs84.iloc[idx]
            
            # Utiliser les vraies données du shapefile
            parcelle_id = idx
            numero_parcelle = str(row.get('Numero_de', f'PARC_{idx:04d}'))
            proprietaire = str(row.get('Noms_Raiso', f'Propriétaire {idx}'))
            quartier = str(row.get('Quartier', 'Biyem-Assi'))
            lieu_dit = str(row.get('Lieu_dit', ''))
            commune = str(row.get('Commune', 'Yaoundé'))
            
            adresse = f"{quartier}, {commune}"
            if lieu_dit and lieu_dit != 'nan':
                adresse = f"{lieu_dit}, {adresse}"
            
            superficie = round(float(superficies.iloc[idx]), 2)
            
            # Utiliser les montants du shapefile si disponibles
            montant_annuel_shp = row.get('Montant_an', 0)
            if montant_annuel_shp and montant_annuel_shp > 0:
                impot_annuel = int(montant_annuel_shp)
            else:
                prix_m2 = random.uniform(100, 1000)
                impot_annuel = round(superficie * prix_m2 / 1000) * 1000
            
            # Simuler les statuts de paiement
            rand_val = random.random()
            if rand_val < 0.4:
                statut = "a_jour"
                montant_du = 0
            elif rand_val < 0.75:
                statut = "en_retard"
                mois_retard = random.randint(1, 6)
                montant_du = round((impot_annuel / 12) * mois_retard)
            else:
                statut = "impaye"
                annees_impayees = random.randint(1, 3)
                montant_du = impot_annuel * annees_impayees
            
            centroid = row.geometry.centroid
            latitude = round(float(centroid.y), 6)
            longitude = round(float(centroid.x), 6)
            
            parcelle_data = {
                "id": str(parcelle_id),
                "numero": numero_parcelle,
                "proprietaireNom": proprietaire,
                "adresse": adresse,
                "quartier": quartier,
                "superficie": superficie,
                "impotAnnuel": int(impot_annuel),
                "montantDu": int(montant_du),
                "statut": statut,
                "latitude": latitude,
                "longitude": longitude,
                "geometry": json.loads(gpd.GeoSeries([row.geometry]).to_json())['features'][0]['geometry']
            }
            
            parcelles_with_status.append(parcelle_data)
        
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
        gdf = load_geodataframe()
        gdf = convert_to_wgs84(gdf)
        
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
        <title>Carte Parcellaire - Biyem-Assi</title>
        <meta charset="utf-8" />
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            body { margin: 0; padding: 0; font-family: Arial, sans-serif; }
            #map { width: 100%; height: 100vh; }
            .info { padding: 10px; background: white; border-radius: 5px; max-width: 300px; }
            .info h3 { margin: 0 0 10px 0; color: #2c3e50; }
            .legend { 
                position: absolute; 
                bottom: 20px; 
                right: 20px; 
                background: white; 
                padding: 15px; 
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            }
            .legend h4 { margin: 0 0 10px 0; color: #2c3e50; }
            .legend-item { margin: 5px 0; }
        </style>
    </head>
    <body>
        <div id="map"></div>
        <div class="legend">
            <h4>🗺️ Biyem-Assi</h4>
            <div class="legend-item"><span style="color: #3388ff">■</span> Parcelles cadastrales</div>
            <div class="legend-item"><span style="color: #ff0000">■</span> 3 plus grandes parcelles</div>
            <div style="margin-top: 10px; font-size: 12px; color: #666;">
                Total: 208 parcelles
            </div>
        </div>
        <script>
            var map = L.map('map').setView([3.8480, 11.5021], 14);
            
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors',
                maxZoom: 19
            }).addTo(map);
            
            fetch('/api/geojson')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        var allParcels = L.geoJSON(data.features, {
                            onEachFeature: function(feature, layer) {
                                var props = feature.properties;
                                var popup = '<div class="info">';
                                popup += '<h3>📋 Parcelle</h3>';
                                popup += '<b>Numéro:</b> ' + (props.Numero_de || 'N/A') + '<br>';
                                popup += '<b>Propriétaire:</b> ' + (props.Noms_Raiso || 'N/A') + '<br>';
                                popup += '<b>Quartier:</b> ' + (props.Quartier || 'N/A') + '<br>';
                                popup += '<b>Superficie:</b> ' + (props.AREA || 'N/A') + ' m²<br>';
                                popup += '</div>';
                                layer.bindPopup(popup);
                            },
                            style: {
                                color: '#3388ff',
                                weight: 1,
                                fillOpacity: 0.2
                            }
                        }).addTo(map);
                        
                        fetch('/api/largest')
                            .then(response => response.json())
                            .then(largestData => {
                                if (largestData.success) {
                                    L.geoJSON(largestData.largest_parcels, {
                                        onEachFeature: function(feature, layer) {
                                            var props = feature.properties;
                                            var popup = '<div class="info">';
                                            popup += '<h3>🏆 Parcelle #' + props.rank + '</h3>';
                                            popup += '<b>Superficie:</b> ' + props.area_ha + ' ha<br>';
                                            popup += '<b>(' + props.area_m2 + ' m²)</b><br>';
                                            popup += '<b>Propriétaire:</b> ' + (props.Noms_Raiso || 'N/A') + '<br>';
                                            popup += '</div>';
                                            layer.bindPopup(popup);
                                        },
                                        style: {
                                            color: '#ff0000',
                                            weight: 3,
                                            fillColor: '#ff0000',
                                            fillOpacity: 0.3
                                        }
                                    }).addTo(map);
                                }
                            });
                        
                        map.fitBounds(allParcels.getBounds());
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