import sys
import os
import json
import numpy as np
import rasterio
from rasterio.transform import from_origin
import re
from preprocess_soils import get_spectral_intervals
import xml.etree.ElementTree as ET

np.seterr(divide='ignore', invalid='ignore')
    
# Charger les valeurs de LAI depuis le fichier lai.txt
def load_lai_values(lai_file):
    lai_values = {}
    with open(lai_file, 'r', encoding='utf-8') as f:
        for line in f:
            if ':' in line:
                key, value = line.split(':')
                lai_values[key.strip()] = float(value.strip())
    return lai_values

# Extraire les objets depuis object3d.xml
def extract_objects_from_xml(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    objects = []
    for obj in root.findall(".//Object"):
        file_src = obj.get("file_src").split('\\')[-1]  # Récupérer juste le nom du fichier
        objects.append(file_src.replace('.obj', ''))
    
    return objects

# Mettre à jour props.json avec les valeurs de LAI
def update_props_json(props_file, objects, lai_values):
    with open(props_file, 'r', encoding='utf-8') as f:
        props = json.load(f)
    
    for i, obj in enumerate(objects):
        if obj in lai_values:
            props[f'lai{i}'] = lai_values[obj]
    
    with open(props_file, 'w', encoding='utf-8') as f:
        json.dump(props, f, indent=4)

# Fonction principale pour parcourir les dossiers et ajouter les valeurs de LAI dans props.json
def process_sequences(lai_file, saveTIF_directory, xml_file_directory):
    lai_values = load_lai_values(lai_file)
    
    # Parcours des sous-dossiers dans saveTIF
    for sequence_dir in os.listdir(saveTIF_directory):
        sequence_path = os.path.join(saveTIF_directory, sequence_dir)
        
        if os.path.isdir(sequence_path):
            # Trouver le fichier object3d.xml dans xml_file_directory
            xml_file = os.path.join(xml_file_directory, 'object_3d.xml')
            if os.path.exists(xml_file):
                objects = extract_objects_from_xml(xml_file)
                
                # Trouver et mettre à jour le fichier props.json dans chaque séquence
                props_file = os.path.join(sequence_path, 'props.json')
                if os.path.exists(props_file):
                    update_props_json(props_file, objects, lai_values)
                    print(f'Mis à jour: {props_file}')    
    
np.seterr(divide='ignore', invalid='ignore')

def load_config():
    """Load configuration from config.json file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    with open(config_path, 'r') as f:
        return json.load(f)

def extract_size_from_config(content):
    """Extract image dimensions from header file"""
    size_match = re.search(r'Size=(\d+)\s+(\d+)', content)
    if size_match:
        columns = int(size_match.group(1))
        rows = int(size_match.group(2))
        #print(f"Extracted Size: Columns={columns}, Rows={rows}")
        return columns, rows
    else:
        # Alternative format
        ncols_match = re.search(r'ncols\s*=\s*(\d+)', content)
        nrows_match = re.search(r'nrows\s*=\s*(\d+)', content)
        if ncols_match and nrows_match:
            columns = int(ncols_match.group(1))
            rows = int(nrows_match.group(1))
            print(f"Extracted Size: Columns={columns}, Rows={rows}")
            return columns, rows
        else:
            raise ValueError("Size not found in the configuration file")

def get_band_mode_dict(simulation_path):
    """Get dictionary of band numbers and their spectral modes"""
    spectral_info = get_spectral_intervals(simulation_path)
    if not spectral_info:
        print("Warning: Failed to get spectral intervals. Treating all bands as reflectance bands.")
        return {}
    return spectral_info

def is_thermal_band(band_num, band_modes):
    """Check if the band is a thermal band based on its mode"""
    # SpectralDartMode = 2 indicates thermal band
    if band_num in band_modes and band_modes[band_num] == 2:
        return True
    # Default to False if band not found in the mapping
    return False

def save_tiff_and_props():
    """Process sequence outputs and save as GeoTIFF and properties JSON"""
    # Load configuration
    config = load_config()
    
    # Get paths from configuration
    simulation_path = config['paths']['simulation_path']
    output_tif_path = config['paths']['output_tif_path']
    
    # Ensure the output directory exists
    os.makedirs(output_tif_path, exist_ok=True)
    
    # Get band mode information
    band_modes = get_band_mode_dict(simulation_path)
    
    # Path to sequence directory
    pathsim = os.path.join(simulation_path, "sequence")
    pathsavesim = output_tif_path
    
    # Debug: Print paths
    #print(f"Reading from: {pathsim}")
    #print(f"Saving to: {pathsavesim}")
    
    # Check if sequence directory exists
    if not os.path.exists(pathsim):
        print(f"Error: Sequence directory not found at {pathsim}")
        return
    
    # Get sequence directories
    sequence_dirs = [d for d in os.listdir(pathsim) if os.path.isdir(os.path.join(pathsim, d))]
    print(f"Found {len(sequence_dirs)} sequence directories: {sequence_dirs}")
    
    # Process each sequence
    for seq_dir in sequence_dirs:
        # Create output directory for this sequence
        savedirectory = os.path.join(pathsavesim, seq_dir)
        print(f"\nProcessing sequence directory: {seq_dir}")
        os.makedirs(savedirectory, exist_ok=True)
        
        # Check properties file
        properties_path = os.path.join(pathsim, seq_dir, 'output', 'dart.sequenceur.properties')
        if not os.path.exists(properties_path):
            print(f"Properties file not found: {properties_path}")
            continue

        # Read and parse properties file
        props_dict = {}
        try:
            with open(properties_path, 'r') as g:
                contenu = g.read()
                x2 = contenu.split("\n")
                
                # Extract parameters and values
                for k in range(1, len(x2) - 1, 2):
                    if k+1 < len(x2) and ':' in x2[k] and ':' in x2[k+1]:
                        try:
                            param_parts = x2[k].split(':')
                            value_parts = x2[k+1].split(':')
                            
                            if len(param_parts) > 1 and len(value_parts) > 1:
                                param_name = param_parts[1].split('.')[-1]
                                # Try to convert to float, but keep as string if not possible
                                try:
                                    param_value = float(value_parts[1])
                                except ValueError:
                                    param_value = value_parts[1].strip()  # Keep as string but strip whitespace
                                props_dict[param_name + str(k//2)] = param_value
                        except (ValueError, IndexError) as e:
                            print(f"Error parsing line {k}: {e}")
        except Exception as e:
            print(f"Error reading properties file: {e}")
            continue

        # Save props.json
        with open(os.path.join(savedirectory, "props.json"), "w") as outfile:
            json.dump(props_dict, outfile)
        print(f"Created props.json")

        # Find available bands
        band_dir = os.path.join(pathsim, seq_dir, 'output')
        available_bands = [d for d in os.listdir(band_dir) if d.startswith("BAND") and os.path.isdir(os.path.join(band_dir, d))]
        
        if not available_bands:
            print(f"No band directories found in {band_dir}")
            continue
            
        print(f"Found {len(available_bands)} bands: {', '.join(available_bands)}")
        
        # Process band images
        bands_arr = []
        band_names = []
        
        for band in sorted(available_bands):
            band_num = int(band.replace("BAND", ""))
            band_names.append(band)
            
            # Determine if this is a thermal band
            is_thermal = is_thermal_band(band_num, band_modes)
            folder_type = "Tapp" if is_thermal else "BRF"
            
            # Check both BRF and Tapp folders
            band_folder = os.path.join(band_dir, band, folder_type, "ITERX", "IMAGES_DART")
            if not os.path.exists(band_folder):
                # Try the alternative folder
                alt_folder_type = "BRF" if folder_type == "Tapp" else "Tapp"
                band_folder = os.path.join(band_dir, band, alt_folder_type, "ITERX", "IMAGES_DART")
                if not os.path.exists(band_folder):
                    print(f"Band folder not found for {band}, skipping")
                    continue
                print(f"Using {alt_folder_type} instead of {folder_type} for {band}")
                folder_type = alt_folder_type
            
            print(f"Processing {band} as {'thermal' if is_thermal else 'reflectance'} band using {folder_type} folder")
            
            # Get header file
            ima_prefixed = sorted([filename for filename in os.listdir(band_folder) if filename.startswith("ima")])
            if not ima_prefixed:
                print(f"No image files found in: {band_folder}")
                continue
                
            header_files = sorted([filename for filename in ima_prefixed if filename.endswith("mpr")])
            if not header_files:
                print(f"No header files found in: {band_folder}")
                continue
                
            header_name = header_files[0]
            
            # Read header file
            try:
                with open(os.path.join(band_folder, header_name), "rb") as header_file:
                    header_content = header_file.read().decode('utf-8', errors='ignore')
                    rows, columns = extract_size_from_config(header_content)
            except Exception as e:
                print(f"Error reading header file for {band}: {e}")
                continue
                
            # Read image data
            img_files = sorted([filename for filename in ima_prefixed if filename.endswith("mp#")])
            if not img_files:
                print(f"No mp# files found for {band}")
                continue

            if len(img_files) > 1:
                print(f"Warning: Multiple mp# files found for {band}, using the first file: {img_files[0]}")
            
            img_name = img_files[0]
            
            try:
                img_data = np.fromfile(os.path.join(band_folder, img_name), dtype=np.double)
                #print(f"Band: {band}, Min: {np.min(img_data)}, Max: {np.max(img_data)}")
                
                img_data = np.reshape(img_data, (rows, columns))
                
                # Convert to 16-bit based on band type
                if is_thermal or folder_type == "Tapp":
                    # Scale temperature values appropriately
                    img_data_16bit = (img_data * 100).astype(np.uint16)  # Different scaling for temperature
                    #print(f"Using thermal scaling for {band}")
                else:
                    # Regular reflectance scaling
                    img_data_16bit = (10000 * img_data).astype(np.uint16)
                    #print(f"Using reflectance scaling for {band}")
                    
                bands_arr.append(img_data_16bit)
            except Exception as e:
                print(f"Error processing {band}: {e}")
        
        if not bands_arr:
            print(f"No valid bands processed for {seq_dir}, skipping")
            continue
        
        # Create GeoTIFF
        imagename = os.path.join(savedirectory, f"{seq_dir}.tif")
        
        # Add georeferencing info
        origin_x = 600000
        origin_y = 3850000
        pixel_size = 2.5  # 2.5 meter resolution
        transform = from_origin(origin_x, origin_y, pixel_size, pixel_size)
        
        try:
            with rasterio.open(
                imagename, 'w',
                driver='GTiff',
                height=bands_arr[0].shape[0],
                width=bands_arr[0].shape[1],
                count=len(bands_arr),
                dtype=str(bands_arr[0].dtype),
                crs="EPSG:32632",
                transform=transform
            ) as dst:
                for i, band_data in enumerate(bands_arr):
                    dst.write(band_data, i + 1)
                    dst.set_band_description(i + 1, band_names[i])
            
            print(f"Successfully created GeoTIFF for {seq_dir}.")
        except Exception as e:
            print(f"Error creating GeoTIFF for {seq_dir}: {e}")

    print("Processing complete")

if __name__ == "__main__":
    save_tiff_and_props()
    # Add lai values
    config = load_config()
    
    # Get paths from configuration
    simulation_path = config['paths']['simulation_path']
    output_tif_path = config['paths']['output_tif_path']
    lai_file= config['paths']['lai_file']
    object_3d_directory= os.path.join(simulation_path, "input")
    process_sequences(lai_file, output_tif_path, object_3d_directory)   
