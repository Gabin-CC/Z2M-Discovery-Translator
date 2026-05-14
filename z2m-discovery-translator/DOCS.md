# Z2M Discovery Translator

## What it does

This add-on listens to Zigbee2MQTT Home Assistant MQTT Discovery payloads on a source prefix, translates known entity names, then republishes them to Home Assistant's discovery prefix.

Default flow:

```text
z2m_discovery/#  →  translator  →  homeassistant/#
```

## Zigbee2MQTT configuration

In Zigbee2MQTT, configure:

```yaml
homeassistant:
  enabled: true
  discovery_topic: z2m_discovery
  status_topic: homeassistant/status
```

Restart Zigbee2MQTT after the translator add-on is running.

## Add-on options

```yaml
mqtt_host: core-mosquitto
mqtt_port: 1883
mqtt_user: ""
mqtt_password: ""
source_prefix: z2m_discovery
target_prefix: homeassistant
language: fr
log_payloads: false
```

- **language:** Dropdown in the add-on options: **`fr`**, **`de`**, or **`es`**, each matching `translations/<code>.json`. If a file were missing, the add-on would fall back to `fr.json` (all three files are shipped in 1.0.0).

Use the same MQTT credentials as Zigbee2MQTT if your broker requires authentication.

## Known limitations

- **Entity registry:** Home Assistant may keep **old entity names** already stored in the entity registry, even after discovery payloads change.
- **Existing devices:** You may need an **MQTT discovery refresh** or **removing the MQTT device / entities** in Home Assistant so names update; **Zigbee re-pairing is not required**.
- **Scope:** Only the explicit **`name`** field in MQTT discovery payloads is rewritten. Other keys (topics, `device`, `unique_id`, etc.) are left unchanged.

## Contributing translations

All strings are in JSON under **`translations/`** in the add-on package — for example `fr.json`, `de.json`, `es.json`. To improve or add a language:

1. Edit **`translations/<code>.json`** for an existing language (`fr`, `de`, `es`).
2. To add another language, add **`translations/<code>.json`**, extend the **`language`** list in **`config.yaml`** (`list(fr|de|es|…)`), and open a PR (no Python change required for new keys in existing files).
2. Use Zigbee2MQTT expose names or the English label as keys, for example:

```json
{
  "smart_temperature_control": "Contrôle intelligent de la température"
}
```

No Python changes are required for new keys or new language files. Open a pull request that only touches the JSON file(s).
