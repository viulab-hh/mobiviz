import sys
import json
import os
import glob

# List of property keys to keep (edit this list as needed)
# List of property keys to keep (you can include comments)
# keep_keys = [
#     "EW_22",
#     "EW_40",
# 	"t_100pctDocs_Nom", #: nominal time, d.h. die wahrscheinlichste Zeit in Minuten
# 	"t_100pctDocs_Min", #: minimum time, d.h. die minimale Zeit in Minuten
# 	"t_100pctDocs_Max", #: maximum time, d.h. die maximale Zeit in Minuten
# 	# "tNom_100pctDocs", #: nominal time, d.h. die wahrscheinlichste Zeit in Minuten
# 	# "tMin_100pctDocs", #: minimum time, d.h. die minimale Zeit in Minuten
# 	# "tMax_100pctDocs", #: maximum time, d.h. die maximale Zeit in Minuten
# 	"EwM_22_100pctDocs_Nom", #: nominal (Einwohner*Minuten), d.h. die wahrscheinlichste Zeit in Minuten, gewichtet mit der Bevölkerung
# 	"EwM_22_100pctDocs_Min", #: minimum (Einwohner*Minuten), d.h. die minimale Zeit in Minuten, gewichtet mit der Bevölkerung
# 	"EwM_22_100pctDocs_Max", #: maximum (Einwohner*Minuten), d.h. die maximale Zeit in Minuten, gewichtet mit der Bevölkerung
# 	"EwM_22_40_070pctDocs_Nom_pct", #: Prozentuale Veränderung von 2022 zu 2040 in Einwohner*Minuten
# ]

keep_keys = [
    # ungewichtet
    "tMin_100pctDocs",
    "tMax_100pctDocs",
    "tNom_100pctDocs",
    "tNom_090pctDocs",
    "tNom_080pctDocs",
    
    # gewichtet
    "EwM_22_Min_100pctDocs",
    "EwM_22_Max_100pctDocs",
    "EwM_22_Nom_100pctDocs",
    # "EwM_22_40_Nom_090pctDocs_diff",
    # "EwM_22_40_Nom_080pctDocs_diff",
    "EwM_40_Nom_090pctDocs",
    "EwM_40_Nom_080pctDocs",
]

TRANSPORT_PREFIXES = ("car_", "transit_")

def expanded_keep_keys():
    keys = set(keep_keys)
    for key in keep_keys:
        for prefix in TRANSPORT_PREFIXES:
            keys.add(prefix + key)
    return keys

def get_output_filename(input_filename):
    """
    Build the filtered output filename from the input filename.

    Expected structure:
    - timestamp
    - optional transport/source token ("car", "transit", "osm")
    - location
    - optional extra "dannenberg" token for "luechow_dannenberg"
    - specialty
    """
    base, ext = os.path.splitext(input_filename)
    filename_parts = base.split("_")

    index = 1  # Skip timestamp
    output_prefix = ""

    if index < len(filename_parts):
        if filename_parts[index] in {"car", "transit"}:
            output_prefix = f"{filename_parts[index]}_"
            index += 1
        elif filename_parts[index] == "osm":
            index += 1

    if index >= len(filename_parts):
        return f"{base}_filtered{ext}"

    location = filename_parts[index]
    index += 1

    # Some files spell the location as "luechow_dannenberg"; ignore the extra token.
    if location == "luechow" and index < len(filename_parts) and filename_parts[index] == "dannenberg":
        index += 1

    if index < len(filename_parts):
        return output_prefix + filename_parts[index] + ext

    return f"{base}_filtered{ext}"

def filter_properties(input_path):
    # Load the input GeoJSON
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    allowed_keys = expanded_keep_keys()

    # Filter properties in each feature
    for feature in data.get("features", []):
        if "properties" in feature:
            feature["properties"] = {
                k: v for k, v in feature["properties"].items() if k in allowed_keys
            }

    # Write output to new file, compact with one-line-per-feature
    # Get directory and filename
    input_dir = os.path.dirname(input_path)
    input_filename = os.path.basename(input_path)
    
    new_filename = get_output_filename(input_filename)
    
    # Add "filtered" subfolder and construct output path
    filtered_dir = os.path.join(input_dir, "filtered")
    os.makedirs(filtered_dir, exist_ok=True)
    output_path = os.path.join(filtered_dir, new_filename)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('{"type":"FeatureCollection","features":[\n')
        for i, feature in enumerate(data.get("features", [])):
            json_str = json.dumps(feature, separators=(',', ':'))
            f.write(json_str)
            if i < len(data["features"]) - 1:
                f.write(',\n')
        f.write('\n]}')

    print(f"Filtered GeoJSON saved to: {output_path}")

def process_directory(directory_path):
    """
    Process all GeoJSON files in a directory.
    
    Args:
        directory_path (str): Path to directory containing GeoJSON files
    """
    # Find all GeoJSON files in the directory
    pattern = os.path.join(directory_path, "*.geojson")
    geojson_files = glob.glob(pattern)
    
    if not geojson_files:
        print(f"No GeoJSON files found in: {directory_path}")
        return
    
    print(f"Found {len(geojson_files)} GeoJSON files to process")
    
    # Process each file
    for file_path in geojson_files:
        try:
            print(f"\nProcessing: {os.path.basename(file_path)}")
            filter_properties(file_path)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python filter_geojson_props.py <path_to_geojson_file_or_directory>")
        print("  - If path is a file: processes that single GeoJSON file")
        print("  - If path is a directory: processes all *.geojson files in the directory")
        sys.exit(1)

    input_path = sys.argv[1]
    
    if not os.path.exists(input_path):
        print(f"Error: Path '{input_path}' does not exist.")
        sys.exit(1)
    
    if os.path.isfile(input_path):
        # Single file processing
        if input_path.lower().endswith('.geojson'):
            print(f"Processing single file: {input_path}")
            filter_properties(input_path)
        else:
            print(f"Error: '{input_path}' is not a GeoJSON file.")
            sys.exit(1)
    elif os.path.isdir(input_path):
        # Directory processing
        print(f"Processing directory: {input_path}")
        process_directory(input_path)
    else:
        print(f"Error: '{input_path}' is neither a file nor a directory.")
        sys.exit(1)
