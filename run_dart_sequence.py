import os
import sys
import json
from subprocess import Popen, STDOUT
import subprocess
import random as rd

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
        # If we can't find DART, let's use reasonable defaults
        print("Warning: Could not find 'DART' in the path. Using defaults.")
        if sys.platform == 'win32':
            base_path = "C:\\Users\\LENOVO\\DART"
        else:
            base_path = "/Users/LENOVO/DART"
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
        tools_subpath = os.path.join('tools', 'linux')
    
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
        process = Popen(cmd, cwd=DART_TOOLS, env=env, stdout=log, stderr=STDOUT, shell=False, universal_newlines=True)
        if process.wait() > 0:
            break
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
    #print(f"Working directory: {DART_TOOLS}")
    #print(f"Environment variables: DART_HOME={DART_HOME}, DART_LOCAL={DART_LOCAL}")
    
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
    
    # Run the sequence
    # Use the full simulation path for sequence.xml
    sequence_xml = os.path.join(simulation_path, "sequence.xml")
    
    # Ensure consistent path separators
    if sys.platform == 'win32':
        sequence_xml = sequence_xml.replace('/', '\\')
    
    if os.path.exists(sequence_xml):
        #print(f"Running sequence from: {sequence_xml}")
        #print(f"DART_HOME: {DART_HOME}")
        #print(f"DART_LOCAL: {DART_LOCAL}")
        #print(f"DART_TOOLS: {DART_TOOLS}")
        result = run_sequence(sequence_xml, DART_HOME, DART_LOCAL, DART_TOOLS)
        

        # Save results if configured
        if config['simulation_settings']['save_result_to_tif_json']:
                save_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saveTIFF.py")
                print(f"Running save script: {save_script_path}")
                os.system(f"python {save_script_path} {rd.random()}")

    else:
        print(f"Error: Sequence file not found at {sequence_xml}")

if __name__ == "__main__":
    main() 