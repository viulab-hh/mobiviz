#!/usr/bin/env python3
"""
Apply shortening and rounding rules to filtered GeoJSON files.

The script:
- shortens property names according to `shortening_rules.json`
- rounds numeric property values to the configured number of decimal places
- rounds geometry coordinate values to the configured number of decimal places

Input is expected to be a `filtered` directory created by `filter_geojson_props.py`.
Output is written to a sibling directory named `filtered_shortened`.
"""

import glob
import json
import os
import sys
from pathlib import Path


DEFAULT_RULES_FILE = Path(__file__).with_name("shortening_rules.json")
DEFAULT_OUTPUT_DIRNAME = "filtered_shortened"


def load_rules(rules_path):
    """Load shortening and rounding rules from JSON."""
    with open(rules_path, "r", encoding="utf-8") as handle:
        rules = json.load(handle)

    property_renaming = rules.get("property_renaming", {})
    rounding = rules.get("rounding", {})
    property_value_decimals = rounding.get("property_values", rounding.get("properties"))
    coordinate_value_decimals = rounding.get("coordinate_values", rounding.get("coordinates"))

    return property_renaming, property_value_decimals, coordinate_value_decimals


def round_numeric_value(value, decimals):
    """Round a numeric value if rounding is configured."""
    if decimals is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    return round(value, decimals)


def round_property_value(value, decimals):
    """Round numeric values in nested property structures."""
    if isinstance(value, dict):
        return {key: round_property_value(nested_value, decimals) for key, nested_value in value.items()}
    if isinstance(value, list):
        return [round_property_value(item, decimals) for item in value]
    return round_numeric_value(value, decimals)


def round_coordinates(coordinates, decimals):
    """Round numeric values in nested GeoJSON coordinate arrays."""
    if isinstance(coordinates, list):
        return [round_coordinates(item, decimals) for item in coordinates]
    return round_numeric_value(coordinates, decimals)


def transform_feature(feature, property_renaming, property_value_decimals, coordinate_value_decimals):
    """Apply property renaming and rounding to a feature."""
    properties = feature.get("properties")
    if isinstance(properties, dict):
        renamed_properties = {}
        for key, value in properties.items():
            new_key = property_renaming.get(key, key)
            renamed_properties[new_key] = round_property_value(value, property_value_decimals)
        feature["properties"] = renamed_properties

    geometry = feature.get("geometry")
    if isinstance(geometry, dict) and "coordinates" in geometry:
        geometry["coordinates"] = round_coordinates(geometry["coordinates"], coordinate_value_decimals)

    return feature


def write_feature_collection(output_path, data):
    """Write GeoJSON with compact formatting and one feature per line."""
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write("{\n")

        root_items = []
        for key, value in data.items():
            if key == "features":
                continue
            root_items.append((key, value))

        for key, value in root_items:
            json_value = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
            handle.write(f'  "{key}": {json_value},\n')

        handle.write('  "features": [\n')
        features = data.get("features", [])
        for index, feature in enumerate(features):
            json_str = json.dumps(feature, separators=(",", ":"), ensure_ascii=False)
            handle.write(f"    {json_str}")
            if index < len(features) - 1:
                handle.write(",")
            handle.write("\n")
        handle.write("  ]\n")
        handle.write("}\n")


def determine_output_directory(input_directory, output_directory=None):
    """Determine where processed files should be written."""
    if output_directory:
        return output_directory

    normalized_input = os.path.normpath(input_directory)
    input_name = os.path.basename(normalized_input)
    parent_directory = os.path.dirname(normalized_input)

    if input_name == "filtered":
        return os.path.join(parent_directory, DEFAULT_OUTPUT_DIRNAME)

    return os.path.join(normalized_input, DEFAULT_OUTPUT_DIRNAME)


def process_geojson_file(file_path, output_directory, property_renaming, property_value_decimals, coordinate_value_decimals):
    """Process a single GeoJSON file."""
    with open(file_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    for feature in data.get("features", []):
        transform_feature(
            feature,
            property_renaming,
            property_value_decimals,
            coordinate_value_decimals,
        )

    output_path = os.path.join(output_directory, os.path.basename(file_path))
    write_feature_collection(output_path, data)
    print(f"Saved: {output_path}")


def process_directory(input_directory, rules_path, output_directory=None):
    """Process all GeoJSON files in a directory."""
    property_renaming, property_value_decimals, coordinate_value_decimals = load_rules(rules_path)

    pattern = os.path.join(input_directory, "*.geojson")
    geojson_files = sorted(glob.glob(pattern))

    if not geojson_files:
        print(f"No GeoJSON files found in: {input_directory}")
        return 1

    output_directory = determine_output_directory(input_directory, output_directory)
    os.makedirs(output_directory, exist_ok=True)

    print(f"Using rules: {rules_path}")
    print(f"Input directory: {input_directory}")
    print(f"Output directory: {output_directory}")
    print(f"Found {len(geojson_files)} GeoJSON files to process")

    for file_path in geojson_files:
        try:
            print(f"Processing: {os.path.basename(file_path)}")
            process_geojson_file(
                file_path,
                output_directory,
                property_renaming,
                property_value_decimals,
                coordinate_value_decimals,
            )
        except Exception as exc:
            print(f"Error processing {file_path}: {exc}")

    return 0


def main():
    """Handle command line arguments."""
    if len(sys.argv) < 2 or len(sys.argv) > 4:
        print("Usage: python shorten_filtered_geojson.py <filtered_directory> [rules_json] [output_directory]")
        print("Example: python shorten_filtered_geojson.py 'Data 20260511/hamburg/filtered'")
        sys.exit(1)

    input_directory = sys.argv[1]
    rules_path = sys.argv[2] if len(sys.argv) >= 3 else str(DEFAULT_RULES_FILE)
    output_directory = sys.argv[3] if len(sys.argv) == 4 else None

    if not os.path.isdir(input_directory):
        print(f"Error: Directory '{input_directory}' not found.")
        sys.exit(1)

    if not os.path.isfile(rules_path):
        print(f"Error: Rules file '{rules_path}' not found.")
        sys.exit(1)

    exit_code = process_directory(input_directory, rules_path, output_directory)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
