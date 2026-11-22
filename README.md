# Assist LLM (Deutsch)

Eine schlanke Home Assistant Custom Integration (über HACS installierbar), die eine deutsche LLM-API (`Assist (Deutsch)`) bereitstellt.

Sie behält sämtliche Werkzeuge (Tools) der offiziellen Home-Assistant-Assist-API bei (`GetLiveContext`, Intent-Steuerung, Timer, Einkaufsliste, Mediensteuerung, Skripte, Kalender usw.), ersetzt aber die englischen Core-Prompt-Texte (`DYNAMIC_CONTEXT_PROMPT`, `Static Context`, `DEVICE_CONTROL_TOOL_USAGE_PROMPT`, Bereichs- und Timer-Hinweise) vollständig durch deutsche Versionen — ganz ohne Fork oder Rebase der offiziellen `llama.cpp`-Integration.

Zusätzlich setzt die Integration abgeschlossene Gespräche automatisch zurück, damit die nächste Anfrage direkt mit einer frischen Konversations-ID ohne alten Verlauf startet (anstatt 5 Minuten auf den Home-Assistant-Session-Timeout zu warten). Stellt der Assistent eine Rückfrage (`?`), bleibt der Verlauf für die Antwort erhalten und wird erst danach gelöscht.

## Installation über HACS

1. Öffne **HACS** in Home Assistant.
2. Wähle oben rechts das Dreipunkt-Menü → **Benutzerdefinierte Repositories**.
3. Füge diese Repository-URL hinzu:
   `https://github.com/Melonmain/HA_LLamaCustomIntegration`
4. Wähle als Kategorie **Integration** und klicke auf **Hinzufügen**.
5. Suche in HACS nach **Assist LLM (Deutsch)**, lade die Integration herunter und starte Home Assistant anschließend neu.

## Einrichtung

1. Gehe zu **Einstellungen → Geräte & Dienste → Integration hinzufügen** und suche nach **Assist LLM (Deutsch)** (ein Bestätigungsschritt).
2. Öffne die Konfiguration deiner LLM-Integration (z. B. **llama.cpp**, **Ollama** oder **OpenAI Conversation**).
3. Wähle unter **Home Assistant steuern** (LLM-API) **nur** `Assist (Deutsch)` aus und **deaktiviere** die eingebaute englische `Assist`- bzw. `Gerätesteuerung`-API (sonst kombiniert Home Assistant beide APIs mit englischen Zwischenüberschriften).
4. Lasse deinen eigenen deutschen System-Prompt gesetzt (nicht komplett leeren, sonst verwendet Home Assistant Core seinen englischen Standard-Fallback).

## Optionen & Aktion

Über **Einstellungen → Geräte & Dienste → Assist LLM (Deutsch) → Konfigurieren** stehen folgende Optionen zur Verfügung (beide standardmäßig aktiviert):

- **Verlauf nach Antwort zurücksetzen:** Beendet die aktive Chat-Session sofort nach Abschluss der Antwort, sodass die nächste Anfrage eine neue `conversation_id` erhält.
- **Verlauf bei Rückfragen beibehalten:** Endet die Antwort des Assistenten mit einer Rückfrage (`?`), bleibt die Session bis zur Antwort des Nutzers erhalten und wird danach zurückgesetzt.

Zusätzlich steht die Aktion **`assist_llm_de.clear_conversations`** bereit, um alle aktuell inaktiven Home-Assistant-Gesprächssitzungen jederzeit manuell oder per Automation zu leeren.

## Herkunft & Lizenz

- Basiert auf der offiziellen `AssistAPI`-Prompt-Struktur aus [home-assistant/core](https://github.com/home-assistant/core) (`homeassistant/components/homeassistant/llm.py` und `homeassistant/components/intent/llm.py`).
- Die lokalen Brand-Icons unter `custom_components/assist_llm_de/brand/` stammen aus [home-assistant/brands](https://github.com/home-assistant/brands/tree/master/core_integrations/llama_cpp).
- Veröffentlicht unter der [Apache License 2.0](LICENSE).
