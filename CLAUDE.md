# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository shape

This repo is a **Home Assistant add-on repository** (`repository.yaml` at the root, consumed by the HA add-on store), containing a single add-on under `z2m-discovery-translator/`. The add-on itself is a tiny Python MQTT bridge — there is no test suite, no linter, and no local build step: Home Assistant Supervisor builds the image from `z2m-discovery-translator/Dockerfile` on install.

## What the add-on does

Subscribes to `<source_prefix>/#` (default `z2m_discovery/#`), translates the `name` field of Zigbee2MQTT MQTT Discovery payloads using `translations/<language>.json`, and republishes to `<target_prefix>/#` (default `homeassistant/#`). Only the `name` field is rewritten — topics, `device`, `unique_id`, etc. are preserved. Empty payloads (MQTT discovery deletions) pass through untouched.

The user must reconfigure Zigbee2MQTT to publish discovery on `z2m_discovery` instead of the default `homeassistant` — see `README.md` and `z2m-discovery-translator/DOCS.md`.

## Translation pipeline (`run.py`)

Understanding this is key before editing translations or the matcher:

1. On startup, `load_translation_dict(language)` reads `translations/<lang>.json` (falls back to `fr.json` if the requested file is missing). Each key is stored both verbatim *and* under a `normalize()`-d form (`lowercase`, `[\s\-]+ → _`, strip non-`[a-z0-9_]`). That is why entries are normally added in **both** snake_case and space-separated forms — but the auto-normalization also means a single canonical form is enough if you do not care about in-string replacement (see step 3).
2. For each incoming component with a non-empty `name`, `translate_component()` calls `translate_name()`: an exact whole-name match (verbatim or normalized) wins outright; otherwise every known label found *inside* the name is replaced in place, longest label first (word-boundary, case-insensitive), and untranslated words are left intact. This is deliberate — a single matching word must **not** overwrite the whole name (the `Alarm siren duration → Alarm` bug). Components *without* a usable `name` fall back to `find_component_translation()`, which scans `object_id`, `unique_id`, the `*_topic` fields, and the topic for a translation to use as the name.
3. `translate_name()` returns the leftover untranslated word tokens; `log_missing_words()` prints each unknown word once (`Traduction manquante (<lang>) : [...]`) so missing entries are easy to spot and contribute. In-string replacement matches on word boundaries against the **raw** dict keys, so a multi-word English label still needs its space form to be substituted inside a longer name like `"Smart temperature control valve 1"`; single-word entries need only one form.
4. Both classic discovery (`<prefix>/<component>/.../config`) and device-based discovery (payload with a `components` dict) are handled — the latter iterates and translates each sub-component.

## Adding / editing translations

Pure JSON, no Python edits.

- Add to existing language: edit `z2m-discovery-translator/translations/{fr,de,es}.json`. Keep the dual `snake_case` + `space separated` entries for any multi-word label that may appear embedded in a longer `name`.
- Add a new language: create `translations/<code>.json` *and* extend the schema enum in `z2m-discovery-translator/config.yaml` (`language: list(fr|de|es|<new>)`); the option default lives just above. The runtime `sanitize_language()` only accepts `[a-z]{2}(-[a-z]{2})?`.
- Validate JSON before committing:
  ```bash
  python3 -c "import json; [json.load(open(f'z2m-discovery-translator/translations/{l}.json')) for l in ('fr','de','es')]"
  ```

## Releasing a new version

The Supervisor uses `config.yaml` `version:` to detect updates — bumping it is what triggers the "update available" flow for installed instances.

1. Bump `version:` in `z2m-discovery-translator/config.yaml`.
2. Add a section to `z2m-discovery-translator/CHANGELOG.md` (most recent on top, matching the existing terse style).
3. Commit with the version number as the commit subject (existing history is literally `1.0.0`, `1.0.1`). Tag `vX.Y.Z` and push both `main` and the tag.

## Runtime notes that have bitten before

- The Dockerfile launches `run.py` via `/usr/bin/with-contenv`. **Do not drop this** — s6-overlay does not propagate `SUPERVISOR_TOKEN` to the process otherwise, which breaks the Supervisor MQTT auto-config path (`load_supervisor_mqtt_service()`), forcing users to fill `mqtt_user` / `mqtt_password` manually.
- Supervisor MQTT credentials always win over `mqtt_user` / `mqtt_password` from options when the token is present.
- Translated payloads are published with `retain=True` — re-running the add-on against a fresh `target_prefix` will re-seed retained discovery, but stale entity names already in the HA entity registry are *not* fixed by republishing alone (users must remove the MQTT device or refresh discovery).
