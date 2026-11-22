"""Config flow for Assist LLM (Deutsch)."""

from __future__ import annotations

from typing import Any

import probatio

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback

from .const import (
    API_NAME,
    CONF_KEEP_HISTORY_ON_FOLLOWUP,
    CONF_RESET_HISTORY,
    DEFAULT_KEEP_HISTORY_ON_FOLLOWUP,
    DEFAULT_RESET_HISTORY,
    DOMAIN,
)


class AssistLlmDeOptionsFlow(OptionsFlowWithReload):
    """Handle options for Assist LLM (Deutsch)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the integration options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        schema = probatio.Schema(
            {
                probatio.Required(
                    CONF_RESET_HISTORY,
                    default=options.get(CONF_RESET_HISTORY, DEFAULT_RESET_HISTORY),
                ): bool,
                probatio.Required(
                    CONF_KEEP_HISTORY_ON_FOLLOWUP,
                    default=options.get(
                        CONF_KEEP_HISTORY_ON_FOLLOWUP,
                        DEFAULT_KEEP_HISTORY_ON_FOLLOWUP,
                    ),
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


class AssistLlmDeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Assist LLM (Deutsch)."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> AssistLlmDeOptionsFlow:
        """Get the options flow for this handler."""
        return AssistLlmDeOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title=API_NAME, data={})

        return self.async_show_form(step_id="user")
