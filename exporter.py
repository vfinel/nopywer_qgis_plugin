# -*- coding: utf-8 -*-
import json
import os
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

    def get_feature_data(self, layer, is_cable=False):
        """
        Extracts features and calculates geometry properties.
        """
        data = []
        for feature in layer.getFeatures():
            geom = feature.geometry()
            if not geom:
                continue

            # Basic attributes
            props = feature.attributeMap()
            
            # Calculations
            if is_cable:
                # Calculate length in meters
                length_m = self.da.measureLength(geom)
                props['_calculated_length_m'] = length_m
            else:
                # Calculate position (centroid for points/polygons)
                point = geom.centroid().asPoint()
                props['_calculated_x'] = point.x()
                props['_calculated_y'] = point.y()

            data.append({
                "id": feature.id(),
                "properties": props,
                "geometry": json.loads(geom.asJson()) 
            })
        return data

    def run_preview(self, load_layers, cable_layers):
        """Prints the validation and data preview to console."""
        print("\n" + "="*40)
        print(" NOPYWER EXPORTER PREVIEW")
        print("="*40)

        results = {
            "loads": [],
            "cables": []
        }

        # Process Loads
        for layer in load_layers:
            valid, missing = self.validate_layer(layer, ["name", "power"])
            if valid:
                features = self.get_feature_data(layer, is_cable=False)
                print(f"[OK] Load Layer: {layer.name()} ({len(features)} features)")
                results["loads"].extend(features)
            else:
                print(f"[!] ERR: Load Layer '{layer.name()}' missing: {missing}")

        # Process Cables
        for layer in cable_layers:
            valid, missing = self.validate_layer(layer, ["area", "plugs&sockets"])
            if valid:
                features = self.get_feature_data(layer, is_cable=True)
                print(f"[OK] Cable Layer: {layer.name()} ({len(features)} features)")
                results["cables"].extend(features)
            else:
                print(f"[!] ERR: Cable Layer '{layer.name()}' missing: {missing}")

        return results
