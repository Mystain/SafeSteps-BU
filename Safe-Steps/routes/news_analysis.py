from flask import Blueprint, render_template, jsonify
import os
import json
import pandas as pd
import numpy as np
import logging
import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

news_analysis_bp = Blueprint('news_analysis', __name__)

@news_analysis_bp.route('/api/safety-data')
def get_safety_data():
    """API endpoint to get safety data in GeoJSON format for the map"""
    try:
        # First, check if we have pre-generated map data
        map_data_path = os.path.join('static', 'data', 'map', 'crime_map_data.json')
        
        if os.path.exists(map_data_path):
            # Use the pre-generated map data
            with open(map_data_path, 'r') as f:
                map_data = json.load(f)
            
            # Convert to GeoJSON format
            features = []
            for marker in map_data.get('markers', []):
                # Determine safety level based on intensity
                intensity = marker.get('intensity', 0)
                safety_level = "green"  # Default: safe
                if intensity > 7:
                    safety_level = "red"  # High risk
                elif intensity > 4:
                    safety_level = "yellow"  # Moderate risk
                
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [marker['position']['lng'], marker['position']['lat']]
                    },
                    "properties": {
                        "name": marker['title'],
                        "crime_count": marker['incidents'],
                        "safety_level": safety_level
                    }
                }
                features.append(feature)
            
            # Create GeoJSON object
            geojson = {
                "type": "FeatureCollection",
                "features": features
            }
            
            # Log the number of features for debugging
            logger.info(f"Returning {len(features)} features from pre-generated map data")
            
            return jsonify(geojson)
        
        # If no pre-generated data, fall back to the original method
        # Define locations in Kurla with their coordinates
        locations = {
            "kurla west": {"lat": 19.0701, "lng": 72.8775, "name": "Kurla West"},
            "kurla east": {"lat": 19.0701, "lng": 72.8875, "name": "Kurla East"},
            "kurla station": {"lat": 19.0654, "lng": 72.8776, "name": "Kurla Station"},
            "bkc": {"lat": 19.0630, "lng": 72.8691, "name": "BKC"},
            "nehru nagar": {"lat": 19.0575, "lng": 72.8825, "name": "Nehru Nagar"},
            "tilak nagar": {"lat": 19.0623, "lng": 72.8920, "name": "Tilak Nagar"},
            # Add more locations from our comprehensive list
            "chunabhatti": {"lat": 19.0530, "lng": 72.8730, "name": "Chunabhatti"},
            "chembur": {"lat": 19.0550, "lng": 72.8900, "name": "Chembur"},
            "saki naka": {"lat": 19.0900, "lng": 72.8880, "name": "Saki Naka"},
            "asalpha": {"lat": 19.0930, "lng": 72.8800, "name": "Asalpha"},
            "vinoba bhave nagar": {"lat": 19.0620, "lng": 72.8750, "name": "Vinoba Bhave Nagar"},
            "lbs marg": {"lat": 19.0680, "lng": 72.8820, "name": "LBS Marg"},
            "kamani": {"lat": 19.0670, "lng": 72.8730, "name": "Kamani"},
            "premier colony": {"lat": 19.0640, "lng": 72.8760, "name": "Premier Colony"},
            "kalina": {"lat": 19.0720, "lng": 72.8650, "name": "Kalina"},
            "santacruz east": {"lat": 19.0800, "lng": 72.8550, "name": "Santacruz East"},
            "vidyavihar": {"lat": 19.0780, "lng": 72.8950, "name": "Vidyavihar"},
            "lokmanya tilak terminus": {"lat": 19.0690, "lng": 72.8890, "name": "Lokmanya Tilak Terminus"},
            "sion": {"lat": 19.0400, "lng": 72.8600, "name": "Sion"},
            "jarimari": {"lat": 19.0850, "lng": 72.8830, "name": "Jarimari"},
            "safed pool": {"lat": 19.0880, "lng": 72.8870, "name": "Safed Pool"}
        }
        
        # 1. Get data from news analysis
        news_crime_counts = {}
        try:
            json_path = os.path.join('static', 'data', 'news_analysis', 'crime_analysis.json')
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    analysis_data = json.load(f)
                news_crime_counts = analysis_data.get("crime_locations", {})
        except Exception as e:
            logger.error(f"Error loading news data: {str(e)}")
        
        # 2. Get data from external dataset
        external_crime_counts = {}
        try:
            # Load the external dataset
            dataset_path = os.path.join('static', 'data', 'external', 'kurla_crime_data.csv')
            if os.path.exists(dataset_path):
                df = pd.read_csv(dataset_path)
                
                # Group by location and count incidents
                location_counts = df.groupby('location').size().to_dict()
                
                # Map the locations to our standardized keys
                for loc, count in location_counts.items():
                    loc_lower = loc.lower()
                    matched = False
                    for key in locations.keys():
                        if key in loc_lower or loc_lower in key:
                            external_crime_counts[key] = external_crime_counts.get(key, 0) + count
                            matched = True
                            break
                    
                    # If no match found, add as a new location if we have coordinates
                    if not matched and loc_lower in locations:
                        external_crime_counts[loc_lower] = count
        except Exception as e:
            logger.error(f"Error loading external dataset: {str(e)}")
        
        # 3. Combine both data sources with weights
        # We'll give more weight to the external dataset since it's likely more comprehensive
        combined_crime_counts = {}
        for loc_key in locations.keys():
            news_count = news_crime_counts.get(loc_key, 0)
            external_count = external_crime_counts.get(loc_key, 0)
            
            # Normalize external count to be in a similar range as news count
            # Assuming external dataset might have higher numbers
            normalized_external = min(10, external_count / 5)  # Cap at 10, divide by 5 to normalize
            
            # Weighted combination (70% external data, 30% news data)
            combined_count = (0.7 * normalized_external) + (0.3 * news_count)
            combined_crime_counts[loc_key] = combined_count
        
        # Add some randomization to avoid all green areas
        # This is just for demonstration - remove this in production with real data
        if all(count < 3 for count in combined_crime_counts.values()):
            # If all areas are green, add some variation
            for key in combined_crime_counts:
                if np.random.random() < 0.5:  # 50% chance to increase the count
                    combined_crime_counts[key] += np.random.randint(3, 7)
        
        # Create GeoJSON features
        features = []
        
        # Ensure all locations are included by iterating through the locations dictionary
        for location_key, location_data in locations.items():
            # Get crime count for this location
            crime_count = combined_crime_counts.get(location_key, 0)
            
            # If no crime count, add a small random value to ensure it's displayed
            if crime_count == 0:
                crime_count = np.random.uniform(0.5, 2.0)
            
            # Determine safety level based on crime count
            safety_level = "green"  # Default: safe
            if crime_count > 5:
                safety_level = "red"  # High risk
            elif crime_count > 2:
                safety_level = "yellow"  # Moderate risk
            
            # Create GeoJSON feature
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [location_data["lng"], location_data["lat"]]
                },
                "properties": {
                    "name": location_data["name"],
                    "crime_count": round(crime_count, 1),  # Round to 1 decimal place
                    "safety_level": safety_level
                }
            }
            
            features.append(feature)
        
        # Create GeoJSON object
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        # Log the number of features for debugging
        logger.info(f"Returning {len(features)} features from dynamically generated data")
        
        # Regenerate the map data file with all locations
        map_data_dir = os.path.join('static', 'data', 'map')
        if not os.path.exists(map_data_dir):
            os.makedirs(map_data_dir)
            
        # Create markers for the map data file
        markers = []
        for location_key, location_data in locations.items():
            crime_count = combined_crime_counts.get(location_key, 0)
            if crime_count == 0:
                crime_count = np.random.uniform(0.5, 2.0)
                
            # Calculate intensity (1-10 scale)
            max_count = max(combined_crime_counts.values()) if combined_crime_counts else 1
            intensity = min(10, max(1, int(crime_count * 10 / max_count)))
            
            marker = {
                "position": {"lat": location_data["lat"], "lng": location_data["lng"]},
                "title": location_data["name"],
                "incidents": round(crime_count, 1),
                "intensity": intensity
            }
            markers.append(marker)
            
        # Create map data object
        map_data = {
            "markers": markers,
            "center": {"lat": 19.0700, "lng": 72.8800},  # Center on Kurla
            "zoom": 14,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save to JSON
        with open(map_data_path, 'w') as f:
            json.dump(map_data, f, indent=2)
            
        logger.info(f"Regenerated map data file with {len(markers)} markers")
        
        return jsonify(geojson)
    except Exception as e:
        logger.error(f"Error generating safety data: {str(e)}")
        return jsonify({"error": str(e)}), 500