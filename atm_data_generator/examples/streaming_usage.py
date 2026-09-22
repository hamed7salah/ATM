"""
Example: Streaming mode usage
"""

from atm_data_generator import ATMDataGenerator, GeneratorConfig
import pandas as pd

# Create configuration for streaming
config = GeneratorConfig(
    num_atms=50,
    duration_days=7,
    observation_interval_minutes=5,
    random_seed=42
)

generator = ATMDataGenerator(config)

print("Streaming ATM telemetry data...")
print(f"Simulating {config.num_atms} ATMs for {config.duration_days} days\n")

# Example: Process data in real-time
observations_buffer = []
failure_count = 0

for timestamp, observations in generator.stream():
    # Add to buffer
    observations_buffer.extend(observations)
    
    # Check for failures
    for obs in observations:
        if obs['operational_status'] == 'out_of_service':
            failure_count += 1
    
    # Process every 1000 observations (example)
    if len(observations_buffer) >= 1000:
        # Convert to DataFrame and process
        df = pd.DataFrame(observations_buffer)
        
        # Example processing: Calculate average temperature
        avg_temp = df['temperature_cabinet_temp_c'].mean()
        print(f"[{timestamp}] Processed {len(observations_buffer)} observations")
        print(f"  Average cabinet temperature: {avg_temp:.1f}°C")
        print(f"  Total failures detected: {failure_count}")
        print()
        
        # Clear buffer
        observations_buffer = []

# Process remaining observations
if observations_buffer:
    df = pd.DataFrame(observations_buffer)
    print(f"Final batch: {len(observations_buffer)} observations")

print(f"\nStreaming complete!")
print(f"Total failures: {failure_count}")
