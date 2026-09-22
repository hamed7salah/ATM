"""
Example: Basic usage of ATM data generator
"""

from atm_data_generator import ATMDataGenerator, GeneratorConfig

# Example 1: Use default configuration
print("Example 1: Default configuration")
config = GeneratorConfig()
generator = ATMDataGenerator(config)

# Generate and save data
generator.generate_and_save(output_format='csv', output_path='./data/output/example1')

print("\n" + "="*50 + "\n")

# Example 2: Load configuration from JSON
print("Example 2: Load from JSON config")
config = GeneratorConfig.from_json('atm_data_generator/config/default_config.json')
generator = ATMDataGenerator(config)
generator.generate_and_save()

print("\n" + "="*50 + "\n")

# Example 3: Smoke test (quick test with small dataset)
print("Example 3: Smoke test")
config = GeneratorConfig.from_json('atm_data_generator/config/smoke_test_config.json')
generator = ATMDataGenerator(config)
generator.generate_and_save()

print("\n" + "="*50 + "\n")

# Example 4: Custom configuration
print("Example 4: Custom configuration")
config = GeneratorConfig(
    num_atms=100,
    duration_days=30,
    observation_interval_minutes=5,
    random_seed=123,
    output_format='parquet',
    output_path='./data/output/custom'
)
generator = ATMDataGenerator(config)
generator.generate_and_save()
