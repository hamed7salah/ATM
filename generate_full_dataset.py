"""
Generate full ATM dataset (500 ATMs, 90 days) and save to CSV.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from atm_data_generator import ATMDataGenerator, GeneratorConfig

def main():
    print("="*70)
    print("ATM DATA GENERATOR - FULL DATASET")
    print("="*70)
    print()
    
    # Load default configuration (500 ATMs, 90 days)
    print("Loading configuration...")
    config = GeneratorConfig.from_json('atm_data_generator/config/default_config.json')
    
    print(f"Configuration loaded:")
    print(f"  - Number of ATMs: {config.num_atms}")
    print(f"  - Duration: {config.duration_days} days")
    print(f"  - Observation interval: {config.observation_interval_minutes} minutes")
    print(f"  - Random seed: {config.random_seed}")
    print(f"  - Output format: {config.output_format}")
    print(f"  - Output path: {config.output_path}")
    print()
    
    # Calculate expected data size
    total_observations = int((config.duration_days * 24 * 60) / config.observation_interval_minutes)
    total_rows = config.num_atms * total_observations
    print(f"Expected output:")
    print(f"  - Total time steps: {total_observations:,}")
    print(f"  - Total observations: {total_rows:,}")
    print(f"  - Estimated size: ~2-3 GB (CSV)")
    print()
    
    # Create generator
    print("Initializing generator...")
    generator = ATMDataGenerator(config)
    print(f"[OK] Generator initialized with {len(generator.atms)} ATMs")
    print()
    
    # Generate and save
    print("Starting data generation...")
    print("This will take approximately 10-15 minutes.")
    print()
    
    try:
        generator.generate_and_save()
        print()
        print("="*70)
        print("[SUCCESS] DATA GENERATION COMPLETE!")
        print("="*70)
        print()
        print(f"Output files saved to: {config.output_path}")
        print()
        print("Generated files:")
        print("  - sensor_observations.csv")
        print("  - failure_incidents.csv")
        print("  - maintenance_events.csv")
        print("  - metadata.json")
        print("  - data_dictionary.md")
        print()
        
    except Exception as e:
        print()
        print("="*70)
        print("[ERROR] ERROR DURING GENERATION")
        print("="*70)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
