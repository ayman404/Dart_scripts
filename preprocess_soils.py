import os
import json
import sys
import xml.etree.ElementTree as ET

def check_soil_band_files(soil_factor_path, spectral_info):
    """
    Check if each soil folder has the correct number of txt files matching the number of bands.
    
    Args:
        soil_factor_path (str): Path to the soil factor directory
        spectral_info (dict): Dictionary containing band numbers and their spectralDartMode values
    
    Returns:
        list: List of valid soil folder names that have the correct number of files
    """
    if not spectral_info:
        print("ERROR: No spectral information available")
        return []
    
    num_bands = len(spectral_info)
    valid_soils = []
    
    # Get all soil folders
    soil_folders = [f for f in os.listdir(soil_factor_path) 
                   if os.path.isdir(os.path.join(soil_factor_path, f))]
    
    for folder in soil_folders:
        folder_path = os.path.join(soil_factor_path, folder)
        
        # Count txt files in the folder
        txt_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
        num_files = len(txt_files)
        
        if num_files != num_bands:
            print(f"WARNING: Soil folder '{folder}' has {num_files} txt files, expected {num_bands} files")
            print(f"  Found files: {', '.join(txt_files)}")
            continue
        
        valid_soils.append(folder)
    
    if valid_soils:
        print("\nThe following soils will be used in the sequencer:")
        for soil in valid_soils:
            print(f"  - {soil}")
    else:
        print("\nWARNING: No valid soil folders found with the correct number of txt files!")
    
    return valid_soils

def get_spectral_intervals(simulation_path):
    """
    Check phase.xml in the simulation input folder and extract spectral intervals information.
    
    Args:
        simulation_path (str): Path to the simulation directory
    
    Returns:
        dict: Dictionary containing band numbers and their spectralDartMode values
    """
    try:
        # Construct path to phase.xml
        phase_xml_path = os.path.join(simulation_path, "input", "phase.xml")
        
        # Check if file exists
        if not os.path.exists(phase_xml_path):
            print(f"WARNING: phase.xml not found at: {phase_xml_path}")
            return None
        
        # Parse XML file
        tree = ET.parse(phase_xml_path)
        root = tree.getroot()
        
        # Find SpectralIntervals element
        spectral_intervals = root.find(".//SpectralIntervals")
        if spectral_intervals is None:
            print("WARNING: No SpectralIntervals found in phase.xml")
            return None
        
        # Extract band information
        band_info = {}
        for band in spectral_intervals.findall("SpectralIntervalsProperties"):
            band_number = band.get("bandNumber")
            spectral_mode = band.get("spectralDartMode")
            if band_number is not None and spectral_mode is not None:
                band_info[int(band_number)] = int(spectral_mode)
        
        if not band_info:
            print("WARNING: No valid spectral intervals found in phase.xml")
            return None
        
        print(f"Found {len(band_info)} spectral bands in phase.xml")
        print("Band information:")
        for band_num, mode in sorted(band_info.items()):
            print(f"  Band {band_num}: spectralDartMode = {mode}")
        
        return band_info
        
    except ET.ParseError as e:
        print(f"ERROR: Invalid XML in phase.xml: {str(e)}")
        return None
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while reading phase.xml: {str(e)}")
        return None

def check_soil_factor_path(config_path):
    """
    Check if soil_factor_path exists and contains valid soil folders.
    Print warnings based on configuration settings.
    
    Args:
        config_path (str): Path to the config.json file
    
    Returns:
        bool: True if path exists and contains valid soil folders, False otherwise
    """
    try:
        # Read configuration
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Get paths and settings
        soil_factor_path = config['paths']['soil_factor_path']
        simulation_path = config['paths']['simulation_path']
        multi_sol = config['simulation_settings']['multi_sol']
        run_sequencer = config['simulation_settings']['run_sequencer']
        
        # Check if path exists
        if not os.path.exists(soil_factor_path):
            print(f"WARNING: Soil factor directory not found: {soil_factor_path}")
            if multi_sol:
                print("WARNING: multi_sol is set to true but soil factor directory is missing!")
            if run_sequencer:
                print("WARNING: run_sequencer is set to true - sequencer will run with default soil only!")
            return False
        
        # Check if it's a directory
        if not os.path.isdir(soil_factor_path):
            print(f"WARNING: Soil factor path is not a directory: {soil_factor_path}")
            if multi_sol:
                print("WARNING: multi_sol is set to true but soil factor path is not a directory!")
            if run_sequencer:
                print("WARNING: run_sequencer is set to true - sequencer will run with default soil only!")
            return False
        
        # Get spectral intervals information
        '''spectral_info = get_spectral_intervals(simulation_path)
        if spectral_info is None:
            print("WARNING: Could not get spectral intervals information")
            return False
        
        # Check soil folders and their txt files
        valid_soils = check_soil_band_files(soil_factor_path, spectral_info)
        if not valid_soils:
            print("WARNING: No valid soil folders found with correct number of txt files!")
            return False'''
        
        return True
        
    except FileNotFoundError:
        print(f"ERROR: Config file not found: {config_path}")
        return False
    except json.JSONDecodeError:
        print(f"ERROR: Invalid JSON in config file: {config_path}")
        return False
    except KeyError:
        print("ERROR: Required configuration keys are missing in config.json")
        return False
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {str(e)}")
        return False

def main():
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    
    # Check soil factor path
    if not check_soil_factor_path(config_path):
        print("Soil factor path check failed. Please check the warnings above.")
        sys.exit(1)
    
    print("Soil factor path check completed successfully.")

if __name__ == "__main__":
    main() 