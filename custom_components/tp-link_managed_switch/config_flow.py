"""Config flow for Hello World integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# This is the schema that used to display the UI to the user. This simple
# schema has a single required host field, but it could include a number of fields
# such as username, password etc. See other components in the HA core code for
# further examples.
# Note the input displayed to the user will be translated. See the
# translations/<lang>.json file and strings.json. See here for further information:
# https://developers.home-assistant.io/docs/config_entries_config_flow_handler/#translations
# At the time of writing I found the translations created by the scaffold didn't
# quite work as documented and always gave me the "Lokalise key references" string
# (in square brackets), rather than the actual translated value. I did not attempt to
# figure this out or look further into it.
DATA_SCHEMA = vol.Schema(
    {
        ("host"): str,
        ("username"): str,
        ("password"): str
    }
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    data: Optional[Dict[str, Any]]
    """Handle a config flow for Hello World."""

    VERSION = 1
    # Pick one of the available connection classes in homeassistant/config_entries.py
    # This tells HA if it should be asking for updates, or it'll be notified of updates
    # automatically. This example uses PUSH, as the dummy hub will notify HA of
    # changes.
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL 

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        _LOGGER.info("1-----------------------------------------------------------------1")
        """Handle the initial step."""
        if user_input is not None:
            self.data = user_input
            return await self.async_step_finish()

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA
        )

    async def async_step_finish(self, user_input: Optional[Dict[str, Any]] = None):
        return self.async_create_entry(title="TP Link Network Switch", data=self.data)

