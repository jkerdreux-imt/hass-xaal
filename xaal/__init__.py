
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .bridge import Bridge
from .const import DOMAIN


_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["light", "switch", "sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # create the hub and load the platforms
    bridge = Bridge(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = bridge

    await bridge.wait_is_ready()
    _LOGGER.debug("xAAL Bridge READY")
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # stop xAAL tasks before removing reference
    # FIXME: some tasks never ends: RecvQ, Timers
    await hass.data[DOMAIN][entry.entry_id].engine.stop()
    _LOGGER.debug("Unloading xAAL platforms")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    else:
        _LOGGER.error("Unable to unload xAAL platforms")
    return unload_ok
