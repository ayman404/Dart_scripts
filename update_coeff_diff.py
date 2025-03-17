import xml.etree.ElementTree as ET
from xml.dom import minidom
import json
import os

def create_thermal_function(id_temperature, mean_t, delta_t):
    thermal_func = ET.Element("ThermalFunction")
    thermal_func.set("deltaT", str(delta_t))
    thermal_func.set("idTemperature", id_temperature)
    thermal_func.set("meanT", str(mean_t))
    thermal_func.set("override3DMatrix", "0")
    thermal_func.set("singleTemperatureSurface", "1")
    thermal_func.set("useOpticalFactorMatrix", "0")
    thermal_func.set("usePrecomputedIPARs", "0")
    return thermal_func

def create_lambertian_multi(ident, model_name, database_name, use_prospect=False, prospect_params=None):
    lambertian_multi = ET.Element("LambertianMulti")
    lambertian_multi.set("ident", ident)
    lambertian_multi.set("lambertianDefinition", "0")
    lambertian_multi.set("roStDev", "0.0")
    lambertian_multi.set("useMultiplicativeFactorForLUT", "0")
    
    lambertian = ET.SubElement(lambertian_multi, "Lambertian")
    lambertian.set("ModelName", model_name)
    lambertian.set("databaseName", database_name)
    lambertian.set("useSpecular", "0")
    
    prospect_module = ET.SubElement(lambertian, "ProspectExternalModule")
    prospect_module.set("isFluorescent", "0")
    prospect_module.set("useProspectExternalModule", "1" if use_prospect else "0")
    
    if use_prospect and prospect_params:
        params = ET.SubElement(prospect_module, "ProspectExternParameters")
        for key, value in prospect_params.items():
            params.set(key, str(value))
    
    return lambertian_multi

def count_trees_in_position_file(position_file_path):
    try:
        with open(position_file_path, 'r') as f:
            lines = f.readlines()
            # Count lines that start with '0' (tree positions)
            tree_count = sum(1 for line in lines if line.strip().startswith('0'))
        return tree_count
    except Exception as e:
        print(f"Error reading position file: {e}")
        return 0

def update_coeff_diff_xml(config_path):
    # Read configuration
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Get paths and settings
    position_file = config['paths']['position_txt_path']
    simulation_path = config['paths']['simulation_path']
    params_to_vary = config['parameters_to_vary']
    
    # Count number of trees
    num_trees = count_trees_in_position_file(position_file)
    if num_trees == 0:
        print("No trees found in position file!")
        return
    
    print(f"Found {num_trees} trees in position file")
    
    # Create root element
    root = ET.Element("DartFile")
    root.set("build", "v1410")
    root.set("version", "5.10.6")
    
    # Create Coeff_diff element
    coeff_diff = ET.SubElement(root, "Coeff_diff")
    coeff_diff.set("fluorescenceFile", "0")
    coeff_diff.set("fluorescenceProducts", "0")
    coeff_diff.set("useCombinedYield", "0")
    
    # Create Surfaces section
    surfaces = ET.SubElement(coeff_diff, "Surfaces")
    lambertian_multi_functions = ET.SubElement(surfaces, "LambertianMultiFunctions")
    
    # Prospect parameters for leaves
    prospect_params = {
        "CBrown": "0.0",
        "Cab": "60.0",
        "Car": "30.0",
        "Cbc": "0.009",
        "Cm": "0.01",
        "Cp": "0.001",
        "Cw": "0.012",
        "N": "1.5",
        "anthocyanin": "0.0",
        "inputProspectFile": "Prospect_Fluspect/Optipar2021_ProspectPRO.txt",
        "isV2Z": "0",
        "useCm": "0"
    }
    
    # Add leaf entries if chlorophyl or water_thickness is true
    if params_to_vary['chlorophyl'] or params_to_vary['water_thickness']:
        for i in range(num_trees):
            leaf = create_lambertian_multi(
                f"leaf_{i}",
                "reflect_equal_1_trans_equal_0_0",
                "Lambertian_vegetation.db",
                True,
                prospect_params
            )
            lambertian_multi_functions.append(leaf)
    
    # Add trunk entry
    trunk = create_lambertian_multi("trunk", "bark_spruce", "Lambertian_vegetation.db")
    lambertian_multi_functions.append(trunk)
    
    # Add soil entry
    soil = create_lambertian_multi(
        "soil",
        "reflect_equal_1_trans_equal_0_0",
        "Lambertian_mineral.db"
    )
    lambertian_multi_functions.append(soil)
    
    # Add other required empty sections
    for section in ["HapkeSpecularMultiFunctions", "RPVMultiFunctions",
                   "PhaseExternMultiFunctions", "SpecularMultiFunctions",
                   "MixedMultiFunctions"]:
        ET.SubElement(surfaces, section)
    
    # Create Volumes section
    volumes = ET.SubElement(coeff_diff, "Volumes")
    understory = ET.SubElement(volumes, "UnderstoryMultiFunctions")
    understory.set("integrationStepOnPhi", "10")
    understory.set("integrationStepOnTheta", "1")
    understory.set("outputLADFile", "0")
    ET.SubElement(volumes, "AirMultiFunctions")
    
    # Create Temperatures section
    temperatures = ET.SubElement(coeff_diff, "Temperatures")
    
    # Add Temp_soil
    temperatures.append(create_thermal_function("Temp_soil", 300.0, 0))
    
    # Add temperature functions based on tree_temperature setting
    if params_to_vary['tree_temperature']:
        # Add individual temperature entries for each tree
        for i in range(num_trees):
            temperatures.append(create_thermal_function(f"Temp_leaf_{i}", 300.0, 0))
            temperatures.append(create_thermal_function(f"Temp_trunk_{i}", 300.0, 0))
    else:
        # Add a single temperature range for all trees
        temperatures.append(create_thermal_function("Temperature_290_310", 300.0, 10))
    
    # Convert to string with pretty printing
    xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")
    
    # Write to file
    output_path = os.path.join(simulation_path, "input", "coeff_diff.xml")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        # Remove the first line (xml declaration) since we already wrote it
        f.write(xmlstr[xmlstr.find("\n")+1:])
    
    print(f"Updated coeff_diff.xml has been generated at: {output_path}")

if __name__ == "__main__":
    config_path = "config.json"
    update_coeff_diff_xml(config_path) 