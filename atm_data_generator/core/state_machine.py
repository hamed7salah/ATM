"""
ATM state machine for simulating health states and transitions.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import numpy as np


class ATMState(Enum):
    """ATM health states."""
    HEALTHY = "healthy"
    DEGRADING = "degrading"
    WARNING = "warning"
    FAILED = "failed"
    UNDER_REPAIR = "under_repair"
    RECOVERED = "recovered"


class FailureType(Enum):
    """Types of ATM failures."""
    NETWORK = "network"
    POWER = "power"
    THERMAL = "thermal"
    DISPENSER = "dispenser"
    CARD_READER = "card_reader"
    PRINTER = "printer"
    SOFTWARE = "software"
    HARDWARE = "hardware"


@dataclass
class FailureEvent:
    """Represents a failure incident."""
    incident_id: str
    atm_id: str
    failure_type: FailureType
    failure_subtype: str
    start_time: datetime
    end_time: Optional[datetime] = None
    severity: str = "medium"  # low, medium, high, critical
    maintenance_level: str = "FLM"  # FLM or SLM
    repair_duration_hours: Optional[float] = None
    root_cause: str = ""
    was_sudden: bool = False


@dataclass
class MaintenanceEvent:
    """Represents a maintenance action."""
    maintenance_id: str
    atm_id: str
    maintenance_type: str  # preventive, corrective, component_replacement
    start_time: datetime
    completion_time: Optional[datetime] = None
    component_replaced: Optional[str] = None
    outcome: str = "pending"  # pending, successful, partial, failed


class ATMStateMachine:
    """
    Manages ATM health state transitions and failure generation.
    
    State flow:
    healthy → degrading → warning → failed → under_repair → recovered → healthy
    
    Alternative paths:
    - degrading → healthy (recovery without failure)
    - healthy → failed (sudden failure)
    - warning → degrading (temporary improvement)
    """
    
    def __init__(self, atm_id: str, config, random_state: np.random.RandomState):
        self.atm_id = atm_id
        self.config = config
        self.rng = random_state
        
        self.current_state = ATMState.HEALTHY
        self.state_entry_time = None
        self.time_in_state = 0  # observations
        
        # Degradation tracking
        self.degradation_level = 0.0  # 0.0 = healthy, 1.0 = critical
        self.degradation_rate = 0.0
        
        # Current failure tracking
        self.current_failure: Optional[FailureEvent] = None
        self.failure_history: list = []
        self.maintenance_history: list = []
        
        # Component ages (affects failure probability)
        self.component_ages = {
            'dispenser': self.rng.uniform(0, 5),
            'card_reader': self.rng.uniform(0, 5),
            'printer': self.rng.uniform(0, 5),
            'power_supply': self.rng.uniform(0, 8),
            'network_module': self.rng.uniform(0, 6),
        }
    
    def update(self, current_time: datetime) -> tuple[ATMState, Optional[FailureEvent]]:
        """
        Update state machine and return current state and any new failure event.
        
        Returns:
            (current_state, new_failure_event or None)
        """
        self.time_in_state += 1
        new_failure = None
        
        if self.current_state == ATMState.HEALTHY:
            new_failure = self._update_healthy(current_time)
        
        elif self.current_state == ATMState.DEGRADING:
            self._update_degrading(current_time)
        
        elif self.current_state == ATMState.WARNING:
            new_failure = self._update_warning(current_time)
        
        elif self.current_state == ATMState.FAILED:
            self._update_failed(current_time)
        
        elif self.current_state == ATMState.UNDER_REPAIR:
            self._update_under_repair(current_time)
        
        elif self.current_state == ATMState.RECOVERED:
            self._update_recovered(current_time)
        
        return self.current_state, new_failure
    
    def _update_healthy(self, current_time: datetime) -> Optional[FailureEvent]:
        """Update healthy state."""
        # Check for sudden failure (no warning)
        sudden_failure_rate = self._calculate_failure_rate() * self.config.sudden_failure_prob
        if self.rng.random() < sudden_failure_rate:
            return self._trigger_failure(current_time, sudden=True)
        
        # Check for degradation start
        if self.rng.random() < self.config.healthy_to_degrading_prob:
            self._transition_to(ATMState.DEGRADING, current_time)
            self.degradation_rate = self.rng.uniform(0.01, 0.05)
        
        return None
    
    def _update_degrading(self, current_time: datetime):
        """Update degrading state."""
        # Increase degradation level
        self.degradation_level += self.degradation_rate
        self.degradation_level = min(self.degradation_level, 1.0)
        
        # Check for recovery
        if self.rng.random() < self.config.degrading_to_healthy_prob:
            self._transition_to(ATMState.HEALTHY, current_time)
            self.degradation_level = 0.0
            self.degradation_rate = 0.0
            return
        
        # Check for warning state
        if self.degradation_level > 0.5 or self.rng.random() < self.config.degrading_to_warning_prob:
            self._transition_to(ATMState.WARNING, current_time)
    
    def _update_warning(self, current_time: datetime) -> Optional[FailureEvent]:
        """Update warning state."""
        # Increase degradation faster
        self.degradation_level += self.degradation_rate * 1.5
        self.degradation_level = min(self.degradation_level, 1.0)
        
        # Check for failure
        failure_prob = self.config.warning_to_failed_prob * (1 + self.degradation_level)
        if self.rng.random() < failure_prob:
            return self._trigger_failure(current_time, sudden=False)
        
        # Check for temporary improvement
        if self.rng.random() < self.config.warning_to_degrading_prob:
            self._transition_to(ATMState.DEGRADING, current_time)
            self.degradation_level *= 0.8
        
        return None
    
    def _update_failed(self, current_time: datetime):
        """Update failed state - waiting for repair to start."""
        # In real scenario, repair would be scheduled
        # For simulation, start repair after a delay
        if self.time_in_state > self.rng.randint(1, 6):  # 5-30 minutes delay
            self._transition_to(ATMState.UNDER_REPAIR, current_time)
    
    def _update_under_repair(self, current_time: datetime):
        """Update under repair state."""
        if self.current_failure:
            # Check if repair is complete
            repair_duration_observations = (self.current_failure.repair_duration_hours * 60) / self.config.observation_interval_minutes
            
            if self.time_in_state >= repair_duration_observations:
                # Repair complete
                self.current_failure.end_time = current_time
                self.current_failure.outcome = "successful"
                self._transition_to(ATMState.RECOVERED, current_time)
    
    def _update_recovered(self, current_time: datetime):
        """Update recovered state - brief period after repair."""
        # Return to healthy after a few observations
        if self.time_in_state > 2:
            self._transition_to(ATMState.HEALTHY, current_time)
            self.degradation_level = 0.0
            self.degradation_rate = 0.0
            self.current_failure = None
    
    def _trigger_failure(self, current_time: datetime, sudden: bool = False) -> FailureEvent:
        """Trigger a failure event."""
        failure_type = self._select_failure_type()
        
        # Determine maintenance level and repair time
        is_slm = self.rng.random() < 0.3  # 30% require SLM
        if is_slm:
            repair_hours = max(0.5, self.rng.normal(
                self.config.maintenance.slm_repair_time_mean,
                self.config.maintenance.slm_repair_time_std
            ))
            maintenance_level = "SLM"
        else:
            repair_hours = max(0.5, self.rng.normal(
                self.config.maintenance.flm_repair_time_mean,
                self.config.maintenance.flm_repair_time_std
            ))
            maintenance_level = "FLM"
        
        # Create failure event
        incident_id = f"INC_{self.atm_id}_{current_time.strftime('%Y%m%d%H%M%S')}"
        failure = FailureEvent(
            incident_id=incident_id,
            atm_id=self.atm_id,
            failure_type=failure_type,
            failure_subtype=self._get_failure_subtype(failure_type),
            start_time=current_time,
            severity=self._determine_severity(),
            maintenance_level=maintenance_level,
            repair_duration_hours=repair_hours,
            root_cause=self._generate_root_cause(failure_type),
            was_sudden=sudden
        )
        
        self.current_failure = failure
        self.failure_history.append(failure)
        self._transition_to(ATMState.FAILED, current_time)
        
        return failure
    
    def _select_failure_type(self) -> FailureType:
        """Select failure type based on configured rates and component ages."""
        rates = self.config.failure_rates
        
        # Adjust rates based on component age
        adjusted_rates = {
            FailureType.NETWORK: rates.network,
            FailureType.POWER: rates.power,
            FailureType.THERMAL: rates.thermal,
            FailureType.DISPENSER: rates.dispenser * (1 + self.component_ages['dispenser'] * 0.1),
            FailureType.CARD_READER: rates.card_reader * (1 + self.component_ages['card_reader'] * 0.1),
            FailureType.PRINTER: rates.printer * (1 + self.component_ages['printer'] * 0.1),
            FailureType.SOFTWARE: rates.software,
            FailureType.HARDWARE: rates.hardware,
        }
        
        # Normalize to probabilities
        total = sum(adjusted_rates.values())
        probs = [v / total for v in adjusted_rates.values()]
        
        return self.rng.choice(list(adjusted_rates.keys()), p=probs)
    
    def _get_failure_subtype(self, failure_type: FailureType) -> str:
        """Get specific subtype for a failure."""
        subtypes = {
            FailureType.NETWORK: ['connectivity_loss', 'timeout', 'dns_failure', 'switch_failure'],
            FailureType.POWER: ['voltage_drop', 'power_outage', 'ups_failure', 'power_supply_failure'],
            FailureType.THERMAL: ['overheating', 'fan_failure', 'cooling_system_failure'],
            FailureType.DISPENSER: ['jam', 'pick_failure', 'transport_error', 'motor_failure'],
            FailureType.CARD_READER: ['read_error', 'card_jam', 'reader_malfunction'],
            FailureType.PRINTER: ['paper_jam', 'cutter_failure', 'print_head_failure'],
            FailureType.SOFTWARE: ['application_crash', 'os_error', 'driver_failure'],
            FailureType.HARDWARE: ['disk_failure', 'memory_error', 'controller_failure'],
        }
        return self.rng.choice(subtypes.get(failure_type, ['unknown']))
    
    def _determine_severity(self) -> str:
        """Determine failure severity."""
        rand = self.rng.random()
        if rand < 0.1:
            return 'critical'
        elif rand < 0.3:
            return 'high'
        elif rand < 0.7:
            return 'medium'
        else:
            return 'low'
    
    def _generate_root_cause(self, failure_type: FailureType) -> str:
        """Generate a plausible root cause description."""
        causes = {
            FailureType.NETWORK: 'Network connectivity issue',
            FailureType.POWER: 'Power supply instability',
            FailureType.THERMAL: 'Thermal management failure',
            FailureType.DISPENSER: 'Mechanical wear in dispenser',
            FailureType.CARD_READER: 'Card reader sensor malfunction',
            FailureType.PRINTER: 'Printer mechanism failure',
            FailureType.SOFTWARE: 'Software exception',
            FailureType.HARDWARE: 'Hardware component failure',
        }
        return causes.get(failure_type, 'Unknown cause')
    
    def _calculate_failure_rate(self) -> float:
        """Calculate current failure rate per observation."""
        # Convert annual rates to per-observation probability
        total_annual_rate = sum([
            self.config.failure_rates.network,
            self.config.failure_rates.power,
            self.config.failure_rates.thermal,
            self.config.failure_rates.dispenser,
            self.config.failure_rates.card_reader,
            self.config.failure_rates.printer,
            self.config.failure_rates.software,
            self.config.failure_rates.hardware,
        ])
        
        observations_per_year = (365 * 24 * 60) / self.config.observation_interval_minutes
        return total_annual_rate / observations_per_year
    
    def _transition_to(self, new_state: ATMState, current_time: datetime):
        """Transition to a new state."""
        self.current_state = new_state
        self.state_entry_time = current_time
        self.time_in_state = 0
    
    def is_operational(self) -> bool:
        """Check if ATM is currently operational."""
        return self.current_state not in [ATMState.FAILED, ATMState.UNDER_REPAIR]
    
    def get_degradation_level(self) -> float:
        """Get current degradation level (0.0 to 1.0)."""
        return self.degradation_level
