
import voluptuous as vol
from homeassistant import config_entries
import logging

# from . import bridge

from .const import DOMAIN  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)
DATA_SCHEMA = vol.Schema({})


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None):

        # no user input right now, so we just show the empty form
        errors = {}

        # br = bridge.Bridge(self.hass)
        # r = await br.wait_is_ready()
        # print(f"READY={r}")
        # br.engine.stop()

        # if we have some user_input let's start
        if user_input is not None:
            try:
                return self.async_create_entry(title="Bridge", data=user_input)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
        # else we show the empty form
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)
