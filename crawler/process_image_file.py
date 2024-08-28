import os
import shutil
import glob

# Define the root directory
root_dir = 'san-pham'
destination_dir = os.path.join(root_dir, 'san-pham')

# Create the destination directory if it doesn't exist
os.makedirs(destination_dir, exist_ok=True)

# Function to rename and copy images
def copy_and_rename_images():
    # Iterate over all files in subdirectories
    for subdir, _, _ in os.walk(root_dir):
        if subdir == destination_dir:
            continue  # Skip the destination directory itself
        # Get all image files in the current subdirectory
        for img_file in glob.glob(os.path.join(subdir, '*.*g')):  # Matches .png, .jpg, .jpeg, etc.
            # Generate the new filename
            relative_path = os.path.relpath(img_file, root_dir)  # Get relative path
            parts = relative_path.split(os.sep)  # Split into parts
            new_filename = '_'.join(parts)  # Join parts with '_'
            
            # Construct full path for the destination file
            new_filepath = os.path.join(destination_dir, new_filename)
            
            # Copy and rename the image
            shutil.copy(img_file, new_filepath)
            print(f"Copied and renamed: {img_file} -> {new_filepath}")

# Run the function
copy_and_rename_images()
