# -*- coding: utf-8 -*-
import json
import os
import tempfile
from qgis.core import QgsProject, QgsDistanceArea, QgsUnitTypes


class NopywerExporter:
    def __init__(self, project=None):
        self.project = project or QgsProject.instance()
        self.da = QgsDistanceArea()
        self.da.setSourceCrs(self.project.crs(), self.project.transformContext())
        self.da.setEllipsoid(self.project.ellipsoid())

    def validate_layer(self, layer, required_fields):
        """Returns (is_valid, missing_fields)"""
        current_fields = [f.name() for f in layer.fields()]
        missing = [f for f in required_fields if f not in current_fields]
        return len(missing) == 0, missing

    def get_features_as_dict(self, layer, is_cable=False):
        """
        Extracts features and formats them to match nopywer GeoJSON.
        """
        features = []
        for feature in layer.getFeatures():
            geom = feature.geometry()
            if not geom or geom.isEmpty():
                continue

            # 1. Start with QGIS attributes
            # We convert attributeMap to a standard dict, ensuring types are JSON-serializable
            props = {}
            for field in layer.fields():
                val = feature.attribute(field.name())
                # Handle NULL values or QPyNullVariant
                if val is None or str(val) == "NULL":
                    props[field.name()] = None
                else:
                    props[field.name()] = val

            # 2. Add/Calculate mandatory nopywer properties
            if is_cable:
                # Calculate ellipsoidal length in meters
                props["length"] = round(self.da.measureLength(geom), 2)
            else:
                # Ensure power is a float if it exists
                if "power" in props and props["power"] is not None:
                    try:
                        props["power"] = float(props["power"])
                    except ValueError:
                        pass

            # 3. Create Feature dict
            features.append(
                {
                    "type": "Feature",
                    "geometry": json.loads(geom.asJson()),
                    "properties": props,
                }
            )
        return features

    def export_to_temp_geojson(self, load_layers, cable_layers):
        """
        Combines all layers into a single GeoJSON file.
        Returns the path to the temporary file.
        """
        all_features = []

        # Process Loads
        for layer in load_layers:
            valid, _ = self.validate_layer(layer, ["name", "power"])
            if valid:
                all_features.extend(self.get_features_as_dict(layer, is_cable=False))

        # Process Cables
        for layer in cable_layers:
            valid, _ = self.validate_layer(layer, ["area", "plugs&sockets"])
            if valid:
                all_features.extend(self.get_features_as_dict(layer, is_cable=True))

        if not all_features:
            return None

        # Create the FeatureCollection
        geojson_data = {"type": "FeatureCollection", "features": all_features}

        # Save to temp file
        fd, path = tempfile.mkstemp(suffix=".geojson", prefix="nopywer_export_")
        with os.fdopen(fd, "w") as f:
            json.dump(geojson_data, f, indent=2)

        return path

    def run_preview(self, load_layers, cable_layers):
        """Old preview method updated to show temp file path."""
        path = self.export_to_temp_geojson(load_layers, cable_layers)
        if path:
            print("\n" + "=" * 40)
            print(" NOPYWER EXPORT SUCCESSFUL")
            print(f" File saved to: {path}")
            print("=" * 40)
            # # For debugging, print the first few lines of the file
            # with open(path, 'r') as f:
            #     print(f.read(500) + "...")
        else:
            print("\n [!] Export failed: No valid features or layers selected.")
        return path
