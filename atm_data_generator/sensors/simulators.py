"""
Sensor simulation modules for generating realistic ATM telemetry data.
"""

import numpy as np
from datetime import datetime
from typing import Dict, Any
from ..core.state_machine import ATMState


class SensorSimulator:
    """Base class for sensor simulators."""
    
    def __init__(self, config, random_state: np.random.RandomState):
        self.config = config
        self.rng = random_state
    
    def generate(self, state: ATMState, degradation_level: float, 
                 current_time: datetime, **kwargs) -> Dict[str, Any]:
        """Generate sensor readings based on current state."""
        raise NotImplementedError


class NetworkSensorSimulator(SensorSimulator):
    """Simulates network and connectivity sensors."""
    
    def generate(self, state: ATMState, degradation_level: float, 
                 current_time: datetime, **kwargs) -> Dict[str, Any]:
        
        env = self.config.environment
        noise = self.config.sensor_noise
        
        # Base values
        signal_strength = self.rng.normal(env.network_signal_mean, env.network_signal_std)
        latency = self.rng.gamma(2, 10)  # ms, typical network latency
        packet_loss = self.rng.exponential(0.5)  # %
        
        # Degrade based on state
        if state == ATMState.DEGRADING:
            signal_strength -= degradation_level * 10
            latency += degradation_level * 20
            packet_loss += degradation_level * 2
        elif state == ATMState.WARNING:
            signal_strength -= degradation_level * 15
            latency += degradation_level * 50
            packet_loss += degradation_level * 5
        elif state in [ATMState.FAILED, ATMState.UNDER_REPAIR]:
            # Network failure
            if kwargs.get('failure_type') == 'network':
                signal_strength = -95  # Very weak
                latency = 999  # Timeout
                packet_loss = 100
        
        # Add noise
        signal_strength += self.rng.normal(0, noise.signal_strength_std)
        latency += self.rng.normal(0, noise.latency_std)
        
        # Clamp values
        signal_strength = np.clip(signal_strength, -100, -30)
        latency = max(0, latency)
        packet_loss = np.clip(packet_loss, 0, 100)
        
        # Missing data
        if self.rng.random() < noise.missing_rate:
            return {k: None for k in ['signal_strength_dbm', 'latency_ms', 'packet_loss_percent',
                                       'heartbeat_gap_sec', 'timeout_count', 'reconnect_count']}
        
        return {
            'signal_strength_dbm': round(signal_strength, 1),
            'latency_ms': round(latency, 1),
            'packet_loss_percent': round(packet_loss, 2),
            'heartbeat_gap_sec': round(self.rng.exponential(5), 1),
            'timeout_count': int(self.rng.poisson(packet_loss / 20)),
            'reconnect_count': int(self.rng.poisson(degradation_level * 0.5)),
        }


class PowerSensorSimulator(SensorSimulator):
    """Simulates power and UPS sensors."""
    
    def generate(self, state: ATMState, degradation_level: float, 
                 current_time: datetime, **kwargs) -> Dict[str, Any]:
        
        env = self.config.environment
        noise = self.config.sensor_noise
        
        # Base voltage
        voltage = self.rng.normal(env.voltage_nominal, env.voltage_variation_std)
        
        # Battery health (degrades over time)
        battery_health = max(50, 100 - degradation_level * 30)
        battery_charge = self.rng.uniform(85, 100)
        
        # Power spikes
        if self.rng.random() < env.power_spike_rate / (24 * 12):  # per 5-min interval
            voltage += self.rng.uniform(-20, 30)
        
        # Degrade based on state
        if state == ATMState.DEGRADING:
            voltage += self.rng.normal(0, degradation_level * 10)
            battery_health -= degradation_level * 10
        elif state == ATMState.WARNING:
            voltage += self.rng.normal(0, degradation_level * 15)
            battery_health -= degradation_level * 20
        elif state in [ATMState.FAILED, ATMState.UNDER_REPAIR]:
            if kwargs.get('failure_type') == 'power':
                voltage = self.rng.uniform(0, 100)  # Power failure
                battery_charge = self.rng.uniform(0, 30)
        
        # Add noise
        voltage += self.rng.normal(0, noise.voltage_std)
        
        # Clamp values
        voltage = max(0, voltage)
        battery_health = np.clip(battery_health, 0, 100)
        battery_charge = np.clip(battery_charge, 0, 100)
        
        # Missing data
        if self.rng.random() < noise.missing_rate:
            return {k: None for k in ['input_voltage_v', 'voltage_variation_v', 'battery_charge_percent',
                                       'battery_health_percent', 'ups_transfers', 'power_supply_temp_c',
                                       'unexpected_reboot_count']}
        
        return {
            'input_voltage_v': round(voltage, 1),
            'voltage_variation_v': round(abs(voltage - env.voltage_nominal), 1),
            'battery_charge_percent': round(battery_charge, 1),
            'battery_health_percent': round(battery_health, 1),
            'ups_transfers': int(self.rng.poisson(degradation_level * 2)),
            'power_supply_temp_c': round(self.rng.normal(45, 5) + degradation_level * 10, 1),
            'unexpected_reboot_count': int(self.rng.poisson(degradation_level * 0.3)),
        }


class TemperatureSensorSimulator(SensorSimulator):
    """Simulates temperature and cooling sensors."""
    
    def generate(self, state: ATMState, degradation_level: float, 
                 current_time: datetime, **kwargs) -> Dict[str, Any]:
        
        env = self.config.environment
        noise = self.config.sensor_noise
        
        # Calculate ambient temperature with daily variation
        hour = current_time.hour
        daily_variation = env.daily_temp_amplitude * np.sin((hour - 6) * np.pi / 12)
        ambient_temp = env.ambient_temp_mean + daily_variation
        ambient_temp += self.rng.normal(0, env.ambient_temp_std)
        ambient_temp = np.clip(ambient_temp, env.ambient_temp_min, env.ambient_temp_max)
        
        # Cabinet temperature (higher than ambient)
        cabinet_temp = ambient_temp + self.rng.uniform(5, 15)
        cpu_temp = cabinet_temp + self.rng.uniform(10, 25)
        
        # Fan speed (RPM)
        fan_speed = self.rng.normal(2000, 200)
        
        # Degrade based on state
        if state == ATMState.DEGRADING:
            cabinet_temp += degradation_level * 10
            cpu_temp += degradation_level * 15
            fan_speed -= degradation_level * 500
        elif state == ATMState.WARNING:
            cabinet_temp += degradation_level * 15
            cpu_temp += degradation_level * 25
            fan_speed -= degradation_level * 800
        elif state in [ATMState.FAILED, ATMState.UNDER_REPAIR]:
            if kwargs.get('failure_type') == 'thermal':
                cabinet_temp += 20
                cpu_temp += 30
                fan_speed = self.rng.uniform(0, 500)  # Fan failure
        
        # Add noise
        cabinet_temp += self.rng.normal(0, noise.temperature_std)
        cpu_temp += self.rng.normal(0, noise.temperature_std)
        
        # Clamp values
        cabinet_temp = max(15, cabinet_temp)
        cpu_temp = max(20, cpu_temp)
        fan_speed = max(0, fan_speed)
        
        # Missing data
        if self.rng.random() < noise.missing_rate:
            return {k: None for k in ['cabinet_temp_c', 'cpu_temp_c', 'power_module_temp_c',
                                       'fan_speed_rpm', 'fan_warning', 'time_above_warning_temp_min']}
        
        return {
            'cabinet_temp_c': round(cabinet_temp, 1),
            'cpu_temp_c': round(cpu_temp, 1),
            'power_module_temp_c': round(cabinet_temp + self.rng.uniform(5, 15), 1),
            'fan_speed_rpm': int(fan_speed),
            'fan_warning': fan_speed < 1000,
            'time_above_warning_temp_min': int(degradation_level * 30) if cabinet_temp > 45 else 0,
        }


class DispenserSensorSimulator(SensorSimulator):
    """Simulates cash dispenser sensors."""
    
    def generate(self, state: ATMState, degradation_level: float, 
                 current_time: datetime, **kwargs) -> Dict[str, Any]:
        
        # Transaction activity affects dispenser wear
        transaction_count = kwargs.get('transaction_count', 0)
        
        # Base failure rates
        failed_pick_count = int(self.rng.poisson(degradation_level * 2))
        note_reject_rate = self.rng.exponential(0.5) + degradation_level * 2
        double_note_count = int(self.rng.poisson(degradation_level * 0.5))
        
        # Motor current (mA)
        motor_current = self.rng.normal(800, 50)
        
        # Degrade based on state
        if state == ATMState.DEGRADING:
            failed_pick_count += int(degradation_level * 3)
            note_reject_rate += degradation_level * 3
            motor_current += degradation_level * 200
        elif state == ATMState.WARNING:
            failed_pick_count += int(degradation_level * 5)
            note_reject_rate += degradation_level * 5
            motor_current += degradation_level * 300
        elif state in [ATMState.FAILED, ATMState.UNDER_REPAIR]:
            if kwargs.get('failure_type') == 'dispenser':
                failed_pick_count += 10
                note_reject_rate = 100
                motor_current = self.rng.uniform(1200, 1500)  # Overload
        
        # Clamp values
        note_reject_rate = np.clip(note_reject_rate, 0, 100)
        motor_current = max(0, motor_current)
        
        # Missing data
        if self.rng.random() < self.config.sensor_noise.missing_rate:
            return {k: None for k in ['failed_pick_count', 'note_reject_rate_percent', 'double_note_count',
                                       'retract_bin_count', 'motor_current_ma', 'jam_warning_count',
                                       'successful_dispense_count']}
        
        return {
            'failed_pick_count': failed_pick_count,
            'note_reject_rate_percent': round(note_reject_rate, 2),
            'double_note_count': double_note_count,
            'retract_bin_count': int(self.rng.poisson(degradation_level)),
            'motor_current_ma': int(motor_current),
            'jam_warning_count': int(self.rng.poisson(degradation_level * 2)),
            'successful_dispense_count': max(0, transaction_count - failed_pick_count),
        }


class CardReaderSensorSimulator(SensorSimulator):
    """Simulates card reader sensors."""
    
    def generate(self, state: ATMState, degradation_level: float, 
                 current_time: datetime, **kwargs) -> Dict[str, Any]:
        
        # Base values
        read_retry_rate = self.rng.exponential(1) + degradation_level * 2
        retained_card_count = int(self.rng.poisson(degradation_level * 0.3))
        reader_reset_count = int(self.rng.poisson(degradation_level * 0.5))
        
        # Degrade based on state
        if state == ATMState.DEGRADING:
            read_retry_rate += degradation_level * 3
            retained_card_count += int(degradation_level * 2)
        elif state == ATMState.WARNING:
            read_retry_rate += degradation_level * 5
            retained_card_count += int(degradation_level * 3)
            reader_reset_count += int(degradation_level * 2)
        elif state in [ATMState.FAILED, ATMState.UNDER_REPAIR]:
            if kwargs.get('failure_type') == 'card_reader':
                read_retry_rate = 100
                retained_card_count += 5
        
        # Clamp values
        read_retry_rate = np.clip(read_retry_rate, 0, 100)
        
        # Missing data
        if self.rng.random() < self.config.sensor_noise.missing_rate:
            return {k: None for k in ['read_retry_rate_percent', 'retained_card_count', 
                                       'reader_reset_count', 'reader_unavailable_warning']}
        
        return {
            'read_retry_rate_percent': round(read_retry_rate, 2),
            'retained_card_count': retained_card_count,
            'reader_reset_count': reader_reset_count,
            'reader_unavailable_warning': state == ATMState.WARNING and degradation_level > 0.7,
        }


class PrinterSensorSimulator(SensorSimulator):
    """Simulates receipt printer sensors."""
    
    def generate(self, state: ATMState, degradation_level: float, 
                 current_time: datetime, **kwargs) -> Dict[str, Any]:
        
        # Paper level
        paper_level = self.rng.uniform(30, 100) - degradation_level * 20
        paper_level = np.clip(paper_level, 0, 100)
        
        # Errors
        cutter_error_count = int(self.rng.poisson(degradation_level * 0.5))
        failed_print_count = int(self.rng.poisson(degradation_level))
        
        # Temperature
        printer_temp = self.rng.normal(40, 5) + degradation_level * 10
        
        # Degrade based on state
        if state == ATMState.WARNING:
            cutter_error_count += int(degradation_level * 2)
            failed_print_count += int(degradation_level * 3)
        elif state in [ATMState.FAILED, ATMState.UNDER_REPAIR]:
            if kwargs.get('failure_type') == 'printer':
                failed_print_count += 10
                printer_temp += 20
        
        # Missing data
        if self.rng.random() < self.config.sensor_noise.missing_rate:
            return {k: None for k in ['paper_level_percent', 'paper_low_warning', 'cutter_error_count',
                                       'printer_temp_c', 'failed_print_count']}
        
        return {
            'paper_level_percent': round(paper_level, 1),
            'paper_low_warning': paper_level < 20,
            'cutter_error_count': cutter_error_count,
            'printer_temp_c': round(printer_temp, 1),
            'failed_print_count': failed_print_count,
        }


class SoftwareSensorSimulator(SensorSimulator):
    """Simulates software and controller health sensors."""
    
    def generate(self, state: ATMState, degradation_level: float, 
                 current_time: datetime, **kwargs) -> Dict[str, Any]:
        
        # Base values
        cpu_usage = self.rng.uniform(20, 50) + degradation_level * 30
        memory_usage = self.rng.uniform(40, 70) + degradation_level * 20
        disk_usage = self.rng.uniform(50, 80)
        
        # Application restarts
        app_restart_count = int(self.rng.poisson(degradation_level * 0.5))
        os_error_count = int(self.rng.poisson(degradation_level))
        
        # Uptime (hours)
        uptime_hours = self.rng.exponential(200) if state == ATMState.HEALTHY else self.rng.exponential(50)
        
        # Degrade based on state
        if state == ATMState.DEGRADING:
            cpu_usage += degradation_level * 20
            memory_usage += degradation_level * 15
        elif state == ATMState.WARNING:
            cpu_usage += degradation_level * 30
            memory_usage += degradation_level * 25
            app_restart_count += int(degradation_level * 2)
        elif state in [ATMState.FAILED, ATMState.UNDER_REPAIR]:
            if kwargs.get('failure_type') == 'software':
                cpu_usage = 100
                memory_usage = 95
                app_restart_count += 5
        
        # Clamp values
        cpu_usage = np.clip(cpu_usage, 0, 100)
        memory_usage = np.clip(memory_usage, 0, 100)
        disk_usage = np.clip(disk_usage, 0, 100)
        
        # Missing data
        if self.rng.random() < self.config.sensor_noise.missing_rate:
            return {k: None for k in ['cpu_usage_percent', 'memory_usage_percent', 'disk_usage_percent',
                                       'app_restart_count', 'os_error_count', 'uptime_hours']}
        
        return {
            'cpu_usage_percent': round(cpu_usage, 1),
            'memory_usage_percent': round(memory_usage, 1),
            'disk_usage_percent': round(disk_usage, 1),
            'app_restart_count': app_restart_count,
            'os_error_count': os_error_count,
            'uptime_hours': round(uptime_hours, 1),
        }


class MonitoringSensorSimulator(SensorSimulator):
    """Simulates central monitoring and transaction data."""
    
    def generate(self, state: ATMState, degradation_level: float, 
                 current_time: datetime, **kwargs) -> Dict[str, Any]:
        
        # Transaction counts (affected by time of day)
        hour = current_time.hour
        is_peak = hour in self.config.peak_hours
        
        base_transactions = self.rng.poisson(10 if is_peak else 3)
        
        if state in [ATMState.FAILED, ATMState.UNDER_REPAIR]:
            successful_transactions = 0
            failed_transactions = 0
            timeout_count = 0
        else:
            successful_transactions = int(base_transactions * (1 - degradation_level * 0.5))
            failed_transactions = int(self.rng.poisson(degradation_level * 2))
            timeout_count = int(self.rng.poisson(degradation_level * 3))
        
        # Warning counts
        unresolved_warning_count = int(degradation_level * 5)
        
        # Missing data
        if self.rng.random() < self.config.sensor_noise.missing_rate:
            return {k: None for k in ['successful_transaction_count', 'failed_transaction_count',
                                       'timeout_count', 'decline_count', 'unresolved_warning_count',
                                       'time_since_last_transaction_min']}
        
        return {
            'successful_transaction_count': successful_transactions,
            'failed_transaction_count': failed_transactions,
            'timeout_count': timeout_count,
            'decline_count': int(self.rng.poisson(1)),
            'unresolved_warning_count': unresolved_warning_count,
            'time_since_last_transaction_min': round(self.rng.exponential(15), 1) if successful_transactions == 0 else 0,
        }
