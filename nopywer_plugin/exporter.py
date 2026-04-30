# -*- coding: utf-8 -*-
import json
import os
import tempfile
from qgis.core import (
    QgsProject, 
    QgsDistanceArea, 
    QgsUnitTypes, 
    QgsCoordinateReferenceSystem, 
    QgsCoordinateTransform
)


class NopywerExporter:
    def __init__(self, project=None):
        self.project = project or QgsProject.instance()
        self.da = QgsDistanceArea()
        self.da.setSourceCrs(self.project.crs(), self.project.transformContext())
        self.da.setEllipsoid(self.project.ellipsoid())
        
        # Target CRS for nopywer (WGS 84 degrees)
        self.target_crs_id = "EPSG:4326"
        self.target_crs = QgsCoordinateReferenceSystem(self.target_crs_id)

    def validate_layer(self, layer, required_fields):
        """Returns (is_valid, missing_fields)"""
        current_fields = [f.name() for f in layer.fields()]
        missing = [f for f in required_fields if f not in current_fields]
        return len(missing) == 0, missing

    def get_features_as_dict(self, layer, is_cable=False, power_units_scale=1.0):
        """
        Extracts features and formats them to match nopywer GeoJSON.
        """
        # Setup transformation for this layer
        transform = QgsCoordinateTransform(
            layer.crs(), self.target_crs, self.project.transformContext()
        )

        features = []
        for feature in layer.getFeatures():
            geom = feature.geometry()
            if not geom or geom.isEmpty():
                continue

            # Transform geometry to WGS 84 (Degrees)
            geom.transform(transform)

            # 1. Start with QGIS attributes
            # We convert attributeMap to a standard dict, ensuring types are JSON-serializable
            props = {}
            for field in layer.fields():
                fname = field.name().lower()
                val = feature.attribute(field.name())
                # Handle NULL values or QPyNullVariant
                if val is None or str(val) == "NULL":
                    props[fname] = None
                else:
                    props[fname] = val

            # 2. Add/Calculate mandatory nopywer properties
            if is_cable:
                # Normalize cable properties
                props["length"] = float(props.get("length") or 0)
                if props["length"] <= 0:
                    props["length"] = round(self.da.measureLength(geom), 2)

                # nopywer looks for 'area' and 'plugs&sockets' (already in props if fields matched)
            else:
                # Ensure 'power' is a float
                # TODO: throw warning or error if "power" or "name" doenst exist. Make a list of non-ok features.
                try:
                    orig_power = float(props.get("power") or 0)
                    props["power"] = orig_power * power_units_scale
                except:
                    props["power"] = 0.0

                # Ensure 'name' exists
                if not props.get("name"):
                    props["name"] = f"node_{feature.id()}"

                # Check for generator
                if "generator" in str(props["name"]).lower():
                    # Force lowercase "generator" in the name for nopywer's detection
                    if "generator" not in str(props["name"]):
                        props["name"] = str(props["name"]) + " generator"
                    print(f" [FOUND] Generator detected: '{props['name']}'")

            # 3. Create Feature dict
            geom_json = json.loads(geom.asJson())

            # Convert MultiPoint to Point if it contains exactly one point
            if not is_cable and geom_json.get("type") == "MultiPoint":
                coords = geom_json.get("coordinates", [])
                if len(coords) == 1:
                    geom_json["type"] = "Point"
                    geom_json["coordinates"] = coords[0]
                else:
                    raise ValueError(
                        f"Layer '{layer.name()}', Feature {feature.id()}: "
                        f"MultiPoint contains {len(coords)} points. "
                        "Only single-point features are supported."
                    )

            features.append(
                {
                    "type": "Feature",
                    "geometry": geom_json,
                    "properties": props,
                }
            )
        return features

    def export_to_temp_geojson(self, load_layers, cable_layers, power_units_scale=1.0):
        """
        Combines all layers into a single GeoJSON file.
        Returns the path to the temporary file.
        """
        all_features = []

        # Process Loads
        for layer in load_layers:
            valid, _ = self.validate_layer(layer, ["name", "power"])
            if valid:
                all_features.extend(self.get_features_as_dict(layer, is_cable=False, power_units_scale=power_units_scale))

        # Process Cables
        for layer in cable_layers:
            valid, _ = self.validate_layer(layer, ["area", "plugs&sockets"])
            if valid:
                all_features.extend(self.get_features_as_dict(layer, is_cable=True))

        if not all_features:
            return None

        # Create the FeatureCollection
        geojson_data = {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {"name": self.target_crs.authid()},
            },
            "power_unit": "W",
            "features": all_features,
        }

        # Save to temp file
        fd, input_path = tempfile.mkstemp(suffix=".geojson", prefix="nopywer_export_")
        with os.fdopen(fd, "w") as f:
            json.dump(geojson_data, f, indent=2)

        print(f"geoJSON file written: {input_path}")

        # Also write to home directory for easy access
        home_export = os.path.join(os.path.expanduser("~"), "nopywer_export.geojson")
        with open(home_export, "w") as f:
            json.dump(geojson_data, f, indent=2)
        print(f"Copy also saved to: {home_export}")

        # define an output file for nopywer outputs
        _, output_path = tempfile.mkstemp(suffix=".geojson", prefix="nopywer_output_")
        return input_path, output_path

    def run_preview(self, load_layers, cable_layers, power_units_scale=1.0):
        """Prints the validation and data preview to console."""
        print("\n" + "=" * 40)
        print(" NOPYWER EXPORTER PREVIEW")
        print("=" * 40)

        # Process Loads
        print(f"\n>>> LOAD LAYERS ({len(load_layers)}) <<<")
        for layer in load_layers:
            valid, missing = self.validate_layer(layer, ["name", "power"])
            if valid:
                print(f" [OK] Layer: {layer.name()}")
                self.print_layer_data(layer)
            else:
                print(f" [!] ERR: Layer '{layer.name()}' missing: {missing}")

        # Process Cables
        print(f"\n>>> CABLE LAYERS ({len(cable_layers)}) <<<")
        for layer in cable_layers:
            valid, missing = self.validate_layer(layer, ["area", "plugs&sockets"])
            if valid:
                print(f" [OK] Layer: {layer.name()}")
                self.print_layer_data(layer)
            else:
                print(f" [!] ERR: Layer '{layer.name()}' missing: {missing}")

        path_tuple = self.export_to_temp_geojson(load_layers, cable_layers, power_units_scale=power_units_scale)
        if path_tuple:
            input_path, output_path = path_tuple
            print("\n" + "-" * 40)
            print(f" Export saved to: {input_path}")
            print("-" * 40)
            return input_path, output_path
        return None

    def print_layer_data(self, layer):
        """Prints all fields and feature attributes for a given layer."""
        fields = layer.fields()
        field_names = [field.name() for field in fields]

        print(f"  Field Names: {field_names}")
        print(f"  Feature Count: {layer.featureCount()}")

        for i, feature in enumerate(layer.getFeatures()):
            print(f"    [Feature {i}] {feature.attributes()}")
            if i >= 19:
                print(f"    ... (Only showing first 20 features for {layer.name()})")
                break
