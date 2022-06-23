import logging


from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN
from .core import XAALEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities ):
    bridge = hass.data[DOMAIN][config_entry.entry_id]
    for dev in bridge._mon.devices:
        entity = None
        if dev.dev_type.startswith('powerrelay.'):
            entity = PowerRelay(dev,bridge)
        
        if entity:
            async_add_entities([entity])
            bridge.add_entity(dev.address, entity)

class PowerRelay(XAALEntity,SwitchEntity):

    @property
    def unique_id(self) -> str:
        return f'switch.{str(self._dev.address)}'

    @property
    def is_on(self) -> bool | None:
        return self._dev.attributes.get('power',None)

    def turn_on(self, **kwargs) -> None:
        _LOGGER.debug(f"turn_on: {kwargs}")
        self.send_request('turn_on')

    def turn_off(self, **kwargs) -> None:
        self.send_request('turn_off')
