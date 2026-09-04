import sys
import os

# Ensure the root of the project is in the Python path
current_dir = "core_logic/generatePalette"
root_dir = os.path.dirname(os.path.dirname(current_dir))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from core_logic.generatePalette.palette_generator import PaletteGenerator

def main():
    print("Forcing generation of high-quality CIEDE2000 candidate cache...")
    print("This will take approximately 15-20 minutes.")
    
    # Passing use_cache=False forces a complete recalculation
    gen = PaletteGenerator(use_cache=False)
    
    print("\nSaving the cache to disk...")
    # Manually save since we passed use_cache=False
    gen._save_cached_candidates()
    
    print("Cache generation complete and saved successfully!")

if __name__ == '__main__':
    main()
