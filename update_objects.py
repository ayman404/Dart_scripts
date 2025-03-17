import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import json
import os
import random

def read_positions_file(filename):
    positions = []
    with open(filename, 'r') as f:
        for line in f:
            # Skip comments and empty lines
            if line.startswith('//') or line.strip() == '' or line.strip() == 'complete transformation':
                continue
            # Parse the line into values
            values = line.strip().split()
            if len(values) == 10:  # Ensure we have all 10 values
                positions.append({
                    'index': int(values[0]),
                    'xpos': float(values[1]),
                    'ypos': float(values[2]),
                    'zpos': float(values[3]),
                    'xscale': float(values[4]),
                    'yscale': float(values[5]),
                    'zscale': float(values[6]),
                    'xrot': float(values[7]),
                    'yrot': float(values[8]),
                    'zrot': float(values[9])
                })
    return positions

def get_obj_files(tree_obj_path):
    """Get all .obj files from the tree_obj_path"""
    obj_files = []
    for root, _, files in os.walk(tree_obj_path):
        for file in files:
            if file.endswith('.obj'):
                obj_files.append(os.path.join(root, file))
    return obj_files

def create_base_xml():
    # Create the root structure
    root = ET.Element("DartFile")
    root.set("build", "v1410")
    root.set("version", "5.10.6")
    
    # Create object_3d element
    object_3d = ET.SubElement(root, "object_3d")
    object_3d.set("generateTriangleFileXML", "0")
    
    # Create Types section
    types = ET.SubElement(object_3d, "Types")
    default_types = ET.SubElement(types, "DefaultTypes")
    
    # Add default types
    default_type_data = [
        ("101", "Default_Object", "255 0 0"),
        ("102", "Leaf", "0 175 0"),
        ("103", "Trunk", "71 55 25")
    ]
    
    for index, name, color in default_type_data:
        default_type = ET.SubElement(default_types, "DefaultType")
        default_type.set("indexOT", index)
        default_type.set("name", name)
        default_type.set("typeColor", color)
    
    ET.SubElement(types, "CustomTypes")
    
    # Create ObjectList
    object_list = ET.SubElement(object_3d, "ObjectList")
    
    return root, object_list

def create_object(position_data, object_index, obj_file_path, use_individual_temps, use_individual_optical):
    obj = ET.Element("Object")
    obj.set("file_src", obj_file_path)
    obj.set("hasGroups", "1")
    obj.set("hidden", "0")
    obj.set("hideRB", "0")
    obj.set("isDisplayed", "1")
    obj.set("name", "Object")
    obj.set("num", str(object_index))
    obj.set("objectColor", "125 0 125")
    obj.set("objectDEMMode", "0")
    obj.set("repeatedOnBorder", "1")
    
    # Geometric Properties
    geo_props = ET.SubElement(obj, "GeometricProperties")
    
    pos_props = ET.SubElement(geo_props, "PositionProperties")
    pos_props.set("xpos", str(position_data['xpos']))
    pos_props.set("ypos", str(position_data['ypos']))
    pos_props.set("zpos", str(position_data['zpos']))
    
    dim_3d = ET.SubElement(geo_props, "Dimension3D")
    dim_3d.set("xdim", "9.32332992553711")
    dim_3d.set("ydim", "9.625602722167969")
    dim_3d.set("zdim", "6.392255189130083")
    
    center_3d = ET.SubElement(geo_props, "Center3D")
    center_3d.set("xCenter", "-0.15236902236938477")
    center_3d.set("yCenter", "-0.17827844619750977")
    center_3d.set("zCenter", "3.1936185945523903")
    
    scale_props = ET.SubElement(geo_props, "ScaleProperties")
    scale_props.set("xScaleDeviation", "0.0")
    scale_props.set("xscale", str(position_data['xscale']))
    scale_props.set("yScaleDeviation", "0.0")
    scale_props.set("yscale", str(position_data['yscale']))
    scale_props.set("zScaleDeviation", "0.0")
    scale_props.set("zscale", str(position_data['zscale']))
    
    rot_props = ET.SubElement(geo_props, "RotationProperties")
    rot_props.set("xRotDeviation", "0.0")
    rot_props.set("xrot", str(position_data['xrot']))
    rot_props.set("yRotDeviation", "0.0")
    rot_props.set("yrot", str(position_data['yrot']))
    rot_props.set("zRotDeviation", "0.0")
    rot_props.set("zrot", str(position_data['zrot']))
    
    # Add other properties
    obj_optical = ET.SubElement(obj, "ObjectOpticalProperties")
    obj_optical.set("isLAICalc", "0")
    obj_optical.set("isSingleGlobalLai", "0")
    obj_optical.set("sameExitanceObject", "0")
    obj_optical.set("sameOPObject", "0")
    obj_optical.set("transparent", "0")
    
    obj_type = ET.SubElement(obj, "ObjectTypeProperties")
    obj_type.set("sameOTObject", "0")
    
    # Add Groups
    groups = ET.SubElement(obj, "Groups")
    
    # Leaves Group
    leaves = ET.SubElement(groups, "Group")
    leaves.set("groupDEMMode", "0")
    leaves.set("hidden", "0")
    leaves.set("hideRB", "0")
    leaves.set("isLAICalc", "0")
    leaves.set("name", "Leaves")
    leaves.set("num", "1")
    leaves.set("transparent", "0")
    
    leaves_op = ET.SubElement(leaves, "GroupOpticalProperties")
    leaves_sop = ET.SubElement(leaves_op, "SurfaceOpticalProperties")
    leaves_sop.set("doubleFace", "0")
    
    leaves_opl = ET.SubElement(leaves_sop, "OpticalPropertyLink")
    # Set optical property based on configuration
    if use_individual_optical:
        leaves_opl.set("ident", f"leaf_{object_index}")
    else:
        leaves_opl.set("ident", "leaf_0")
    leaves_opl.set("indexFctPhase", "0")
    leaves_opl.set("type", "0")
    
    leaves_sep = ET.SubElement(leaves_op, "SurfaceExitanceProperties")
    leaves_sep.set("doubleFace", "0")
    leaves_sep.set("useTemperaturePerTriangle", "0")
    
    leaves_tpl = ET.SubElement(leaves_sep, "ThermalPropertyLink")
    # Set temperature property based on configuration
    if use_individual_temps:
        leaves_tpl.set("idTemperature", f"Temp_leaf_{object_index}")
    else:
        leaves_tpl.set("idTemperature", "Temperature_290_310")
    leaves_tpl.set("indexTemperature", "0")
    
    leaves_gtp = ET.SubElement(leaves, "GroupTypeProperties")
    leaves_otl = ET.SubElement(leaves_gtp, "ObjectTypeLink")
    leaves_otl.set("identOType", "Leaf")
    leaves_otl.set("indexOT", "102")
    
    # Trunk Group
    trunk = ET.SubElement(groups, "Group")
    trunk.set("groupDEMMode", "0")
    trunk.set("hidden", "0")
    trunk.set("hideRB", "0")
    trunk.set("isLAICalc", "0")
    trunk.set("name", "Trunk")
    trunk.set("num", "2")
    trunk.set("transparent", "0")
    
    trunk_op = ET.SubElement(trunk, "GroupOpticalProperties")
    trunk_sop = ET.SubElement(trunk_op, "SurfaceOpticalProperties")
    trunk_sop.set("doubleFace", "0")
    
    trunk_opl = ET.SubElement(trunk_sop, "OpticalPropertyLink")
    trunk_opl.set("ident", "trunk")
    trunk_opl.set("indexFctPhase", "1")
    trunk_opl.set("type", "0")
    
    trunk_sep = ET.SubElement(trunk_op, "SurfaceExitanceProperties")
    trunk_sep.set("doubleFace", "0")
    trunk_sep.set("useTemperaturePerTriangle", "0")
    
    trunk_tpl = ET.SubElement(trunk_sep, "ThermalPropertyLink")
    if use_individual_temps:
        trunk_tpl.set("idTemperature", f"Temp_trunk_{object_index}")
    else:
        trunk_tpl.set("idTemperature", "Temperature_290_310")
    trunk_tpl.set("indexTemperature", "0")
    
    trunk_gtp = ET.SubElement(trunk, "GroupTypeProperties")
    trunk_otl = ET.SubElement(trunk_gtp, "ObjectTypeLink")
    trunk_otl.set("identOType", "Trunk")
    trunk_otl.set("indexOT", "103")
    
    return obj

def update_object_3d_xml(config_path):
    # Read configuration
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Get paths and settings
    position_file = config['paths']['position_txt_path']
    simulation_path = config['paths']['simulation_path']
    tree_obj_path = config['paths']['tree_obj_path']
    settings = config['simulation_settings']
    params_to_vary = config['parameters_to_vary']
    
    # Read positions
    positions = read_positions_file(position_file)
    if not positions:
        print("No tree positions found!")
        return
    
    # Get available obj files
    obj_files = get_obj_files(tree_obj_path)
    if not obj_files:
        print(f"No .obj files found in {tree_obj_path}")
        return
    
    # Select obj file based on multi_tree setting
    if not settings['multi_tree']:
        obj_files = [obj_files[0]]  # Use only the first obj file
    
    # Create base XML structure
    root, object_list = create_base_xml()
    
    # Add objects for each position
    for i, pos in enumerate(positions):
        # Select random obj file if multi_tree is true, otherwise use the single file
        obj_file = random.choice(obj_files) if settings['multi_tree'] else obj_files[0]
        
        # Create object with appropriate settings
        use_individual_temps = params_to_vary['tree_temperature']
        use_individual_optical = params_to_vary['chlorophyl'] or params_to_vary['water_thickness']
        
        object_list.append(create_object(pos, i, obj_file, use_individual_temps, use_individual_optical))
    
    # Add ObjectFields
    ET.SubElement(root.find('object_3d'), "ObjectFields")
    
    # Create the XML string with proper formatting
    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")
    
    # Remove any empty lines and write to file
    output_path = os.path.join(simulation_path, "input", "object_3d.xml")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('\n'.join(line for line in xml_str.split('\n') if line.strip()))
    
    print(f"Updated object_3d.xml has been generated at: {output_path}")

if __name__ == "__main__":
    config_path = "config.json"
    update_object_3d_xml(config_path) 