DART Scripts Documentation
=======================

This folder contains scripts for updating DART simulation files based on configuration settings. The main scripts are:
1. update_coeff_diff.py - Updates optical and thermal properties
2. update_objects.py - Updates 3D object configurations

Installation
-----------
These scripts require several Python packages to run properly. To install all dependencies:

1. Make sure you have Python 3.7+ installed
2. Install the required packages using pip:
   ```
   pip install -r requirements.txt
   ```

3. For rasterio and GDAL installation troubleshooting:
   - Windows users may need to install from wheels: https://www.lfd.uci.edu/~gohlke/pythonlibs/
   - Linux/Mac users might need additional system dependencies:
     ```
     # For Ubuntu/Debian
     sudo apt-get install libgdal-dev
     
     # For Mac (using Homebrew)
     brew install gdal
     ```

4. Verify installation by running a simple test:
   ```
   python -c "import rasterio; import numpy; print('Installation successful!')"
   ```

Configuration (config.json)
--------------------------
The scripts use a shared configuration file (config.json) with the following structure:

{
    "paths": {
        "simulation_path": "Path to DART simulation directory",
        "position_txt_path": "Path to position.txt file",
        "tree_obj_path": "Path to directory containing tree .obj files"
    },
    "simulation_settings": {
        "multi_sol": false,
        "multi_tree": false,
        "run_sequencer": true
    },
    "parameters_to_vary": {
        "scale": false,
        "tree_temperature": false,
        "chlorophyl": false,
        "water_thickness": false,
        "soil_temperature": false
    }
}

Input Files
-----------
1. position.txt:
   - Contains tree positions and transformations
   - Format: index X Y Z Xscale Yscale Zscale Xrot Yrot Zrot
   - Each line represents one tree's position and transformation
   - Number of lines determines the number of trees (N)

2. Tree .obj files:
   - Located in tree_obj_path
   - Used for 3D tree models
   - If multi_tree=true: randomly selects different models for each tree
   - If multi_tree=false: uses the first .obj file for all trees

Workflow
--------
1. update_coeff_diff.py:
   - Reads number of trees (N) from position.txt
   - Creates coeff_diff.xml in simulation_path/input/
   - Handles optical and thermal properties:
     a. If tree_temperature=true:
        - Creates N leaf temperatures (Temp_leaf_0 to Temp_leaf_N-1)
        - Creates N trunk temperatures (Temp_trunk_0 to Temp_trunk_N-1)
     b. If tree_temperature=false:
        - Creates single temperature range (Temperature_290_310)
     c. Always adds Temp_soil
     d. If chlorophyl or water_thickness=true:
        - Creates N leaf optical properties (leaf_0 to leaf_N-1)
     e. Always adds trunk optical property

2. update_objects.py:
   - Reads tree positions from position.txt
   - Creates object_3d.xml in simulation_path/input/
   - For each tree position:
     a. Selects .obj file:
        - If multi_tree=true: random selection
        - If multi_tree=false: uses first file
     b. Creates object with:
        - Position and transformation from position.txt
        - Groups for leaves and trunk
        - Links to optical properties:
          * If chlorophyl/water_thickness=true: leaf_0 to leaf_N-1
          * If false: leaf_0 for all
          * Always "trunk" for trunk
        - Links to thermal properties:
          * If tree_temperature=true: individual temperatures
          * If false: Temperature_290_310 for all

Output Files
-----------
1. coeff_diff.xml:
   - Located in: simulation_path/input/
   - Contains:
     * Optical properties for leaves and trunk
     * Thermal properties for all components
     * Surface and volume properties

2. object_3d.xml:
   - Located in: simulation_path/input/
   - Contains:
     * 3D object definitions
     * Tree positions and transformations
     * Links to optical and thermal properties
     * Group definitions for leaves and trunk

Usage
-----
1. Ensure config.json is properly configured
2. Run update_coeff_diff.py to generate optical and thermal properties
3. Run update_objects.py to generate 3D object configurations

Both scripts can be run independently but typically should be run in sequence as the object definitions reference the properties defined in coeff_diff.xml.