"""
Configuration system for ATM data generator.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json


@dataclass
class FailureRates:
    """Failure rates per ATM per year by failure type."""
    network: float = 2.0
    power: float = 1.5
    thermal: float = 1.0
    dispenser: float = 3.0
    card_reader: float = 2.5
    printer: float = 2.0
    software: float = 1.5
    hardware: float = 1.0


@dataclass
class SensorNoiseConfig:
    """Configuration for sensor noise and measurement errors."""
    temperature_std: float = 1.5  # °C
    voltage_std: float = 2.0  # V
    signal_strength_std: float = 3.0  # dBm
    latency_std: float = 5.0  # ms
    missing_rate: float = 0.02  # 2% missing readings


@dataclass
class EnvironmentalConfig:
    """Environmental conditions configuration."""
    # Temperature ranges (°C)
    ambient_temp_mean: float = 28.0
    ambient_temp_std: float = 5.0
    ambient_temp_min: float = 15.0
    ambient_temp_max: float = 45.0
    
    # Daily temperature variation
    daily_temp_amplitude: float = 8.0
    
    # Power stability (Egypt-specific)
    voltage_nominal: float = 220.0
    voltage_variation_std: float = 5.0
    power_spike_rate: float = 0.1  # per day
    
    # Network conditions
    network_signal_mean: float = -65.0  # dBm
    network_signal_std: float = 10.0


@dataclass
class MaintenanceConfig:
    """Maintenance and repair configuration."""
    # Repair times in hours
    flm_repair_time_mean: float = 2.0  # First Line Maintenance
    flm_repair_time_std: float = 0.5
    
    slm_repair_time_mean: float = 8.0  # Second Line Maintenance
    slm_repair_time_std: float = 2.0
    
    # Maintenance scheduling
    preventive_maintenance_interval_days: float = 90.0
    preventive_maintenance_duration_hours: float = 1.5


@dataclass
class GeneratorConfig:
    """Main configuration for ATM data generator."""
    
    # Simulation parameters
    num_atms: int = 500
    duration_days: int = 90
    observation_interval_minutes: int = 5
    random_seed: Optional[int] = 42
    
    # ATM fleet composition
    atm_age_range: tuple = (0, 10)  # years
    indoor_ratio: float = 0.6  # 60% indoor, 40% outdoor
    
    # Failure configuration
    failure_rates: FailureRates = field(default_factory=FailureRates)
    
    # Sensor noise
    sensor_noise: SensorNoiseConfig = field(default_factory=SensorNoiseConfig)
    
    # Environmental conditions
    environment: EnvironmentalConfig = field(default_factory=EnvironmentalConfig)
    
    # Maintenance
    maintenance: MaintenanceConfig = field(default_factory=MaintenanceConfig)
    
    # Transaction patterns
    daily_transaction_mean: float = 150.0
    daily_transaction_std: float = 50.0
    peak_hours: List[int] = field(default_factory=lambda: [10, 11, 12, 13, 14, 17, 18, 19])
    
    # State transition probabilities
    healthy_to_degrading_prob: float = 0.001  # per observation
    degrading_to_warning_prob: float = 0.05
    degrading_to_healthy_prob: float = 0.02  # recovery without failure
    warning_to_failed_prob: float = 0.3
    warning_to_degrading_prob: float = 0.1  # step back
    
    # Sudden failure probability (no warning)
    sudden_failure_prob: float = 0.2  # 20% of failures are sudden
    
    # Output configuration
    output_format: str = 'csv'  # 'csv' or 'parquet'
    output_path: str = './data/output'
    compress: bool = True
    
    @classmethod
    def from_json(cls, filepath: str) -> 'GeneratorConfig':
        """Load configuration from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Handle nested dataclasses
        if 'failure_rates' in data:
            data['failure_rates'] = FailureRates(**data['failure_rates'])
        if 'sensor_noise' in data:
            data['sensor_noise'] = SensorNoiseConfig(**data['sensor_noise'])
        if 'environment' in data:
            data['environment'] = EnvironmentalConfig(**data['environment'])
        if 'maintenance' in data:
            data['maintenance'] = MaintenanceConfig(**data['maintenance'])
        
        return cls(**data)
    
    def to_json(self, filepath: str):
        """Save configuration to JSON file."""
        def convert_to_dict(obj):
            if hasattr(obj, '__dict__'):
                return {k: convert_to_dict(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_to_dict(item) for item in obj]
            else:
                return obj
        
        data = convert_to_dict(self)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_smoke_test_config(self) -> 'GeneratorConfig':
        """Return a small configuration for quick testing."""
        config = GeneratorConfig(
            num_atms=10,
            duration_days=7,
            observation_interval_minutes=5,
            random_seed=42,
            output_path='./data/output/smoke_test'
        )
        return config
