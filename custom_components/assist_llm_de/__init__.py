"""The Assist LLM (Deutsch) integration."""

from typing import override

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, llm

from .const import (
    API_ID,
    API_NAME,
    CONF_KEEP_HISTORY_ON_FOLLOWUP,
    CONF_RESET_HISTORY,
    DEFAULT_KEEP_HISTORY_ON_FOLLOWUP,
    DEFAULT_RESET_HISTORY,
    DOMAIN,
    SERVICE_CLEAR_CONVERSATIONS,
)
from .prompt import build_german_assist_prompt
from .session import SessionResetManager, async_clear_idle_sessions

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


class GermanAssistAPI(llm.API):
    """Assist API wrapper that replaces the English core prompt with German."""

    def __init__(
        self, hass: HomeAssistant, session_manager: SessionResetManager
    ) -> None:
        """Initialize the German Assist API."""
        super().__init__(
            hass=hass,
            id=API_ID,
            name=API_NAME,
        )
        self._session_manager = session_manager

    @override
    async def async_get_api_instance(
        self, llm_context: llm.LLMContext
    ) -> llm.APIInstance:
        """Return an API instance with official Assist tools and a German prompt."""
        base_api = await llm.async_get_api(
            self.hass, llm.LLM_API_ASSIST, llm_context
        )
        german_prompt = build_german_assist_prompt(
            self.hass, llm_context, base_api.tools
        )
        self._session_manager.track_current_session()
        return llm.APIInstance(
            api=self,
            api_prompt=german_prompt,
            llm_context=llm_context,
            tools=base_api.tools,
            custom_serializer=base_api.custom_serializer,
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Assist LLM (Deutsch) from a config entry."""
    reset_history = bool(
        entry.options.get(CONF_RESET_HISTORY, DEFAULT_RESET_HISTORY)
    )
    keep_followup = bool(
        entry.options.get(
            CONF_KEEP_HISTORY_ON_FOLLOWUP, DEFAULT_KEEP_HISTORY_ON_FOLLOWUP
        )
    )

    session_manager = SessionResetManager(
        hass,
        reset_history=reset_history,
        keep_history_on_followup=keep_followup,
    )
    session_manager.async_start()
    entry.async_on_unload(session_manager.async_stop)

    unreg = llm.async_register_api(hass, GermanAssistAPI(hass, session_manager))
    entry.async_on_unload(unreg)

    if not hass.services.has_service(DOMAIN, SERVICE_CLEAR_CONVERSATIONS):

        async def _async_handle_clear_conversations(call: ServiceCall) -> None:
            async_clear_idle_sessions(hass)

        hass.services.async_register(
            DOMAIN,
            SERVICE_CLEAR_CONVERSATIONS,
            _async_handle_clear_conversations,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    other_loaded = [
        loaded
        for loaded in hass.config_entries.async_entries(DOMAIN)
        if loaded.entry_id != entry.entry_id and loaded.state is ConfigEntryState.LOADED
    ]
    if not other_loaded:
        hass.services.async_remove(DOMAIN, SERVICE_CLEAR_CONVERSATIONS)
    return True
