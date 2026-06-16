# Changelog

## 1.0.2

- Per-word translation: names without an exact dictionary match are now translated label by label, keeping the untranslated words instead of collapsing the whole name to the first matching word (e.g. `Alarm siren duration` no longer became just `Alarm`).
- Untranslated words are logged once each (`Traduction manquante (<lang>) : [...]`) to make contributing missing translations easy.

## 1.0.1

- Expanded translation dictionaries (`fr`, `de`, `es`) with labels covering common Zigbee devices on the market:
  - **Aqara H2 EU (WS-K07E)**: `power`, `current`, `energy`, `state`, `led_indicator`, `flip_indicator_light`, `power_outage_count`, `lock_relay`, `multi_click`, plus the calibration/precision options (`power_calibration`, `power_precision`, `current_calibration`, `current_precision`, `energy_calibration`, `energy_precision`, `device_temperature_calibration`, `state_action`).
  - **Energy / metering**: `voltage`, `frequency`, `power_factor`, `voltage_calibration`, `voltage_precision`.
  - **Sensors**: `temperature`, `humidity`, `pressure`, `illuminance`, `illuminance_lux`, `occupancy`, `presence`, `motion`, `motion_state`, `contact`, `water_leak`, `smoke`, `gas`, `tamper`, `vibration`, `alarm`, `noise`.
  - **Air quality**: `co2`, `voc`, `voc_index`, `formaldehyde`, `pm25`, `pm10`, `air_quality`.
  - **Battery**: `battery_voltage`, `battery_state`.
  - **Lighting**: `brightness`, `color`, `color_mode`, `color_temp`, `color_temp_startup`, `color_xy`, `color_hs`, `effect`, `transition`, `min_brightness`, `max_brightness`.
  - **Covers / motors**: `position`, `tilt`, `motor_direction`, `motor_speed`.
  - **Climate**: `target_temperature`, `current_heating_setpoint`, `unoccupied_heating_setpoint`, `preset`, `mode`, `fan_mode`, `swing_mode`, `away_mode`, `eco_mode`, `boost`, `boost_time`.
  - **Diagnostic / device**: `last_seen`, `update_available`, `restart`, `identify`, `reset`, `factory_reset`, `power_outage_memory`.
  - **Common options**: `duration`, `sensitivity`, `detection_distance`, `keep_time`, `occupancy_timeout`, `illuminance_above_threshold`, `led_disabled_night`.
- Multi-endpoint switch states added (`state_up`, `state_down`, `state_left`, `state_right`).

## 1.0.0

- MQTT discovery proxy; configurable source/target prefixes; Supervisor MQTT auto-config (`with-contenv`)
- Translation dictionaries: **French**, **German**, **Spanish** (`translations/fr.json`, `de.json`, `es.json`)
- **language** add-on option as a dropdown (`fr` | `de` | `es`)
