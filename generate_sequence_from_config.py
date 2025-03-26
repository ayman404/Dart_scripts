import xml.etree.ElementTree as ET
from xml.dom import minidom
import json
import random as rd
import os
import sys
from preprocess_soils import check_soil_factor_path, get_spectral_intervals

def get_available_soils(config_path):
    """Get list of available soil names based on configuration"""
    try:
        # Read configuration
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # If multi_sol is not enabled, return None
        if not config['simulation_settings']['multi_sol']:
            return None
            
        soil_factor_path = config['paths']['soil_factor_path']
        simulation_path = config['paths']['simulation_path']
        
        # Check if soil factor path exists
        if not os.path.exists(soil_factor_path) or not os.path.isdir(soil_factor_path):
            print(f"Warning: Soil factor directory not found: {soil_factor_path}")
            return None
        
        # Get spectral information for validation
        spectral_info = get_spectral_intervals(simulation_path)
        if not spectral_info:
            print("Warning: Could not get spectral intervals information")
            return None
        
        # Check soil folders and validate
        valid_soils = []
        try:
            # Import the function if possible
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from preprocess_soils import check_soil_band_files
            valid_soils = check_soil_band_files(soil_factor_path, spectral_info)
        except (ImportError, AttributeError):
            # Fallback if import fails: just use directory names
            valid_soils = [f for f in os.listdir(soil_factor_path) 
                         if os.path.isdir(os.path.join(soil_factor_path, f))]
            print("Warning: Using directory names as soil identifiers without validation")
        
        if not valid_soils:
            print("Warning: No valid soil folders found")
            return None
            
        return valid_soils
    
    except Exception as e:
        print(f"Error getting available soils: {str(e)}")
        return None

def read_scale_from_positions(position_file_path):
    """Read scale values from positions.txt file."""
    scales = []
    try:
        with open(position_file_path, 'r') as f:
            for line in f:
                if line.strip().startswith('0'):  # Tree position line
                    values = line.strip().split()
                    if len(values) >= 7:  # Ensure we have scale values
                        scales.append(float(values[4]))  # xscale value
    except Exception as e:
        print(f"Error reading position file: {e}")
    return scales

def count_trees_in_position_file(position_file_path):
    """Count number of trees in position file."""
    try:
        with open(position_file_path, 'r') as f:
            lines = f.readlines()
            tree_count = sum(1 for line in lines if line.strip().startswith('0'))
        return tree_count
    except Exception as e:
        print(f"Error reading position file: {e}")
        return 0

def generate_random_values(nbr_simulation, num_trees):
    """Generate random values for parameters."""
    # Generate Cab values (chlorophyll content) - different for each tree
    cab_values = []
    for _ in range(num_trees):
        cab_values.append([str(rd.random() * 70 + 20) for _ in range(nbr_simulation)])
    
    # Generate Cw values (water content) - different for each tree
    cw_values = []
    for _ in range(num_trees):
        cw_values.append([str(rd.random() * 0.04 + 0.01) for _ in range(nbr_simulation)])
    
    # Generate temperature values
    temp_values = []
    for _ in range(nbr_simulation):
        # Base soil temperature between 290K-310K
        soil = rd.uniform(290, 310)
        temps = [soil]  # Soil temperature
        
        # Leaf temperatures (cooler than soil)
        for _ in range(num_trees):
            leaf_temp = soil - rd.uniform(1, 10)
            temps.append(leaf_temp)
        
        # Trunk temperatures (between soil and leaf)
        for _ in range(num_trees):
            trunk_temp = soil - rd.uniform(0.5, 5)
            temps.append(trunk_temp)
        
        temp_values.append([str(t) for t in temps])
    
    return cab_values, cw_values, temp_values

def create_sequence_xml(config_path):
    # Read configuration
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Get parameters
    nbr_simulation = config['nbr_of_sequence']
    position_file = config['paths']['position_txt_path']
    params_to_vary = config['parameters_to_vary']
    
    # Count trees
    num_trees = count_trees_in_position_file(position_file)
    if num_trees == 0:
        print("No trees found in position file!")
        return
    
    print(f"Found {num_trees} trees in position file")
    
    # Generate random values
    cab_values, cw_values, temp_values = generate_random_values(nbr_simulation, num_trees)
    
    # Read scales from positions file if needed
    scales = read_scale_from_positions(position_file) if params_to_vary['scale'] else []
    
    # Determine starting index offset for LambertianMulti elements
    offset = 0
    if config['simulation_settings']['multi_sol']:
        soils = get_available_soils(config_path)
        if soils and len(soils) > 0:
            offset = len(soils)
            print(f"Multi-soil enabled with {offset} soils - tree LambertianMulti indices will start from {offset}")
    
    # Create root element
    root = ET.Element("DartFile")
    root.set("version", "1.0")
    
    # Create DartSequencerDescriptor
    descriptor = ET.SubElement(root, "DartSequencerDescriptor")
    descriptor.set("sequenceName", "sequence;;sequence")
    
    # Create entries section
    entries = ET.SubElement(descriptor, "DartSequencerDescriptorEntries")
    
    # Create primary group for parameters
    group = ET.SubElement(entries, "DartSequencerDescriptorGroup")
    group.set("currentDisplayedPage", "1")
    group.set("groupName", "group1")
    
    # Add entries based on parameters_to_vary
    
    # Scale entries
    if params_to_vary['scale'] and scales:
        for i in range(num_trees):
            # Generate scale deviation for this object
            scale_deviation = [str(scales[i] * (0.8 + 0.4 * rd.random())) for _ in range(nbr_simulation)]
            
            # Add scale entries
            for axis in ['x', 'y', 'z']:
                scale_entry = ET.SubElement(group, "DartSequencerDescriptorEntry")
                scale_entry.set("args", ";".join(scale_deviation))
                scale_entry.set("propertyName", f"object_3d.ObjectList.Object[{i}].GeometricProperties.ScaleProperties.{axis}scale")
                scale_entry.set("type", "enumerate")
    
    # Temperature entries
    if params_to_vary['tree_temperature'] or params_to_vary['soil_temperature']:
        # Soil temperature (if enabled)
        if params_to_vary['soil_temperature']:
            soil_temp_entry = ET.SubElement(group, "DartSequencerDescriptorEntry")
            soil_temp_args = [temp_list[0] for temp_list in temp_values]
            soil_temp_entry.set("args", ";".join(soil_temp_args))
            soil_temp_entry.set("propertyName", "Coeff_diff.Temperatures.ThermalFunction[0].meanT")
            soil_temp_entry.set("type", "enumerate")
        
        # Tree temperatures (if enabled)
        if params_to_vary['tree_temperature']:
            # Leaf temperatures
            for i in range(num_trees):
                leaf_temp_entry = ET.SubElement(group, "DartSequencerDescriptorEntry")
                leaf_temp_args = [temp_list[i + 1] for temp_list in temp_values]
                leaf_temp_entry.set("args", ";".join(leaf_temp_args))
                leaf_temp_entry.set("propertyName", f"Coeff_diff.Temperatures.ThermalFunction[{1 + 2 * i}].meanT")
                leaf_temp_entry.set("type", "enumerate")
            
            # Trunk temperatures
            for i in range(num_trees):
                trunk_temp_entry = ET.SubElement(group, "DartSequencerDescriptorEntry")
                trunk_temp_args = [temp_list[i + num_trees + 1] for temp_list in temp_values]
                trunk_temp_entry.set("args", ";".join(trunk_temp_args))
                trunk_temp_entry.set("propertyName", f"Coeff_diff.Temperatures.ThermalFunction[{2 + 2 * i}].meanT")
                trunk_temp_entry.set("type", "enumerate")
    
    # Chlorophyll (Cab) entries
    if params_to_vary['chlorophyl']:
        for i in range(num_trees):
            cab_entry = ET.SubElement(group, "DartSequencerDescriptorEntry")
            # Use tree-specific chlorophyll values
            tree_cab_values = cab_values[i]
            cab_entry.set("args", ";".join(tree_cab_values))
            # Use offset for LambertianMulti index
            lambertian_index = i + offset
            cab_entry.set("propertyName", f"Coeff_diff.Surfaces.LambertianMultiFunctions.LambertianMulti[{lambertian_index}].Lambertian.ProspectExternalModule.ProspectExternParameters.Cab")
            cab_entry.set("type", "enumerate")
    
    # Water thickness (Cw) entries
    if params_to_vary['water_thickness']:
        for i in range(num_trees):
            cw_entry = ET.SubElement(group, "DartSequencerDescriptorEntry")
            # Use tree-specific water content values
            tree_cw_values = cw_values[i]
            cw_entry.set("args", ";".join(tree_cw_values))
            # Use offset for LambertianMulti index
            lambertian_index = i + offset
            cw_entry.set("propertyName", f"Coeff_diff.Surfaces.LambertianMultiFunctions.LambertianMulti[{lambertian_index}].Lambertian.ProspectExternalModule.ProspectExternParameters.Cw")
            cw_entry.set("type", "enumerate")
    
    # Handle multi_sol setting
    if config['simulation_settings']['multi_sol']:
        soils = get_available_soils(config_path)
        if not soils or len(soils) == 0:
            print("No valid soils found. Using default soil configuration.")
            # No need to add soil-specific entries
        else:
            print(f"Found {len(soils)} valid soil(s). Adding soil entries to sequence.")
            
            # Create a dedicated group for soil parameters
            soil_group = ET.SubElement(entries, "DartSequencerDescriptorGroup")
            soil_group.set("currentDisplayedPage", "1")
            soil_group.set("groupName", "group_soil")
            
            # Format soil identifiers
            soil_identifiers = [f"soil_{soil}" for soil in soils]
            
            # Create entry for soil optical property
            soil_entry = ET.SubElement(soil_group, "DartSequencerDescriptorEntry")
            soil_entry.set("args", ";".join(soil_identifiers))
            soil_entry.set("propertyName", "Maket.Soil.OpticalPropertyLink.ident")
            soil_entry.set("type", "enumerate")
            
            # Create entry for indexFctPhase
            phase_indices = [str(i) for i in range(len(soils))]  #
            phase_entry = ET.SubElement(soil_group, "DartSequencerDescriptorEntry")
            phase_entry.set("args", ";".join(phase_indices))
            phase_entry.set("propertyName", "Maket.Soil.OpticalPropertyLink.indexFctPhase")
            phase_entry.set("type", "enumerate")
            
            print(f"Added soil entries with identifiers: {', '.join(soil_identifiers)}")
            print(f"Added phase indices: {', '.join(phase_indices)}")
    
    # Add DartSequencerPreferences
    preferences = ET.SubElement(descriptor, "DartSequencerPreferences")
    preferences_attrs = {
        "atmosphereMaketLaunched": "true",
        "dartLaunched": "true",
        "deleteAll": "false",
        "deleteAtmosphere": "false",
        "deleteAtmosphereMaket": "false",
        "deleteBandFolder": "false",
        "deleteDartLut": "false",
        "deleteDartSequenceur": "false",
        "deleteDartTxt": "false",
        "deleteDirection": "false",
        "deleteInputs": "false",
        "deleteLibPhase": "false",
        "deleteMaket": "false",
        "deleteMaketTreeResults": "false",
        "deletePlyFolder": "false",
        "deleteScnFiles": "false",
        "deleteTreePosition": "false",
        "deleteTriangles": "false",
        "demGeneratorLaunched": "false",
        "directionLaunched": "false",
        "displayEnabled": "true",
        "hapkeLaunched": "false",
        "individualDisplayEnabled": "false",
        "maketLaunched": "true",
        "numberOfEnumerateValuesDisplayed": "1000",
        "numberParallelThreads": "4",
        "phaseLaunched": "true",
        "prospectLaunched": "true",
        "triangleFileProcessorLaunched": "true",
        "useBroadBand": "true",
        "useSceneSpectra": "true",
        "vegetationLaunched": "true",
        "zippedResults": "false"
    }
    for key, value in preferences_attrs.items():
        preferences.set(key, value)
    
    # Add DartLutPreferences
    lut_prefs = ET.SubElement(descriptor, "DartLutPreferences")
    lut_attrs = {
        "addedDirection": "false",
        "atmosToa": "false",
        "atmosToaOrdre": "false",
        "coupl": "true",
        "fluorescence": "true",
        "generateLUT": "false",
        "iterx": "true",
        "luminance": "true",
        "maketCoverage": "false",
        "ordre": "true",
        "otherIter": "true",
        "phiMax": "",
        "phiMin": "",
        "productsPerType": "false",
        "reflectance": "true",
        "sensor": "true",
        "storeIndirect": "false",
        "thetaMax": "",
        "thetaMin": "",
        "toa": "true"
    }
    for key, value in lut_attrs.items():
        lut_prefs.set(key, value)
    
    # Convert to string with pretty printing
    xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")
    
    # Write to file
    output_path = os.path.join(config['paths']['simulation_path'], "sequence.xml")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(xmlstr[xmlstr.find("\n")+1:])
    
    print(f"sequence.xml has been generated successfully.")

if __name__ == "__main__":
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    create_sequence_xml(config_path)