#!/usr/bin/env python
"""
DART Simulation Preparation Script
---------------------------------
This script orchestrates the preparation of DART simulation by running
a sequence of specialized scripts to set up all required components.
"""

import os
import sys
import json
import time
import importlib
import subprocess

def load_config():
    """Load configuration from config.json file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    with open(config_path, 'r') as f:
        return json.load(f)

def run_script(script_name, module_name=None):
    """Run a script either by importing it or as a subprocess"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, script_name)
    
    print(f"\n{'='*80}\nRunning {script_name}...\n{'='*80}")
    
    if module_name and os.path.exists(script_path):
        try:
            # Try to import and run the module
            module = importlib.import_module(module_name)
            if hasattr(module, 'main'):
                module.main()
            else:
                #print(f"Warning: {script_name} doesn't have a main() function, running as script")
                if script_path.endswith('.py'):
                    subprocess.run([sys.executable, script_path], check=True)
                else:
                    subprocess.run([script_path], check=True)
            print(f"\n{script_name} completed successfully.\n")
            return True
        except Exception as e:
            print(f"Error importing {module_name}: {str(e)}")
            print(f"Trying to run as subprocess instead...")
    
    # Run as subprocess if import fails or module_name isn't provided
    try:
        if script_path.endswith('.py'):
            result = subprocess.run([sys.executable, script_path], check=False)
        else:
            result = subprocess.run([script_path], check=False)
        
        if result.returncode != 0:
            print(f"Warning: {script_name} returned non-zero exit code: {result.returncode}")
            return False
        
        print(f"\n{script_name} completed successfully.\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_name}: {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error running {script_name}: {str(e)}")
        return False

def check_prerequisites():
    """Check if all required scripts exist"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    required_scripts = [
        "update_coeff_diff.py", 
        "update_maket.py", 
        "update_objects.py", 
        "generate_sequence_from_config.py"
    ]
    
    missing_scripts = []
    for script in required_scripts:
        script_path = os.path.join(script_dir, script)
        if not os.path.exists(script_path):
            missing_scripts.append(script)
    
    if missing_scripts:
        print("Warning: The following required scripts are missing:")
        for script in missing_scripts:
            print(f"  - {script}")
        return False
    return True

def check_simulation_path(config):
    """Check if simulation path exists"""
    simulation_path = config['paths']['simulation_path']
    if not os.path.exists(simulation_path):
        print(f"Error: Simulation path not found: {simulation_path}")
        return False
    
    input_dir = os.path.join(simulation_path, "input")
    if not os.path.exists(input_dir):
        try:
            os.makedirs(input_dir)
            print(f"Created input directory: {input_dir}")
        except Exception as e:
            print(f"Error creating input directory: {str(e)}")
            return False
    
    return True

def main():
    start_time = time.time()
    print("\n=== DART Simulation Preparation ===\n")
    
    # Check if config.json exists
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found: {config_path}")
        return 1
    
    # Load configuration
    try:
        config = load_config()
        print("Configuration loaded successfully")
    except Exception as e:
        print(f"Error loading configuration: {str(e)}")
        return 1
    
    # Check prerequisites
    if not check_prerequisites():
        print("Warning: Some preparation scripts are missing.")
        response = input("Do you want to continue anyway? (y/n): ")
        if response.lower() != 'y':
            return 1
    
    # Check simulation path
    if not check_simulation_path(config):
        print("Error: Problem with simulation path.")
        return 1
    
    # Run each preparation script
    scripts_to_run = [
        ("update_coeff_diff.py", "update_coeff_diff"),
        ("update_maket.py", "update_maket"),
        ("update_objects.py", "update_objects"),
        ("generate_sequence_from_config.py", "generate_sequence_from_config")
    ]
    
    success = True
    for script, module in scripts_to_run:
        script_success = run_script(script, module)
        if not script_success:
            print(f"Warning: {script} did not complete successfully")
            success = False
    
    # Print summary
    duration = time.time() - start_time
    print(f"\n{'='*80}")
    print(f"Simulation preparation {'completed successfully' if success else 'completed with warnings/errors'}")
    print(f"Total preparation time: {int(duration // 60)} minutes {int(duration % 60)} seconds")
    print(f"{'='*80}\n")
    
    # Return appropriate exit code
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
