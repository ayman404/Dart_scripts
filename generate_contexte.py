import os
import json
import numpy as np
import torch
import xml.etree.ElementTree as ET

def load_config():
    """Load configuration from config.json file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    with open(config_path, 'r') as f:
        return json.load(f)

def tree(array, position, scale, property_value):
    """Modifies an array by adding a property around a given position based on a scale."""
    tree_radius = 9.5 / 2
    a, b = position
    for x in range(array.shape[0]):
        for y in range(array.shape[1]):
            if (x - a) ** 2 + (y - b) ** 2 < (tree_radius * scale) ** 2:
                array[x, y] = property_value
    return array

def land_patch(positions, scales, cabs, cws, lais, img_shape, chlorophyl, water_thickness):
    """Generates property maps for Cab, Cw, and LAI based on the given parameters."""
    patches = []

    if chlorophyl and cabs:
        cab_patch = np.zeros(img_shape)
        for pos, scale, cab in zip(positions, scales, cabs):
            cab_patch = tree(cab_patch, pos, scale, cab)
        patches.append(cab_patch)

    if water_thickness and cws:
        cw_patch = np.zeros(img_shape)
        for pos, scale, cw in zip(positions, scales, cws):
            cw_patch = tree(cw_patch, pos, scale, cw)
        patches.append(cw_patch)

    lai_patch = np.zeros(img_shape)
    for pos, scale, lai in zip(positions, scales, lais):
        lai_patch = tree(lai_patch, pos, scale, lai)
    patches.append(lai_patch)

    return np.stack(patches).astype(np.float32)

def generate_contexts(grp_path, positions, img_height, img_width, chlorophyl, water_thickness, scales):
    """Generates and saves the contexts as context.pt files."""
    for folder in os.listdir(grp_path):
        folder_path = os.path.join(grp_path, folder)
        if os.path.isdir(folder_path) and os.listdir(folder_path):
            props_path = os.path.join(folder_path, "props.json")
            
            with open(props_path, 'r') as f:
                props = json.load(f)

            # Read values from props.json if scale is active
            if SCALE_ACTIVE:
                scales = [props[key] for key in sorted(props.keys()) if key.startswith("xscale")]  
            else:
                scales = XSCALES  # Read xscale from position.txt
            
            lais = [props[key] for key in sorted(props.keys()) if key.startswith("lai")]
            cabs = [props[key] for key in sorted(props.keys()) if key.startswith("Cab")] if chlorophyl else []
            cws = [props[key] for key in sorted(props.keys()) if key.startswith("Cw")] if water_thickness else []

            patch = land_patch(positions, scales, cabs, cws, lais, (img_height, img_width), chlorophyl, water_thickness)
            patch_tensor = torch.tensor(patch)

            torch.save(patch_tensor, os.path.join(folder_path, 'context.pt'))
            print(f" Context generated for {folder}")
            #print(f" Scales used: {scales}")

def read_positions(file):
    """Reads positions and Xscale values from a text file."""
    positions = []
    xscales = []
    with open(file, 'r') as f:
        for line in f:
            if line.startswith('//') or line.strip() == '':
                continue
            parts = line.split()
            if len(parts) >= 5:  # Ensure at least 5 columns
                x = float(parts[1])  # Xpos
                y = float(parts[2])  # Ypos
                xscale = float(parts[4])  # Xscale
                positions.append((x, y))
                xscales.append(xscale)
    return positions, xscales

def get_scene_dimensions(xml_file_path):
    """
    Extrait les dimensions x et y de la balise <SceneDimensions> dans un fichier XML.

    Args:
        xml_file_path (str): Chemin vers le fichier XML.

    Returns:
        tuple: (x, y) sous forme d'entiers si trouvés, sinon (None, None)
    """
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        scene_dimensions = root.find(".//SceneDimensions")
        if scene_dimensions is not None:
            x = int(scene_dimensions.attrib.get("x"))
            y = int(scene_dimensions.attrib.get("y"))
            return x, y
        else:
            print("Balise <SceneDimensions> non trouvée.")
            return None, None
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier XML : {e}")
        return None, None

if __name__ == "__main__":
    
    config = load_config()
    
    # Get paths from configuration
    positions_file = config['paths']['position_txt_path']
    output_tif_path = config['paths']['output_tif_path']
    simulation_path = config['paths']['simulation_path']
    
    maket_path = os.path.join(simulation_path, "input", "maket.xml")



    # Read the scale parameter correctly
    SCALE_ACTIVE = config["parameters_to_vary"].get("scale", True)
    #print(f" Configuration: scale (raw) = {SCALE_ACTIVE}")


    # Read positions and scales
    POSITIONS, XSCALES = read_positions(positions_file)

    # Read other parameters
    chlorophyl = config["parameters_to_vary"].get("chlorophyl", True)
    water_thickness = config["parameters_to_vary"].get("water_thickness", True)

    # Set scales based on scale setting
    if SCALE_ACTIVE:
        scales = []  # Scales will be read from props.json in generate_contexts
    else:
        scales = XSCALES  # Use xscales from position.txt
        

    x, y = get_scene_dimensions(maket_path)
    #print(f"x = {x}, y = {y}")
    

    # Generate contexts
    generate_contexts(output_tif_path, POSITIONS, x, y, chlorophyl, water_thickness, scales)
