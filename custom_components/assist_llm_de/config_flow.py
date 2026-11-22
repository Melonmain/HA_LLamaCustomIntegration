"""Config flow for Assist LLM (Deutsch)."""

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import API_NAME, DOMAIN


class AssistLlmDeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Assist LLM (Deutsch)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title=API_NAME, data={})

        return self.async_show_form(step_id="user")
