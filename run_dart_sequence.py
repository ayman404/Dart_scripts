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
    print(f"Original simulation path: {simulation_path}")
    
    # Handle mixed slashes by replacing all with the system separator
    simulation_path = simulation_path.replace('/', os.sep).replace('\\', os.sep)
    
    # Parse path based on whether it's a Windows path with drive letter
    if sys.platform == 'win32' and len(simulation_path) > 1 and simulation_path[1] == ':':
        # Windows path with drive letter (e.g., C:\Users\...)
        drive = simulation_path[:2]  # Just C: without the slash
        rest_of_path = simulation_path[2:].strip(os.sep)  # Remove leading and trailing slashes
        path_parts = rest_of_path.split(os.sep)
        path_parts = [p for p in path_parts if p]  # Remove empty strings
    else:
        # Unix-like path or path without drive letter
        drive = ""
        path_parts = simulation_path.strip(os.sep).split(os.sep)
        path_parts = [p for p in path_parts if p]  # Remove empty strings
    
    print(f"Path parts: {path_parts}")
    
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
        if drive:
            base_path = drive + os.sep + os.sep.join(path_parts[:dart_index+1])
        else:
            base_path = os.sep + os.sep.join(path_parts[:dart_index+1])
    
    if user_data_index == -1:
        # If we can't find user_data, use the base_path/user_data
        print("Warning: Could not find 'user_data' in the path. Using defaults.")
        user_data_path = os.path.join(base_path, "user_data")
    else:
        # Create the user_data path including the drive letter if on Windows
        if drive:
            user_data_path = drive + os.sep + os.sep.join(path_parts[:user_data_index+1])
        else:
            user_data_path = os.sep + os.sep.join(path_parts[:user_data_index+1])
    
    # For Windows, ensure the tool path points to windows directory
    tools_subpath = 'tools\\windows' if sys.platform == 'win32' else 'tools'
    
    print(f"DART_HOME: {base_path}")
    print(f"DART_LOCAL: {user_data_path}")
    print(f"DART_TOOLS: {os.path.join(base_path, tools_subpath)}")
    
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
        cmd = (['bash'] if sys.platform != 'win32' else []) + [step + ext, simulation.split(os.sep + 'simulations' + os.sep, 1)[-1]]
        print(f"Executing command: {cmd}")
        process = Popen(cmd, cwd=DART_TOOLS, env=env, stdout=log, stderr=STDOUT, shell=sys.platform == 'win32', universal_newlines=True)
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
    
    log = open('run.log', 'w')
    cmd = (['bash'] if sys.platform != 'win32' else []) + [os.path.join(DART_TOOLS, f"dart-sequence{ext}"), sequencexml, state]
    print(f"Executing sequence command: {cmd}")
    
    process = Popen(cmd, env=env, shell=False, stdin=subprocess.PIPE, universal_newlines=True)
    outs, errs = process.communicate(input="\n")  # Send newline to avoid waiting
    
    if errs:
        print(f"Errors: {errs}")
    print("Finished batch sequence")
    log.close()
    return 0 if process is None else process.returncode

def main():
    # Load configuration
    config = load_config()
    
    # Extract paths from config
    simulation_path = config['paths']['simulation_path']
    
    # Get DART paths from simulation path
    dart_paths = get_dart_paths(simulation_path)
    DART_HOME = dart_paths['DART_HOME']
    DART_LOCAL = dart_paths['DART_LOCAL']
    DART_TOOLS = dart_paths['DART_TOOLS']
    
    # Run the sequence
    print(f"Simulation path: {simulation_path}")
    # Use the full simulation path for sequence.xml
    sequence_xml = os.path.join(simulation_path, "sequence.xml")
    print(f"Sequence XML path: {sequence_xml}")
    if os.path.exists(sequence_xml):
        print(f"Running sequence from: {sequence_xml}")
        result = run_sequence(sequence_xml, DART_HOME, DART_LOCAL, DART_TOOLS)
        
        if result == 0:
            print("Sequence completed successfully")
            
            # Save results if configured
            if config['simulation_settings']['save_result_to_tif_json']:
                save_script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "saveTIFF.py")
                os.system(f"python {save_script_path} {rd.random()}")
        else:
            print(f"Sequence failed with return code: {result}")
    else:
        print(f"Error: Sequence file not found at {sequence_xml}")

if __name__ == "__main__":
    main() 