
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from xaal.lib import tools
from .bridge import Bridge
from .const import DOMAIN, CONF_DB_SERVER
from . import utils


_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["light", "switch", "sensor", "binary_sensor", "cover", "siren"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # create the hub and load the platforms
    addr = entry.data.get(CONF_DB_SERVER)
    db_server = tools.get_uuid(addr)

    bridge = Bridge(hass, db_server)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = bridge

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    # await bridge.wait_is_ready()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # stop xAAL tasks before removing reference
    # FIXME: some tasks never ends: RecvQ, Timers
    await hass.data[DOMAIN][entry.entry_id]._eng.stop()
    _LOGGER.debug("Unloading xAAL platforms")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    else:
        _LOGGER.error("Unable to unload xAAL platforms")
    return unload_ok


async def async_remove_config_entry_device(hass: HomeAssistant, entry: ConfigEntry, device_entry: DeviceEntry) -> bool:
    """Remove a config entry from a device."""
    bridge = hass.data[DOMAIN][entry.entry_id]
    (domain, dev_ident) = utils.extract_device_identifiers(device_entry.identifiers)
    bridge.ha_remove_device(dev_ident)
    return True

