import os
import sys
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from preprocess_soils import check_soil_factor_path, get_spectral_intervals

def load_config():
    """Load configuration from config.json file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    with open(config_path, 'r') as f:
        return json.load(f)

def get_soil_names_from_coeff_diff(simulation_path):
    """Extract soil names from coeff_diff.xml based on LambertianMulti elements"""
    coeff_diff_path = os.path.join(simulation_path, "input", "coeff_diff.xml")
    
    if not os.path.exists(coeff_diff_path):
        print(f"Error: coeff_diff.xml not found at {coeff_diff_path}")
        return None

    try:
        tree = ET.parse(coeff_diff_path)
        root = tree.getroot()
        
        # Find all LambertianMulti elements
        soil_elements = []
        lambertian_multi_list = root.findall(".//LambertianMultiFunctions/LambertianMulti")
        
        for element in lambertian_multi_list:
            ident = element.get("ident")
            if ident and ident.startswith("soil_"):
                soil_elements.append(ident)
        
        return soil_elements
    except Exception as e:
        print(f"Error parsing coeff_diff.xml: {str(e)}")
        return None

def get_thermal_functions_from_coeff_diff(simulation_path):
    """Extract thermal function IDs from coeff_diff.xml"""
    coeff_diff_path = os.path.join(simulation_path, "input", "coeff_diff.xml")
    
    if not os.path.exists(coeff_diff_path):
        print(f"Error: coeff_diff.xml not found at {coeff_diff_path}")
        return None

    try:
        tree = ET.parse(coeff_diff_path)
        root = tree.getroot()
        
        # Find all ThermalFunction elements
        thermal_functions = []
        thermal_function_list = root.findall(".//Temperatures/ThermalFunction")
        
        for element in thermal_function_list:
            id_temp = element.get("idTemperature")
            if id_temp:
                thermal_functions.append(id_temp)
        
        return thermal_functions
    except Exception as e:
        print(f"Error parsing coeff_diff.xml for thermal functions: {str(e)}")
        return None

def determine_soil_name(config_path, simulation_path):
    """Determine soil name based on multi_sol setting and available soil folders"""
    # Read configuration
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Check multi_sol setting
    multi_sol = config['simulation_settings']['multi_sol']
    
    if not multi_sol:
        # If multi_sol is False, use default soil
        return "soil"
    
    # Get soil names from coeff_diff.xml
    soil_names = get_soil_names_from_coeff_diff(simulation_path)
    
    if not soil_names:
        print("Warning: No soil definitions found in coeff_diff.xml")
        return "soil"
    
    print(f"Found {len(soil_names)} soil definitions in coeff_diff.xml:")
    for soil in soil_names:
        print(f"  - {soil}")
    
    # Return the first soil name (we'll use others when doing multi-soil runs)
    return soil_names[0]

def determine_thermal_function(simulation_path, soil_name):
    # Default to first function or Temp_soil
    return "Temp_soil"

def update_maket_xml(config_path):
    """Update maket.xml with appropriate soil name and thermal properties from coeff_diff.xml"""
    # Read configuration
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Get simulation path
    simulation_path = config['paths']['simulation_path']
    
    # Path to maket.xml
    maket_path = os.path.join(simulation_path, "input", "maket.xml")
    
    if not os.path.exists(maket_path):
        print(f"Error: maket.xml not found at {maket_path}")
        return False
    
    # Create backup of original file
    backup_path = maket_path + ".backup"
    if not os.path.exists(backup_path):
        import shutil
        shutil.copy2(maket_path, backup_path)
        print(f"Created backup of maket.xml at {backup_path}")
    
    # Determine soil name to use
    soil_name = determine_soil_name(config_path, simulation_path)
    
    # Determine thermal function to use
    thermal_function = determine_thermal_function(simulation_path, soil_name)
    
    try:
        # Parse XML
        tree = ET.parse(maket_path)
        root = tree.getroot()
        
        # Update optical property
        soil_link = root.find(".//OpticalPropertyLink")
        if soil_link is None:
            print("Error: Could not find OpticalPropertyLink in maket.xml")
            return False
        
        current_soil = soil_link.get("ident")
        print(f"Updating optical property in maket.xml from '{current_soil}' to '{soil_name}'")
        soil_link.set("ident", soil_name)
        
        # Update thermal property
        thermal_link = root.find(".//ThermalPropertyLink")
        if thermal_link is None:
            print("Error: Could not find ThermalPropertyLink in maket.xml")
        else:
            current_thermal = thermal_link.get("idTemperature")
            print(f"Updating thermal property in maket.xml from '{current_thermal}' to '{thermal_function}'")
            thermal_link.set("idTemperature", thermal_function)
        
        # Write back to file with pretty formatting
        xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")
        
        with open(maket_path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            # Remove the first line (xml declaration) since we already wrote it
            f.write(xmlstr[xmlstr.find("\n")+1:])
        
        print(f"Successfully updated maket.xml with:")
        print(f"  - Soil optical property: {soil_name}")
        print(f"  - Soil thermal property: {thermal_function}")
        return True
        
    except Exception as e:
        print(f"Error updating maket.xml: {str(e)}")
        return False

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    
    # Check if config.json exists
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found at {config_path}")
        return
    
    # Update maket.xml
    if update_maket_xml(config_path):
        print("maket.xml update completed successfully.")
    else:
        print("maket.xml update failed. See error messages above.")

if __name__ == "__main__":
    main()
