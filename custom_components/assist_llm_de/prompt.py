"""German prompt builder for the Assist LLM (Deutsch) integration."""

from operator import attrgetter
from typing import Any

from homeassistant.components.homeassistant import async_should_expose
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    floor_registry as fr,
    intent,
    llm,
)
from homeassistant.util import yaml as yaml_util

CALENDAR_DOMAIN = "calendar"
SCRIPT_DOMAIN = "script"

NO_ENTITIES_PROMPT_DE = (
    "Nur wenn der Nutzer ein Gerät steuern möchte, weise ihn darauf hin, "
    "in Home Assistant Entitäten für den Sprachassistenten freizugeben."
)

DYNAMIC_CONTEXT_PROMPT_DE = (
    "Du bist dafür ausgestattet, Fragen zum aktuellen Zustand des Zuhauses zu "
    "beantworten, indem du den Live-Kontext abrufst. Das ist eine Hauptfunktion. "
    "Behaupte nicht, dass dir diese Funktion fehlt, wenn die Frage Live-Daten erfordert.\n"
    "Wenn der Nutzer nach der Existenz oder Art eines Geräts fragt "
    '(z. B. "Habe ich Lichter im Schlafzimmer?"): Antworte anhand des statischen '
    "Kontexts unten.\n"
    "Wenn der Nutzer nach dem AKTUELLEN Zustand, Wert oder Modus fragt "
    '(z. B. "Ist das Schloss verriegelt?", "Ist der Ventilator an?", '
    '"In welchem Modus ist das Thermostat?", "Wie ist die Außentemperatur?"):\n'
    "    1. Erkenne, dass Live-Daten erforderlich sind.\n"
    "    2. Du MUSST das bereitgestellte Werkzeug {live_context_tool} verwenden, "
    "um den Live-Kontext abzurufen. Dieses Werkzeug liefert die benötigten "
    "Echtzeitinformationen (wie Temperatur vom lokalen Wetter, Schlossstatus usw.).\n"
    "    3. Nutze die Antwort des Werkzeugs, um dem Nutzer präzise zu antworten "
    "und den tatsächlich zurückgegebenen Wert oder Zustand zu nennen.\n"
    "Bei allgemeinen Wissensfragen, die nicht das Zuhause betreffen: "
    "Antworte wahrheitsgemäß aus deinem eigenen Wissen.\n"
)

STATIC_CONTEXT_HEADER_DE = (
    "Statischer Kontext: Übersicht der Bereiche und Geräte in diesem Smart Home:"
)

DEVICE_CONTROL_TOOL_USAGE_PROMPT_DE = (
    "Rufe zum Steuern von Home Assistant immer die Intent-Werkzeuge auf. "
    "Verwende {turn_on_tool} zum Verriegeln und {turn_off_tool} zum Entriegeln eines Schlosses. "
    "Gib beim Steuern eines Geräts bevorzugt nur name und domain an. "
    "Gib beim Steuern eines Bereichs bevorzugt nur area (Bereichsname) und domain an."
)


def _get_effective_device_area_id(
    hass: HomeAssistant, device_entry: dr.DeviceEntry
) -> str | None:
    """Resolve effective area ID for a device across HA versions."""
    effective_area_fn = getattr(dr, "async_get_effective_area_id", None)
    if callable(effective_area_fn):
        return effective_area_fn(hass, device_entry)
    return device_entry.area_id


def _get_exposed_entities(
    hass: HomeAssistant, assistant: str
) -> dict[str, dict[str, Any]]:
    """Collect exposed entities without live states."""
    try:
        from homeassistant.components.homeassistant.llm import (  # noqa: PLC0415
            async_get_exposed_entities,
        )

        return async_get_exposed_entities(hass, assistant, include_state=False)
    except ImportError:
        pass

    area_registry = ar.async_get(hass)
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    entities: dict[str, dict[str, Any]] = {}
    for state in sorted(hass.states.async_all(), key=attrgetter("name")):
        if not async_should_expose(hass, assistant, state.entity_id):
            continue
        if state.domain in (CALENDAR_DOMAIN, SCRIPT_DOMAIN):
            continue

        entity_entry = entity_registry.async_get(state.entity_id)
        device_entry = (
            device_registry.async_get(entity_entry.device_id)
            if entity_entry is not None and entity_entry.device_id is not None
            else None
        )
        names = intent.async_get_entity_aliases(hass, entity_entry, state=state)
        area_names: list[str] = []

        if entity_entry is not None:
            area_id: str | None = None
            if entity_entry.area_id is not None:
                area_id = entity_entry.area_id
            elif device_entry is not None:
                area_id = _get_effective_device_area_id(hass, device_entry)

            if area_id is not None and (
                area_entry := area_registry.async_get_area(area_id)
            ) is not None:
                area_names.append(area_entry.name)
                area_names.extend(sorted(area_entry.aliases))

        info: dict[str, Any] = {
            "names": ", ".join(names),
            "domain": state.domain,
        }
        if area_names:
            info["areas"] = ", ".join(area_names)
        entities[state.entity_id] = info

    return entities


def _device_supports_timers(
    hass: HomeAssistant, device_id: str | None, tools: list[llm.Tool]
) -> bool:
    """Return whether the calling device supports timers."""
    if device_id is None:
        return False
    try:
        from homeassistant.components.intent.timers import (  # noqa: PLC0415
            async_device_supports_timers,
        )

        return async_device_supports_timers(hass, device_id)
    except ImportError:
        return any(tool.name.endswith("HassStartTimer") for tool in tools)


def _get_exposed_domains(hass: HomeAssistant, assistant: str) -> set[str]:
    """Return domains of all entities exposed to the assistant."""
    return {
        state.domain
        for state in hass.states.async_all()
        if async_should_expose(hass, assistant, state.entity_id)
    }


def _get_device_area_and_floor(
    hass: HomeAssistant, device_id: str | None
) -> tuple[ar.AreaEntry | None, fr.FloorEntry | None]:
    """Return the area and floor of the requesting device, if known."""
    if not device_id:
        return None, None
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return None, None
    device_area_id = _get_effective_device_area_id(hass, device)
    if not device_area_id:
        return None, None
    area = ar.async_get(hass).async_get_area(device_area_id)
    if area is None:
        return None, None
    floor = (
        fr.async_get(hass).async_get_floor(area.floor_id)
        if area.floor_id
        else None
    )
    return area, floor


def build_german_assist_prompt(
    hass: HomeAssistant, llm_context: llm.LLMContext, tools: list[llm.Tool]
) -> str:
    """Build a complete German clone of the Assist API prompt."""
    live_context_tool = next(
        (tool.name for tool in tools if tool.name.endswith("GetLiveContext")),
        "homeassistant__GetLiveContext",
    )
    turn_on_tool = next(
        (tool.name for tool in tools if tool.name.endswith("HassTurnOn")),
        "intent__HassTurnOn",
    )
    turn_off_tool = next(
        (tool.name for tool in tools if tool.name.endswith("HassTurnOff")),
        "intent__HassTurnOff",
    )
    schedule_tool = next(
        (tool.name for tool in tools if tool.name.endswith("schedule_command")),
        None,
    )

    prompts: list[str] = []

    exposed_entities = (
        _get_exposed_entities(hass, llm_context.assistant)
        if llm_context.assistant
        else {}
    )
    if exposed_entities:
        prompts.append(
            "\n".join(
                [
                    DYNAMIC_CONTEXT_PROMPT_DE.format(
                        live_context_tool=live_context_tool
                    ),
                    STATIC_CONTEXT_HEADER_DE,
                    yaml_util.dump(list(exposed_entities.values())),
                ]
            )
        )
    else:
        prompts.append(NO_ENTITIES_PROMPT_DE)

    exposed_domains = (
        _get_exposed_domains(hass, llm_context.assistant)
        if llm_context.assistant
        else set()
    )
    if exposed_domains:
        prompts.append(
            DEVICE_CONTROL_TOOL_USAGE_PROMPT_DE.format(
                turn_on_tool=turn_on_tool,
                turn_off_tool=turn_off_tool,
            )
        )

        area, floor = _get_device_area_and_floor(hass, llm_context.device_id)
        if area and floor:
            area_prompt = (
                f"Du befindest dich im Bereich {area.name} (Etage {floor.name}) "
                "und alle allgemeinen Befehle wie 'Mach das Licht an' sollen sich "
                "auf diesen Bereich beziehen."
            )
        elif area:
            area_prompt = (
                f"Du befindest dich im Bereich {area.name} und alle allgemeinen "
                "Befehle wie 'Mach das Licht an' sollen sich auf diesen Bereich beziehen."
            )
        else:
            area_prompt = (
                "Wenn ein Nutzer darum bittet, alle Geräte eines bestimmten Typs "
                "einzuschalten, bitte den Nutzer um Angabe eines Bereichs, es sei denn, "
                "es gibt nur ein Gerät dieses Typs."
            )
        prompts.append(area_prompt)

        supports_timers = _device_supports_timers(hass, llm_context.device_id, tools)
        if not supports_timers:
            timer_prompt = "Dieses Gerät kann keine Timer starten."
            if schedule_tool:
                timer_prompt += (
                    f" Es kann aber dennoch einen Befehl später mit {schedule_tool} ausführen."
                )
            prompts.append(timer_prompt)

    return "\n".join(prompts)
