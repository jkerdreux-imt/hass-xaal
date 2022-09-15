import logging
from homeassistant.components.switch import SwitchEntity, DEVICE_CLASS_OUTLET


from .const import DOMAIN
from .core import XAALEntity, EntryHandler

_LOGGER = logging.getLogger(__name__)


class Handler(EntryHandler):

    def new_entity(self, device):
        if device.dev_type.startswith('powerrelay.'):
            entity = PowerRelay(device, self._bridge)
            self.add_entity(entity,device.address)
            return True
        return False

async def async_setup_entry(hass, config_entry, async_add_entities):
    bridge = hass.data[DOMAIN][config_entry.entry_id]
    handler = Handler(bridge, async_add_entities)
    for dev in bridge._mon.devices:
        handler.new_entity(dev)


class PowerRelay(XAALEntity, SwitchEntity):
    _attr_device_class = DEVICE_CLASS_OUTLET

    @property
    def is_on(self) -> bool | None:
        return self._dev.attributes.get('power', None)

    def turn_on(self, **kwargs) -> None:
        _LOGGER.debug(f"turn_on: {kwargs}")
        self.send_request('turn_on')

    def turn_off(self, **kwargs) -> None:
        self.send_request('turn_off')
