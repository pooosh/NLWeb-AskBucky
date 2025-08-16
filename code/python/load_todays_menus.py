#!/usr/bin/env python3
import subprocess
import sys
import os

def load_files_for_dining_hall(dining_hall, date="2025-08-05"):
    """Load all files for a specific dining hall for today"""
    site_name = f"menus_{date}"
    
    # Get all files for this dining hall and date
    pattern = f"../../data/jsonld/{dining_hall}_*{date}.jsonld"
    
    # Use find to get the list of files
    result = subprocess.run(['find', '../../data/jsonld', '-name', f'{dining_hall}_*{date}.jsonld'], 
                          capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error finding files for {dining_hall}: {result.stderr}")
        return False
    
    files = result.stdout.strip().split('\n')
    files = [f for f in files if f]  # Remove empty lines
    
    print(f"Found {len(files)} files for {dining_hall}")
    
    # Load each file
    for file_path in files:
        print(f"Loading {file_path}...")
        result = subprocess.run([
            'python', '-m', 'data_loading.db_load', 
            file_path, site_name
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ Successfully loaded {os.path.basename(file_path)}")
        else:
            print(f"✗ Failed to load {os.path.basename(file_path)}: {result.stderr}")
            return False
    
    return True

def main():
    print("Loading today's menus (2025-08-05)...")
    
    # Load Four Lakes Market
    print("\n=== Loading Four Lakes Market ===")
    if load_files_for_dining_hall("four-lakes-market"):
        print("✓ Successfully loaded all Four Lakes Market files")
    else:
        print("✗ Failed to load Four Lakes Market files")
        sys.exit(1)
    
    # Load Gordon Avenue Market
    print("\n=== Loading Gordon Avenue Market ===")
    if load_files_for_dining_hall("gordon-avenue-market"):
        print("✓ Successfully loaded all Gordon Avenue Market files")
    else:
        print("✗ Failed to load Gordon Avenue Market files")
        sys.exit(1)
    
    print("\n🎉 All today's menus loaded successfully!")

if __name__ == "__main__":
    main() 