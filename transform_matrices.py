import os
import numpy as np
import argparse
import shutil
import json

def load_config():
    """Load configuration from config.json file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    with open(config_path, 'r') as f:
        return json.load(f)

def read_matrix_from_file(file_path):
    """Read a matrix from a text file."""
    try:
        return np.loadtxt(file_path)
    except Exception as e:
        print(f"Error reading matrix from {file_path}: {e}")
        return None

def save_matrix_to_file(matrix, file_path):
    """Save a matrix to a text file with the same format."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Save with the same format as the original
        np.savetxt(file_path, matrix, fmt='%.6f')
        return True
    except Exception as e:
        print(f"Error saving matrix to {file_path}: {e}")
        return False

def mirror_horizontal(matrix):
    """Mirror a matrix horizontally (flip left-right)."""
    return np.fliplr(matrix)

def mirror_vertical(matrix):
    """Mirror a matrix vertically (flip up-down)."""
    return np.flipud(matrix)

def rotate_180(matrix):
    """Rotate a matrix 180 degrees."""
    return np.rot90(matrix, 2)  # Rotate twice by 90 degrees

def scale_matrix(matrix, factor=1.2):
    """Multiply all values in the matrix by a factor."""
    return matrix * factor

def create_transformed_folders(source_folder):
    """Create mirrored and rotated versions of the source folder."""
    print(f"Creating transformed versions of folder: {source_folder}")
    
    # Create destination folders
    mirror_h_folder = f"{source_folder}_mirror_h"
    mirror_v_folder = f"{source_folder}_mirror_v"
    rotate_folder = f"{source_folder}_rotate_180"
    
    # Ensure destination folders exist
    for folder in [mirror_h_folder, mirror_v_folder, rotate_folder]:
        os.makedirs(folder, exist_ok=True)
        print(f"Created output folder: {folder}")
    
    # Find all txt files in the source folder
    txt_files = []
    for root, _, files in os.walk(source_folder):
        for file in files:
            if file.endswith('.txt'):
                txt_files.append(os.path.join(root, file))
    
    print(f"Found {len(txt_files)} txt files to process")
    
    # Process each file
    for file_path in txt_files:
        # Get relative path to maintain subfolder structure
        rel_path = os.path.relpath(file_path, source_folder)
        
        # Read the matrix
        matrix = read_matrix_from_file(file_path)
        if matrix is None:
            continue
        
        # Generate transformed matrices
        matrix_h = mirror_horizontal(matrix)
        matrix_v = mirror_vertical(matrix)
        matrix_r = rotate_180(matrix)
        
        # Save transformed matrices
        save_matrix_to_file(matrix_h, os.path.join(mirror_h_folder, rel_path))
        save_matrix_to_file(matrix_v, os.path.join(mirror_v_folder, rel_path))
        save_matrix_to_file(matrix_r, os.path.join(rotate_folder, rel_path))
    
    print(f"Completed creating transformed versions of {len(txt_files)} files in {source_folder}")
    
    # Return the paths of newly created folders
    return [mirror_h_folder, mirror_v_folder, rotate_folder]

def scale_folder(source_folder, factor=1.2):
    """Create a scaled version of the source folder."""
    print(f"Creating scaled version (x{factor}) of folder: {source_folder}")
    
    # Create destination folder
    scale_folder = f"{source_folder}_scaled_{factor}"
    os.makedirs(scale_folder, exist_ok=True)
    
    # Find all txt files in the source folder
    txt_files = []
    for root, _, files in os.walk(source_folder):
        for file in files:
            if file.endswith('.txt'):
                txt_files.append(os.path.join(root, file))
    
    print(f"Found {len(txt_files)} txt files to scale")
    
    # Process each file
    for file_path in txt_files:
        # Get relative path to maintain subfolder structure
        rel_path = os.path.relpath(file_path, source_folder)
        
        # Read the matrix
        matrix = read_matrix_from_file(file_path)
        if matrix is None:
            continue
        
        # Scale the matrix
        matrix_s = scale_matrix(matrix, factor)
        
        # Save scaled matrix
        save_matrix_to_file(matrix_s, os.path.join(scale_folder, rel_path))
    
    print(f"Completed scaling {len(txt_files)} files in {source_folder}")
    return scale_folder

def process_root_folder(root_folder):
    """Process all immediate subfolders in the root folder."""
    # Get all immediate subfolders
    subfolders = [f.path for f in os.scandir(root_folder) if f.is_dir()]
    
    if not subfolders:
        print(f"No subfolders found in {root_folder}")
        return
    
    print(f"Found {len(subfolders)} subfolders to process")
    
    # First, create mirrored and rotated versions for each subfolder
    all_folders = list(subfolders)  # Start with original folders
    
    for folder in subfolders:
        # Create transformed versions
        transformed_folders = create_transformed_folders(folder)
        all_folders.extend(transformed_folders)
    
    print(f"Created transformed versions. Total folders: {len(all_folders)}")
    
    # Now, scale all folders (original + transformed)
    for folder in all_folders:
        scale_folder(folder)
    
    print(f"All folders processed and scaled successfully")

def main():
    # Support both command-line argument and config.json
    parser = argparse.ArgumentParser(description='Transform matrix files in multiple folders.')
    parser.add_argument('--root_folder', help='Path to the root folder containing subfolders with matrix files (optional)')
    args = parser.parse_args()
    
    # If root_folder is provided as an argument, use it
    if args.root_folder and os.path.isdir(args.root_folder):
        root_folder = args.root_folder
    else:
        # Otherwise, try to get it from config.json
        try:
            config = load_config()
            if 'paths' in config and 'soil_factor_path' in config['paths']:
                root_folder = config['paths']['soil_factor_path']
                print(f"Using soil_factor_path from config: {root_folder}")
            else:
                print("soil_factor_path not found in config.json")
                return
        except Exception as e:
            print(f"Error loading config: {e}")
            print("Please provide a root folder path as an argument")
            return
    
    if not os.path.isdir(root_folder):
        print(f"Error: {root_folder} is not a valid directory")
        return
    root_folder = os.path.abspath("../Aymen/soldart_bandes")
    process_root_folder(root_folder)
    print("Matrix transformation complete!")

if __name__ == "__main__":
    main()
