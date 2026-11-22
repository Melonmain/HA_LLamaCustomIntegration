"""The Assist LLM (Deutsch) integration."""

from typing import override

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, llm

from .const import API_ID, API_NAME, DOMAIN
from .prompt import build_german_assist_prompt

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


class GermanAssistAPI(llm.API):
    """Assist API wrapper that replaces the English core prompt with German."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the German Assist API."""
        super().__init__(
            hass=hass,
            id=API_ID,
            name=API_NAME,
        )

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
        return llm.APIInstance(
            api=self,
            api_prompt=german_prompt,
            llm_context=llm_context,
            tools=base_api.tools,
            custom_serializer=base_api.custom_serializer,
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Assist LLM (Deutsch) from a config entry."""
    unreg = llm.async_register_api(hass, GermanAssistAPI(hass))
    entry.async_on_unload(unreg)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True
