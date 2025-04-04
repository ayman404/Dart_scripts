import os
import json
import numpy as np
import xml.etree.ElementTree as ET

np.seterr(divide='ignore', invalid='ignore')

def load_config():
    """Load configuration from config.json file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    with open(config_path, 'r') as f:
        return json.load(f)


    
    
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
    
    

if __name__ == "__main__":
    # Add lai values
    config = load_config()
    
    # Get paths from configuration
    simulation_path = config['paths']['simulation_path']
    output_tif_path = config['paths']['output_tif_path']
    lai_file= config['paths']['lai_file']
    object_3d_directory= os.path.join(simulation_path, "input")
    process_sequences(lai_file, output_tif_path, object_3d_directory)   

