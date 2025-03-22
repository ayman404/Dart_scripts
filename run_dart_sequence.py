import os
import sys
import json
from subprocess import Popen, STDOUT, PIPE
import subprocess
import random as rd
import time
import xml.etree.ElementTree as ET
import shutil
from preprocess_soils import get_spectral_intervals, check_soil_band_files

def load_config():
    """Load configuration from config.json file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    with open(config_path, 'r') as f:
        return json.load(f)

def get_dart_paths(simulation_path):
    """Derive DART paths from simulation path"""
    # Print original path for debugging
    #print(f"Original simulation path: {simulation_path}")
    
    # Handle mixed slashes by replacing all with the system separator
    simulation_path = simulation_path.replace('/', os.sep).replace('\\', os.sep)
    
    # Parse path based on whether it's a Windows path with drive letter
    if sys.platform == 'win32' and len(simulation_path) > 1 and simulation_path[1] == ':':
        # Windows path with drive letter (e.g., C:\Users\...)
        drive = simulation_path[:2]  # Just C: without the slash
        rest_of_path = simulation_path[2:].strip(os.sep)  # Remove leading and trailing slashes
        path_parts = rest_of_path.split(os.sep)
        path_parts = [p for p in path_parts if p]  # Remove empty strings
        path_parts.insert(0, drive)  # Add drive back to path parts
    else:
        # Unix-like path or path without drive letter
        path_parts = simulation_path.strip(os.sep).split(os.sep)
        path_parts = [p for p in path_parts if p]  # Remove empty strings
    
    #print(f"Path parts: {path_parts}")
    
    # Find 'DART' and 'user_data' in the path
    dart_index = -1
    user_data_index = -1
    
    for i, part in enumerate(path_parts):
        if part.upper() == 'DART':  # Case-insensitive match for robustness
            dart_index = i
        elif part.lower() == 'user_data':  # Case-insensitive match for robustness
            user_data_index = i
    
    if dart_index == -1:
        # If we can't find DART, raise an error
        raise ValueError("Error: 'DART' not found in the path. Please check the simulation path and try again.")
    else:
        # Create the base path including the drive letter if on Windows
        if sys.platform == 'win32' and path_parts[0].endswith(':'):
            base_path = path_parts[0] + os.sep + os.sep.join(path_parts[1:dart_index+1])
        else:
            base_path = os.sep + os.sep.join(path_parts[:dart_index+1])
    
    if user_data_index == -1:
        # If we can't find user_data, use the base_path/user_data
        print("Warning: Could not find 'user_data' in the path. Using defaults.")
        user_data_path = os.path.join(base_path, "user_data")
    else:
        # Create the user_data path including the drive letter if on Windows
        if sys.platform == 'win32' and path_parts[0].endswith(':'):
            user_data_path = path_parts[0] + os.sep + os.sep.join(path_parts[1:user_data_index+1])
        else:
            user_data_path = os.sep + os.sep.join(path_parts[:user_data_index+1])
    
    # Handle tools path based on platform
    if sys.platform == 'win32':
        tools_subpath = os.path.join('tools', 'windows')
    else:
        tools_subpath = 'tools'
    
    #print(f"DART_HOME: {base_path}")
    #print(f"DART_LOCAL: {user_data_path}")
    #print(f"DART_TOOLS: {os.path.join(base_path, tools_subpath)}")
    
    return {
        'DART_HOME': base_path,
        'DART_LOCAL': user_data_path,
        'DART_TOOLS': os.path.join(base_path, tools_subpath)
    }

def run_simulation(simulation, DART_HOME, DART_LOCAL, DART_TOOLS, direction=True, phase=True, maket=True, dart=True):
    """Run a DART simulation with specified parameters"""
    ext = '.bat' if sys.platform == 'win32' else '.sh'
    if direction and phase and maket and dart:
        steps = ['dart-full']
    else:
        steps = []
        if direction:
            steps.append('dart-directions')
        if phase:
            steps.append('dart-phase')
        if maket:
            steps.append('dart-maket')
        if dart:
            steps.append('dart-only')

    env = os.environ.copy()
    env['DART_HOME'] = DART_HOME
    env['DART_LOCAL'] = DART_LOCAL

    process = None
    log = open('run.log', 'w')

    for step in steps:
        cmd = (['bash'] if sys.platform != 'win32' else ['cmd', '/c']) + [step + ext, simulation.split(os.sep + 'simulations' + os.sep, 1)[-1]]
        print(f"Executing command: {cmd}")
        try:
            process = Popen(cmd, cwd=DART_TOOLS, env=env, stdout=log, stderr=STDOUT, shell=False, universal_newlines=True)
            if process.wait(timeout=600) > 0:  # Add timeout of 10 minutes
                print(f"Error: Command failed with code {process.returncode}")
                break
        except subprocess.TimeoutExpired:
            process.kill()
            print(f"Error: Command timed out after 10 minutes")
            return 1
    log.close()
    return 0 if process is None else process.returncode

def run_sequence(sequencexml, DART_HOME, DART_LOCAL, DART_TOOLS, start=True):
    """Run a DART sequence with specified parameters"""
    ext = '.bat' if sys.platform == 'win32' else '.sh'
    state = "-start" if start else "-continue"
    env = os.environ.copy()
    env['DART_HOME'] = DART_HOME
    env['DART_LOCAL'] = DART_LOCAL
    
    # Ensure consistent path separators
    if sys.platform == 'win32':
        sequencexml = sequencexml.replace('/', '\\')
        DART_LOCAL = DART_LOCAL.replace('/', '\\')
    
    try:
        # Extract just the simulation name and sequence.xml
        sep = '\\' if sys.platform == 'win32' else '/'
        parts = sequencexml.split(f'simulations{sep}')
        if len(parts) != 2:
            raise ValueError("Path must contain 'simulations' directory")
        rel_path = parts[1]  # This will be "test/sequence.xml" or similar
        print(f"Using relative path: {rel_path}")
        
    except (ValueError, IndexError) as e:
        print(f"Error processing path: {str(e)}")
        return 1
    
    log_file = 'run.log'
    log = open(log_file, 'w')
    
    # Construct command differently for Windows vs Linux
    if sys.platform == 'win32':
        cmd = ['cmd', '/c', os.path.join(DART_TOOLS, f"dart-sequence{ext}"), rel_path, state]
    else:
        cmd = ['bash', os.path.join(DART_TOOLS, f"dart-sequence{ext}"), rel_path, state]
    
    print(f"Executing sequence command: {cmd}")
    print(f"Working directory: {DART_TOOLS}")
    print(f"Environment variables: DART_HOME={DART_HOME}, DART_LOCAL={DART_LOCAL}")
    
    try:
        # Use subprocess.Popen with real-time output handling
        process = subprocess.Popen(
            cmd, 
            env=env, 
            shell=False, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            stdin=subprocess.PIPE,  # Add stdin pipe for interaction
            universal_newlines=True,
            bufsize=1  # Line buffered
        )
        
        print("Process started. Waiting for output...")
        
        # Read and print output in real-time
        for line in process.stdout:
            print(line, end='')  # Print to console
            log.write(line)      # Write to log file
            
            # Automatically respond to "Press any key to continue..." and "Terminate batch job (Y/N)?"
            if "Press any key to continue" in line or "Terminate batch job" in line:
                process.stdin.write('\n')
                process.stdin.flush()
            
            # Terminate process if "Total processing time" is detected
            if "Total processing time" in line:
                print("Total processing time detected. Terminating process.")
                process.terminate()
                break
            
        # Wait for process to complete with timeout
        return_code = process.wait(timeout=1800)  # 30 minute timeout
        
        #print(f"Process completed with return code: {return_code}")
        log.close()
        return return_code
        
    except subprocess.TimeoutExpired:
        print("Error: Process timed out after 30 minutes")
        process.kill()
        log.write("Process timed out after 30 minutes\n")
        log.close()
        return 1
    except Exception as e:
        print(f"Error executing command: {str(e)}")
        log.write(f"Error executing command: {str(e)}\n")
        log.close()
        return 1

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
        valid_soils = check_soil_band_files(soil_factor_path, spectral_info)
        if not valid_soils:
            print("Warning: No valid soil folders found with correct number of txt files")
            return None
            
        return valid_soils
    
    except Exception as e:
        print(f"Error getting available soils: {str(e)}")
        return None

def update_maket_xml_soil(simulation_path, soil_name):
    """Update the maket.xml file to use a specific soil"""
    try:
        # Path to maket.xml
        maket_path = os.path.join(simulation_path, "input", "maket.xml")
        
        # Check if file exists
        if not os.path.exists(maket_path):
            print(f"Error: maket.xml not found at {maket_path}")
            return False
        
        # Create backup of original file
        backup_path = maket_path + ".backup"
        if not os.path.exists(backup_path):
            shutil.copy2(maket_path, backup_path)
        
        # Parse XML
        tree = ET.parse(maket_path)
        root = tree.getroot()
        
        # Find OpticalPropertyLink
        soil_link = root.find(".//OpticalPropertyLink")
        if soil_link is None:
            print("Error: Could not find OpticalPropertyLink in maket.xml")
            return False
        
        # Update soil reference
        current_soil = soil_link.get("ident")
        new_soil = f"soil_{soil_name}"
        print(f"Updating soil in maket.xml from '{current_soil}' to '{new_soil}'")
        soil_link.set("ident", new_soil)
        
        # Write back to file
        tree.write(maket_path, encoding='UTF-8', xml_declaration=True)
        return True
        
    except Exception as e:
        print(f"Error updating maket.xml: {str(e)}")
        return False

def restore_original_maket_xml(simulation_path):
    """Restore the original maket.xml file from backup"""
    maket_path = os.path.join(simulation_path, "input", "maket.xml")
    backup_path = maket_path + ".backup"
    
    if os.path.exists(backup_path):
        shutil.copy2(backup_path, maket_path)
        print("Restored original maket.xml")
        return True
    else:
        print("Warning: No backup file found for maket.xml")
        return False

def safe_rename_directory(old_path, new_path):
    """Safely rename a directory by copying files and then deleting the old directory"""
    try:
        # Try direct rename first (faster)
        os.rename(old_path, new_path)
        return True
    except (PermissionError, OSError):
        print(f"Direct rename failed for {old_path}, trying copy and delete approach...")
        try:
            # If rename fails, copy and delete
            if os.path.exists(new_path):
                shutil.rmtree(new_path)
            shutil.copytree(old_path, new_path)
            # Wait a moment to ensure all file operations complete
            time.sleep(1)
            try:
                shutil.rmtree(old_path)
            except:
                print(f"Warning: Could not delete original directory {old_path} after copying")
            return True
        except Exception as e:
            print(f"Error copying directory: {str(e)}")
            return False

def run_for_all_soils(config, simulation_path, DART_HOME, DART_LOCAL, DART_TOOLS):
    """Run simulation and sequence for all available soils"""
    # Get the config path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    
    # Get available soils
    soils = get_available_soils(config_path)
    
    if not soils or len(soils) == 0:
        print("No valid soils found. Using default soil configuration.")
        # Run with default soil settings
        sequence_xml = os.path.join(simulation_path, "sequence.xml")
        
        # Ensure consistent path separators
        if sys.platform == 'win32':
            sequence_xml = sequence_xml.replace('/', '\\')
        
        # First run the root simulation
        print("Running root simulation before executing sequence...")
        sim_result = run_simulation(simulation_path, DART_HOME, DART_LOCAL, DART_TOOLS)
        
        if sim_result != 0:
            print(f"Error: Root simulation failed with return code: {sim_result}")
            return False
        
        print("Root simulation completed successfully. Proceeding with sequence...")
        
        # Now run the sequence
        result = run_sequence(sequence_xml, DART_HOME, DART_LOCAL, DART_TOOLS)
        
        if result == 0:
            print("Sequence completed successfully")
            return True
        else:
            print(f"Sequence failed with return code: {result}")
            return False
    else:
        print(f"Found {len(soils)} valid soil(s). Running simulation for each soil.")
        all_successful = True
        
        # Keep track of original output folders to prevent overwriting
        sequence_dir_base = os.path.join(simulation_path, "sequence")
        
        # Run for each soil
        for i, soil in enumerate(soils):
            print(f"\n=== Processing Soil {i+1}/{len(soils)}: {soil} ===")
            
            # Update maket.xml to use this soil
            if not update_maket_xml_soil(simulation_path, soil):
                print(f"Skipping soil '{soil}' due to error updating maket.xml")
                all_successful = False
                continue
            
            # Backup existing sequence folders by renaming them with soil name if needed
            if os.path.exists(sequence_dir_base):
                # Rename any existing sequence_i folders to include the current soil name
                if i > 0:  # Only needed after first soil
                    rename_sequence_folders(sequence_dir_base, soils[i-1], soils)
            else:
                # Create sequence directory if it doesn't exist
                os.makedirs(sequence_dir_base, exist_ok=True)
            
            sequence_xml = os.path.join(simulation_path, "sequence.xml")
            if sys.platform == 'win32':
                sequence_xml = sequence_xml.replace('/', '\\')
            
            # Run the root simulation
            print(f"Running root simulation for soil '{soil}'...")
            sim_result = run_simulation(simulation_path, DART_HOME, DART_LOCAL, DART_TOOLS)
            
            if sim_result != 0:
                print(f"Error: Root simulation failed for soil '{soil}' with return code: {sim_result}")
                all_successful = False
                continue
            
            # Run the sequence
            print(f"Running sequence for soil '{soil}'...")
            result = run_sequence(sequence_xml, DART_HOME, DART_LOCAL, DART_TOOLS)
            
            if result == 0:
                print(f"Sequence completed successfully for soil '{soil}'")
                
                # For the last soil, rename its sequence folders immediately
                if i == len(soils) - 1:
                    print(f"Renaming sequence folders for the last soil: {soil}")
                    rename_sequence_folders(sequence_dir_base, soil, soils)
            else:
                print(f"Sequence failed for soil '{soil}' with return code: {result}")
                all_successful = False
            
            # Give the file system a brief moment to complete operations
            time.sleep(1)
        
        # Restore original maket.xml
        restore_original_maket_xml(simulation_path)
        
        # Verify all sequence folders have been renamed correctly
        check_and_fix_sequence_folders(sequence_dir_base, soils)
        
        # Print summary of where results are stored
        print("\n=== Simulation Complete ===")
        print(f"All soil sequence outputs are in: {sequence_dir_base}")
        print("Sequence folders are renamed to include soil names:")
        print("  Format: sequence_[soil_name]_[sequence_number]")
        
        return all_successful

def rename_sequence_folders(sequence_dir, soil_name, all_soils):
    """Rename sequence folders to include soil name"""
    if not os.path.exists(sequence_dir):
        return
    
    print(f"Looking for sequence folders to rename for soil: {soil_name}")
    renamed_count = 0
    
    for item in os.listdir(sequence_dir):
        # Find sequence folders that don't already have a soil name in them
        if item.startswith("sequence_") and not any(s in item for s in all_soils):
            old_path = os.path.join(sequence_dir, item)
            # Get the sequence number from the folder name
            parts = item.split("_")
            if len(parts) >= 2:
                seq_num = parts[-1]
                new_path = os.path.join(sequence_dir, f"sequence_{soil_name}_{seq_num}")
                
                if os.path.exists(new_path):
                    try:
                        shutil.rmtree(new_path)
                    except Exception as e:
                        print(f"Warning: Could not remove existing directory {new_path}: {str(e)}")
                        continue
                
                print(f"Renaming {old_path} to {new_path}")
                if not safe_rename_directory(old_path, new_path):
                    print(f"Warning: Failed to rename {old_path} to {new_path}")
                else:
                    renamed_count += 1
    
    print(f"Renamed {renamed_count} sequence folders for soil: {soil_name}")

def check_and_fix_sequence_folders(sequence_dir, all_soils):
    """Final check to ensure all sequence folders are properly named"""
    if not os.path.exists(sequence_dir):
        return
    
    # Check if any sequence folders remain without soil names
    unnamed_folders = []
    for item in os.listdir(sequence_dir):
        if item.startswith("sequence_") and not any(s in item for s in all_soils):
            unnamed_folders.append(item)
    
    if unnamed_folders:
        print(f"\nWARNING: Found {len(unnamed_folders)} sequence folders without soil names:")
        for folder in unnamed_folders:
            print(f"  - {folder}")
        print("These may be from the last soil run. Attempting to fix...")
        
        # Try to rename them with the last soil name
        if all_soils:
            last_soil = all_soils[-1]
            for folder in unnamed_folders:
                old_path = os.path.join(sequence_dir, folder)
                parts = folder.split("_")
                if len(parts) >= 2:
                    seq_num = parts[-1]
                    new_path = os.path.join(sequence_dir, f"sequence_{last_soil}_{seq_num}")
                    
                    if os.path.exists(new_path):
                        continue  # Skip if target already exists
                    
                    print(f"Fixing: Renaming {old_path} to {new_path}")
                    if not safe_rename_directory(old_path, new_path):
                        print(f"Warning: Failed to rename {old_path} to {new_path}")

def main():
    # Load configuration
    config = load_config()
    
    # Extract paths from config
    simulation_path = config['paths']['simulation_path']
    
    # Normalize path separators for Windows
    if sys.platform == 'win32':
        simulation_path = simulation_path.replace('/', '\\')
    
    # Get DART paths from simulation path
    dart_paths = get_dart_paths(simulation_path)
    DART_HOME = dart_paths['DART_HOME']
    DART_LOCAL = dart_paths['DART_LOCAL']
    DART_TOOLS = dart_paths['DART_TOOLS']
    
    # Check if the sequence file exists
    sequence_xml = os.path.join(simulation_path, "sequence.xml")
    if sys.platform == 'win32':
        sequence_xml = sequence_xml.replace('/', '\\')
    
    if not os.path.exists(sequence_xml):
        print(f"Error: Sequence file not found at {sequence_xml}")
        return
    
    # Check if the DART tools directory exists and contains the required script
    script_path = os.path.join(DART_TOOLS, "dart-sequence" + ('.bat' if sys.platform == 'win32' else '.sh'))
    if not os.path.exists(script_path):
        print(f"Error: Required script not found at {script_path}")
        return
    
    print(f"Running sequence from: {sequence_xml}")
    print(f"DART_HOME: {DART_HOME}")
    print(f"DART_LOCAL: {DART_LOCAL}")
    print(f"DART_TOOLS: {DART_TOOLS}")
    
    # Check if we should use multiple soils
    if config['simulation_settings']['multi_sol']:
        success = run_for_all_soils(config, simulation_path, DART_HOME, DART_LOCAL, DART_TOOLS)
    else:
        # First run the root simulation
        print("Running root simulation before executing sequence...")
        sim_result = run_simulation(simulation_path, DART_HOME, DART_LOCAL, DART_TOOLS)
        
        if sim_result != 0:
            print(f"Error: Root simulation failed with return code: {sim_result}")
            return
        
        print("Root simulation completed successfully. Proceeding with sequence...")
        
        # Now run the sequence
        result = run_sequence(sequence_xml, DART_HOME, DART_LOCAL, DART_TOOLS)
        
        success = (result == 0)
        if success:
            print("Sequence completed successfully")
        else:
            print(f"Sequence failed with return code: {result}")
    
    # Save results if configured and simulation was successful
    if config['simulation_settings']['save_result_to_tif_json']:
        # Use the saveTIFF.py script in the same directory
        save_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saveTIFF.py")
        print(f"Saving TIFF outputs using: {save_script_path}")
        try:
            # Import and run directly instead of using os.system
            from saveTIFF import save_tiff_and_props
            save_tiff_and_props()
            print("TIFF saving completed successfully")
        except Exception as e:
            print(f"Error saving TIFF outputs: {str(e)}")
            # Fall back to external script call if direct import fails
            os.system(f"python {save_script_path}")

if __name__ == "__main__":
    main()