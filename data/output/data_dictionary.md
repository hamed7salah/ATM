# ATM Telemetry Data Dictionary

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
