import json
import os
import re
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import paho.mqtt.client as mqtt

OPTIONS_PATH = Path("/data/options.json")
TRANSLATIONS_DIR = Path("/translations")


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def sanitize_language(code: Any) -> str:
    """Code langue pour `translations/<code>.json` (évite chemins arbitraires)."""
    if not isinstance(code, str):
        return "fr"
    candidate = code.strip().lower()
    if not candidate or not re.fullmatch(r"[a-z]{2}(-[a-z]{2})?", candidate):
        print(f"Code langue invalide {code!r}, utilisation de « fr ».", flush=True)
        return "fr"
    return candidate


def load_translation_dict(language: str) -> Dict[str, Any]:
    """Charge `translations/<language>.json`, repli sur `fr.json` si absent."""
    path = TRANSLATIONS_DIR / f"{language}.json"
    try:
        return load_json(path)
    except FileNotFoundError:
        if language != "fr":
            fallback = TRANSLATIONS_DIR / "fr.json"
            if fallback.is_file():
                print(
                    f"Fichier de traduction absent ({path.name}) ; repli sur fr.json.",
                    flush=True,
                )
                return load_json(fallback)
        print(f"Fichier de traduction introuvable : {path}", flush=True)
        raise SystemExit(1) from None
    except json.JSONDecodeError as error:
        print(f"JSON invalide dans {path}: {error}", flush=True)
        raise SystemExit(1) from None


def supervisor_api_token() -> Optional[str]:
    """Token injecté par le Supervisor (legacy: HASSIO_TOKEN)."""
    for name in ("SUPERVISOR_TOKEN", "HASSIO_TOKEN"):
        raw = os.environ.get(name)
        if raw and str(raw).strip():
            return str(raw).strip()
    return None


def load_supervisor_mqtt_service():
    token = supervisor_api_token()

    if not token:
        print(
            "SUPERVISOR_TOKEN / HASSIO_TOKEN absents ; impossible d’appeler l’API Supervisor pour le service MQTT.",
            flush=True,
        )
        return None

    request = urllib.request.Request(
        "http://supervisor/services/mqtt",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if isinstance(payload, dict) and "data" in payload:
            payload = payload["data"]

        required = ["host", "port", "username", "password"]

        if not all(key in payload for key in required):
            print(f"Supervisor MQTT service response incomplete: {payload}", flush=True)
            return None

        return payload

    except Exception as error:
        print(f"Unable to read Supervisor MQTT service: {error}", flush=True)
        return None


def normalize(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None

    normalized = value.strip().lower()
    normalized = re.sub(r"[\s\-]+", "_", normalized)
    normalized = re.sub(r"[^a-z0-9_]+", "", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or None


options = load_json(OPTIONS_PATH)
language = sanitize_language(options.get("language", "fr"))
raw_translations = load_translation_dict(language)

# Keep exact keys and normalized keys (contributions = JSON uniquement, pas de Python).
TRANSLATIONS: Dict[str, str] = {}
for key, value in raw_translations.items():
    if not isinstance(key, str) or not isinstance(value, str):
        continue
    TRANSLATIONS[key] = value
    normalized_key = normalize(key)
    if normalized_key:
        TRANSLATIONS[normalized_key] = value

print(f"Traductions chargées : langue={language}, entrées={len(raw_translations)}", flush=True)

mqtt_service = load_supervisor_mqtt_service()

if mqtt_service:
    MQTT_HOST = mqtt_service["host"]
    MQTT_PORT = int(mqtt_service["port"])
    MQTT_USER = mqtt_service.get("username")
    MQTT_PASSWORD = mqtt_service.get("password")
    print("Using Home Assistant Supervisor MQTT service credentials", flush=True)
else:
    MQTT_HOST = options["mqtt_host"]
    MQTT_PORT = int(options["mqtt_port"])
    MQTT_USER = options.get("mqtt_user") or None
    MQTT_PASSWORD = options.get("mqtt_password") or None
    print("Using manual MQTT configuration", flush=True)
    if not supervisor_api_token():
        print(
            "Token Supervisor absent après chargement de l’environnement (hors Supervisor, ou image sans « with-contenv »). "
            "Renseignez mqtt_user / mqtt_password comme pour Zigbee2MQTT ou l’add-on Mosquitto.",
            flush=True,
        )
    if not (options.get("mqtt_user") or "").strip():
        print(
            "mqtt_user est vide : le broker refuse souvent la connexion (ex. code 5 « not authorized »). "
            "Ajoutez les identifiants MQTT configurés dans Mosquitto.",
            flush=True,
        )
SOURCE_PREFIX = options.get("source_prefix", "z2m_discovery").strip("/")
TARGET_PREFIX = options.get("target_prefix", "homeassistant").strip("/")
LOG_PAYLOADS = bool(options.get("log_payloads", False))


def split_topic_words(value: str) -> Iterable[str]:
    for part in re.split(r"[/\s]+", value):
        if part:
            yield part


def find_translation_from_value(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None

    if value in TRANSLATIONS:
        return TRANSLATIONS[value]

    normalized_value = normalize(value)
    if normalized_value and normalized_value in TRANSLATIONS:
        return TRANSLATIONS[normalized_value]

    return None


def replace_known_label_in_name(name: str) -> str:
    translated_name = find_translation_from_value(name)
    if translated_name:
        return translated_name

    result = name
    # Prefer replacing longer English labels first.
    for source, target in sorted(raw_translations.items(), key=lambda item: len(item[0]), reverse=True):
        if not isinstance(source, str) or not isinstance(target, str):
            continue
        if " " in source and source.lower() in result.lower():
            result = re.sub(re.escape(source), target, result, flags=re.IGNORECASE)
    return result


def candidate_values(component: Dict[str, Any], topic: str = "") -> Iterable[str]:
    for key in (
        "name",
        "object_id",
        "unique_id",
        "state_topic",
        "command_topic",
        "availability_topic",
        "json_attributes_topic",
        "value_template",
        "command_template",
        "state_value_template",
    ):
        value = component.get(key)
        if isinstance(value, str):
            yield value
            for word in split_topic_words(value):
                yield word

    if topic:
        yield topic
        for word in split_topic_words(topic):
            yield word


def find_component_translation(component: Dict[str, Any], topic: str = "") -> Optional[str]:
    for value in candidate_values(component, topic):
        translated = find_translation_from_value(value)
        if translated:
            return translated
    return None


def translate_component(component: Any, topic: str = "") -> None:
    if not isinstance(component, dict):
        return

    current_name = component.get("name")

    if isinstance(current_name, str):
        replaced_name = replace_known_label_in_name(current_name)
        if replaced_name != current_name:
            component["name"] = replaced_name
            return

    translated_name = find_component_translation(component, topic)
    if translated_name:
        component["name"] = translated_name


def translate_payload(raw_payload: bytes, topic: str) -> bytes:
    # Empty retained payload = MQTT discovery deletion.
    if raw_payload in (b"", None):
        return raw_payload

    try:
        payload = json.loads(raw_payload.decode("utf-8"))
    except Exception:
        return raw_payload

    if not isinstance(payload, dict):
        return raw_payload

    # Classic MQTT discovery: one component per config topic.
    translate_component(payload, topic)

    # Device-based MQTT discovery: multiple components in one payload.
    components = payload.get("components")
    if isinstance(components, dict):
        for component_key, component in components.items():
            translate_component(component, f"{topic}/{component_key}")

    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    if LOG_PAYLOADS:
        print(encoded.decode("utf-8"), flush=True)

    return encoded


# MQTT 3.1.1 CONNACK return codes (paho often surfaces these as int reason_code).
_MQTT_CONNACK_REFUSED = {
    1: "protocole non accepté",
    2: "identifiant client refusé",
    3: "serveur indisponible",
    4: "mauvais utilisateur ou mot de passe",
    5: "non autorisé (compte sans droit ou identifiants manquants / incorrects)",
}


def on_connect(client, userdata, flags, reason_code, properties=None):
    try:
        code = int(reason_code)
    except Exception:
        code = reason_code

    if code != 0:
        detail = _MQTT_CONNACK_REFUSED.get(code, "")
        suffix = f" — {detail}" if detail else ""
        print(f"MQTT connection refused, reason_code={reason_code}{suffix}", flush=True)
        if code in (4, 5):
            print(
                "Vérifiez mqtt_user et mqtt_password (identiques à Zigbee2MQTT ou à un utilisateur Mosquitto).",
                flush=True,
            )
        else:
            print("Consultez la configuration MQTT de l’add-on et l’état du broker.", flush=True)
        return

    print("Connected to MQTT successfully", flush=True)
    client.subscribe(f"{SOURCE_PREFIX}/#")
    print(f"Listening on {SOURCE_PREFIX}/#", flush=True)
    print(f"Publishing translated discovery to {TARGET_PREFIX}/#", flush=True)


def on_message(client, userdata, message):
    if not message.topic.startswith(SOURCE_PREFIX + "/"):
        return

    target_topic = TARGET_PREFIX + message.topic[len(SOURCE_PREFIX):]
    translated_payload = translate_payload(message.payload, message.topic)

    client.publish(
        target_topic,
        translated_payload,
        qos=message.qos,
        retain=True,
    )

    print(f"{message.topic} -> {target_topic}", flush=True)


try:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
except AttributeError:
    client = mqtt.Client()

if MQTT_USER:
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

client.on_connect = on_connect
client.on_message = on_message

while True:
    try:
        print(f"Connecting to MQTT {MQTT_HOST}:{MQTT_PORT}", flush=True)
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        client.loop_forever()
    except Exception as error:
        print(f"MQTT error: {error}; retrying in 5 seconds", flush=True)
        time.sleep(5)
