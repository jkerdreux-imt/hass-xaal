

import asyncio
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import bridge
from .const import DOMAIN

PLATFORMS: list[str] = ["light", "switch", "sensor", "binary_sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # create the hub and load the platforms
    br = bridge.Bridge(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = br
    await br.wait_is_ready()
    print("READY")
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # stop xAAL tasks before removing reference
    # FIXME: some tasks never ends: RecvQ, Timers
    await hass.data[DOMAIN][entry.entry_id].engine.stop()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
