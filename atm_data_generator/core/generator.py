"""
Main ATM data generator with streaming and export capabilities.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Iterator, Dict, Any, List, Optional
from pathlib import Path
import json

from .config import GeneratorConfig
from .state_machine import ATMStateMachine, ATMState, FailureEvent, FailureType
from ..sensors.simulators import (
    NetworkSensorSimulator,
    PowerSensorSimulator,
    TemperatureSensorSimulator,
    DispenserSensorSimulator,
    CardReaderSensorSimulator,
    PrinterSensorSimulator,
    SoftwareSensorSimulator,
    MonitoringSensorSimulator
)


class ATMDataGenerator:
    """
    Main ATM telemetry data generator with streaming and batch export capabilities.
    
    Usage:
        # Streaming mode
        generator = ATMDataGenerator(config)
        for timestamp, atm_data in generator.stream():
            process(atm_data)
        
        # Batch mode
        generator.generate_and_save(output_format='csv')
    """
    
    def __init__(self, config: GeneratorConfig):
        self.config = config
        
        # Set random seed for reproducibility
        if config.random_seed is not None:
            np.random.seed(config.random_seed)
            self.rng = np.random.RandomState(config.random_seed)
        else:
            self.rng = np.random.RandomState()
        
        # Initialize ATMs
        self.atms: Dict[str, ATMStateMachine] = {}
        self._initialize_atms()
        
        # Initialize sensor simulators
        self.sensor_simulators = {
            'network': NetworkSensorSimulator(config, self.rng),
            'power': PowerSensorSimulator(config, self.rng),
            'temperature': TemperatureSensorSimulator(config, self.rng),
            'dispenser': DispenserSensorSimulator(config, self.rng),
            'card_reader': CardReaderSensorSimulator(config, self.rng),
            'printer': PrinterSensorSimulator(config, self.rng),
            'software': SoftwareSensorSimulator(config, self.rng),
            'monitoring': MonitoringSensorSimulator(config, self.rng),
        }
        
        # Storage for events
        self.failure_events: List[FailureEvent] = []
        self.maintenance_events: List[Dict] = []
        
        # Simulation state
        self.start_time = datetime(2026, 1, 1, 0, 0, 0)
        self.current_time = self.start_time
    
    def _initialize_atms(self):
        """Initialize ATM fleet with diverse characteristics."""
        for i in range(self.config.num_atms):
            atm_id = f"ATM_{i+1:04d}"
            
            # Create independent random state for each ATM
            atm_seed = self.config.random_seed + i if self.config.random_seed else None
            atm_rng = np.random.RandomState(atm_seed)
            
            # Create state machine
            self.atms[atm_id] = ATMStateMachine(atm_id, self.config, atm_rng)
    
    def stream(self, duration_days: Optional[int] = None) -> Iterator[tuple[datetime, List[Dict[str, Any]]]]:
        """
        Stream generated data in real-time simulation mode.
        
        Yields:
            (timestamp, list of ATM observations)
        """
        if duration_days is None:
            duration_days = self.config.duration_days
        
        total_observations = int((duration_days * 24 * 60) / self.config.observation_interval_minutes)
        
        for obs_idx in range(total_observations):
            self.current_time = self.start_time + timedelta(
                minutes=obs_idx * self.config.observation_interval_minutes
            )
            
            observations = []
            
            for atm_id, atm in self.atms.items():
                # Update state machine
                state, new_failure = atm.update(self.current_time)
                
                # Record failure event
                if new_failure:
                    self.failure_events.append(new_failure)
                
                # Generate sensor readings
                observation = self._generate_observation(atm_id, atm, self.current_time)
                observations.append(observation)
            
            yield self.current_time, observations
    
    def _generate_observation(self, atm_id: str, atm: ATMStateMachine, 
                             timestamp: datetime) -> Dict[str, Any]:
        """Generate a complete observation for one ATM at one timestamp."""
        
        state = atm.current_state
        degradation = atm.get_degradation_level()
        
        # Get failure type if currently failed
        failure_type = None
        if atm.current_failure:
            failure_type = atm.current_failure.failure_type.value
        
        # Base observation
        observation = {
            'timestamp': timestamp,
            'atm_id': atm_id,
            'operational_status': 'operational' if atm.is_operational() else 'out_of_service',
            'state': state.value,  # Hidden state (not for model features)
            'degradation_level': degradation,  # Hidden (not for model features)
        }
        
        # Generate sensor readings from all simulators
        sensor_kwargs = {
            'failure_type': failure_type,
            'transaction_count': 0,  # Will be set by monitoring simulator
        }
        
        for sensor_name, simulator in self.sensor_simulators.items():
            sensor_data = simulator.generate(state, degradation, timestamp, **sensor_kwargs)
            
            # Prefix sensor readings with category
            for key, value in sensor_data.items():
                observation[f'{sensor_name}_{key}'] = value
        
        # Add ATM metadata (for grouping, not for model features)
        observation['atm_age_years'] = self.rng.uniform(*self.config.atm_age_range)
        observation['installation_type'] = 'indoor' if self.rng.random() < self.config.indoor_ratio else 'outdoor'
        
        return observation
    
    def generate_and_save(self, output_format: str = 'csv', output_path: Optional[str] = None):
        """
        Generate complete dataset incrementally and save to files to prevent MemoryErrors.
        
        Args:
            output_format: 'csv' or 'parquet'
            output_path: Output directory path
        """
        if output_path is None:
            output_path = self.config.output_path
        
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Generating ATM telemetry data...")
        print(f"  ATMs: {self.config.num_atms}")
        print(f"  Duration: {self.config.duration_days} days")
        print(f"  Observation interval: {self.config.observation_interval_minutes} minutes")
        print(f"  Output: {output_dir}")
        
        total_observations = int((self.config.duration_days * 24 * 60) / self.config.observation_interval_minutes)
        sensor_file_path = output_dir / f'sensor_observations.{output_format}'
        
        # Remove existing file if it exists to start fresh
        if sensor_file_path.exists():
            sensor_file_path.unlink()
            
        print(f"\nGenerating {total_observations} time steps incrementally...")
        
        total_obs_count = 0
        operational_count = 0
        
        # Stream and write chunk-by-chunk
        for idx, (timestamp, observations) in enumerate(self.stream()):
            total_obs_count += len(observations)
            
            # Count operational statuses on the fly for statistics
            for obs in observations:
                if obs['operational_status'] == 'operational':
                    operational_count += 1
            
            # Convert current time step observations into a small DataFrame
            df_chunk = pd.DataFrame(observations)
            
            # Append directly to disk
            if output_format == 'csv':
                # Write header only on the very first time step
                header = not sensor_file_path.exists()
                df_chunk.to_csv(sensor_file_path, mode='a', index=False, header=header)
            elif output_format == 'parquet':
                # Note: Standard Parquet doesn't support native row-by-row appending out-of-the-box 
                # without specialized libraries like pyarrow.parquet. If using parquet, write to temp parts 
                # or fallback to CSV for streaming huge data, then convert.
                raise NotImplementedError("Incremental streaming is optimized for 'csv'. Use CSV format for massive datasets.")
            else:
                raise ValueError(f"Unsupported format: {output_format}")
            
            # Progress indicator
            if (idx + 1) % 1000 == 0 or idx == 0:
                progress = ((idx + 1) / total_observations) * 100
                print(f"  Progress: {progress:.1f}% ({idx + 1}/{total_observations} time steps)")
        
        print(f"\nGenerated {total_obs_count} total observations")
        
        # Save failure incidents
        if self.failure_events:
            print(f"Saving {len(self.failure_events)} failure incidents...")
            df_failures = pd.DataFrame([
                {
                    'incident_id': f.incident_id,
                    'atm_id': f.atm_id,
                    'failure_type': f.failure_type.value,
                    'failure_subtype': f.failure_subtype,
                    'start_time': f.start_time,
                    'end_time': f.end_time,
                    'severity': f.severity,
                    'maintenance_level': f.maintenance_level,
                    'repair_duration_hours': f.repair_duration_hours,
                    'root_cause': f.root_cause,
                    'was_sudden': f.was_sudden,
                }
                for f in self.failure_events
            ])
            self._save_dataframe(df_failures, output_dir / f'failure_incidents.{output_format}', output_format)
        
        # Generate and save maintenance events
        print("Generating maintenance events...")
        self._generate_maintenance_events()
        if self.maintenance_events:
            df_maintenance = pd.DataFrame(self.maintenance_events)
            self._save_dataframe(df_maintenance, output_dir / f'maintenance_events.{output_format}', output_format)
        
        # Save metadata
        print("Saving metadata...")
        operational_percentage = (operational_count / total_obs_count) * 100 if total_obs_count > 0 else 0
        metadata = {
            'generation_date': datetime.now().isoformat(),
            'config': {
                'num_atms': self.config.num_atms,
                'duration_days': self.config.duration_days,
                'observation_interval_minutes': self.config.observation_interval_minutes,
                'random_seed': self.config.random_seed,
            },
            'statistics': {
                'total_observations': total_obs_count,
                'total_failures': len(self.failure_events),
                'total_maintenance_events': len(self.maintenance_events),
                'failure_rate_per_atm_year': self._calculate_failure_rate(),
                'operational_percentage': operational_percentage,
            }
        }
        
        with open(output_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Save data dictionary
        print("Saving data dictionary...")
        self._save_data_dictionary(output_dir / 'data_dictionary.md')
        
        print(f"\n✓ Data generation complete!")
        print(f"  Output directory: {output_dir}")
        print(f"  Total failures: {len(self.failure_events)}")
        print(f"  Failure rate: {metadata['statistics']['failure_rate_per_atm_year']:.2f} per ATM/year")
        print(f"  Operational: {metadata['statistics']['operational_percentage']:.1f}%")

    def _save_dataframe(self, df: pd.DataFrame, filepath: Path, format: str):
        """Save DataFrame in specified format."""
        if format == 'csv':
            df.to_csv(filepath, index=False)
        elif format == 'parquet':
            df.to_parquet(filepath, index=False, compression='snappy' if self.config.compress else None)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _generate_maintenance_events(self):
        """Generate maintenance events from failure history."""
        for failure in self.failure_events:
            if failure.end_time:
                maintenance_event = {
                    'maintenance_id': f"MAINT_{failure.incident_id}",
                    'atm_id': failure.atm_id,
                    'maintenance_type': 'corrective',
                    'start_time': failure.start_time,
                    'completion_time': failure.end_time,
                    'component_replaced': self._get_component_for_failure(failure.failure_type),
                    'outcome': 'successful',
                    'related_incident_id': failure.incident_id,
                }
                self.maintenance_events.append(maintenance_event)
    
    def _get_component_for_failure(self, failure_type: FailureType) -> str:
        """Map failure type to component."""
        mapping = {
            FailureType.NETWORK: 'network_module',
            FailureType.POWER: 'power_supply',
            FailureType.THERMAL: 'cooling_fan',
            FailureType.DISPENSER: 'dispenser_mechanism',
            FailureType.CARD_READER: 'card_reader',
            FailureType.PRINTER: 'printer_mechanism',
            FailureType.SOFTWARE: 'software_update',
            FailureType.HARDWARE: 'hardware_module',
        }
        return mapping.get(failure_type, 'unknown')
    
    def _calculate_failure_rate(self) -> float:
        """Calculate failure rate per ATM per year."""
        if not self.failure_events:
            return 0.0
        
        total_atm_years = self.config.num_atms * (self.config.duration_days / 365)
        return len(self.failure_events) / total_atm_years
    
    def _save_data_dictionary(self, filepath: Path):
        """Generate and save data dictionary."""
        dictionary = """# ATM Telemetry Data Dictionary

## Sensor Observations Dataset

### Identification & Temporal
- `timestamp`: Observation timestamp (datetime)
- `atm_id`: ATM identifier (string) - **For grouping only, not for model features**
- `operational_status`: Current operational status (operational/out_of_service)
- `state`: Hidden health state (string) - **Not for model features**
- `degradation_level`: Hidden degradation level 0-1 (float) - **Not for model features**

### ATM Metadata
- `atm_age_years`: Age of ATM in years (float)
- `installation_type`: Indoor or outdoor installation (string)

### Network Sensors
- `network_signal_strength_dbm`: Signal strength in dBm (float)
- `network_latency_ms`: Network latency in milliseconds (float)
- `network_packet_loss_percent`: Packet loss percentage (float)
- `network_heartbeat_gap_sec`: Gap since last heartbeat in seconds (float)
- `network_timeout_count`: Number of timeouts (int)
- `network_reconnect_count`: Number of reconnections (int)

### Power Sensors
- `power_input_voltage_v`: Input voltage in volts (float)
- `power_voltage_variation_v`: Voltage variation from nominal (float)
- `power_battery_charge_percent`: Battery charge percentage (float)
- `power_battery_health_percent`: Battery health percentage (float)
- `power_ups_transfers`: Number of UPS transfers (int)
- `power_power_supply_temp_c`: Power supply temperature in Celsius (float)
- `power_unexpected_reboot_count`: Unexpected reboot count (int)

### Temperature Sensors
- `temperature_cabinet_temp_c`: Cabinet temperature in Celsius (float)
- `temperature_cpu_temp_c`: CPU temperature in Celsius (float)
- `temperature_power_module_temp_c`: Power module temperature in Celsius (float)
- `temperature_fan_speed_rpm`: Fan speed in RPM (int)
- `temperature_fan_warning`: Fan warning flag (bool)
- `temperature_time_above_warning_temp_min`: Time above warning temperature in minutes (int)

### Dispenser Sensors
- `dispenser_failed_pick_count`: Failed note pick count (int)
- `dispenser_note_reject_rate_percent`: Note reject rate percentage (float)
- `dispenser_double_note_count`: Double note detection count (int)
- `dispenser_retract_bin_count`: Retract bin activity count (int)
- `dispenser_motor_current_ma`: Motor current in milliamps (int)
- `dispenser_jam_warning_count`: Jam warning count (int)
- `dispenser_successful_dispense_count`: Successful dispense count (int)

### Card Reader Sensors
- `card_reader_read_retry_rate_percent`: Read retry rate percentage (float)
- `card_reader_retained_card_count`: Retained card count (int)
- `card_reader_reader_reset_count`: Reader reset count (int)
- `card_reader_reader_unavailable_warning`: Reader unavailable warning (bool)

### Printer Sensors
- `printer_paper_level_percent`: Paper level percentage (float)
- `printer_paper_low_warning`: Paper low warning flag (bool)
- `printer_cutter_error_count`: Cutter error count (int)
- `printer_printer_temp_c`: Printer temperature in Celsius (float)
- `printer_failed_print_count`: Failed print count (int)

### Software Sensors
- `software_cpu_usage_percent`: CPU usage percentage (float)
- `software_memory_usage_percent`: Memory usage percentage (float)
- `software_disk_usage_percent`: Disk usage percentage (float)
- `software_app_restart_count`: Application restart count (int)
- `software_os_error_count`: OS error count (int)
- `software_uptime_hours`: System uptime in hours (float)

### Monitoring Sensors
- `monitoring_successful_transaction_count`: Successful transaction count (int)
- `monitoring_failed_transaction_count`: Failed transaction count (int)
- `monitoring_timeout_count`: Transaction timeout count (int)
- `monitoring_decline_count`: Transaction decline count (int)
- `monitoring_unresolved_warning_count`: Unresolved warning count (int)
- `monitoring_time_since_last_transaction_min`: Time since last transaction in minutes (float)

## Failure Incidents Dataset

- `incident_id`: Unique incident identifier (string)
- `atm_id`: ATM identifier (string)
- `failure_type`: Type of failure (network/power/thermal/dispenser/card_reader/printer/software/hardware)
- `failure_subtype`: Specific failure subtype (string)
- `start_time`: Failure start timestamp (datetime)
- `end_time`: Failure end timestamp (datetime)
- `severity`: Failure severity (low/medium/high/critical)
- `maintenance_level`: Maintenance level required (FLM/SLM)
- `repair_duration_hours`: Repair duration in hours (float)
- `root_cause`: Root cause description (string)
- `was_sudden`: Whether failure was sudden without warning (bool)

## Maintenance Events Dataset

- `maintenance_id`: Unique maintenance identifier (string)
- `atm_id`: ATM identifier (string)
- `maintenance_type`: Type of maintenance (corrective/preventive/component_replacement)
- `start_time`: Maintenance start timestamp (datetime)
- `completion_time`: Maintenance completion timestamp (datetime)
- `component_replaced`: Component that was replaced (string)
- `outcome`: Maintenance outcome (successful/partial/failed)
- `related_incident_id`: Related incident ID if corrective maintenance (string)

## Important Notes

### Location Independence
The following fields must NOT be used in production model features:
- `atm_id` (use only for grouping and splitting)
- `state` (hidden simulation state)
- `degradation_level` (hidden simulation state)

### Missing Data
Sensor readings may contain `None` values representing missing or unavailable data (~2% rate).

### Target Variable
For predictive modeling, create target variable `fails_within_next_30m` by checking if any failure starts within 30 minutes after the observation timestamp.
"""
        
        with open(filepath, 'w') as f:
            f.write(dictionary)
