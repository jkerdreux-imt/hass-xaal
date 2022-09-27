import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.switch import SwitchEntity, DEVICE_CLASS_OUTLET

from .core import EntityFactory, XAALEntity, MonitorDevice, async_setup_factory

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    return async_setup_factory(hass, config_entry, async_add_entities, Factory)


class Factory(EntityFactory):

    def new_entity(self, device: MonitorDevice) -> bool:
        if device.dev_type.startswith('powerrelay.'):
            entity = PowerRelay(device, self._bridge)
            self.add_entity(entity,device.address)
            return True
        return False


class PowerRelay(XAALEntity, SwitchEntity):
    _attr_device_class = DEVICE_CLASS_OUTLET

    @property
    def is_on(self) -> bool | None:
        return self.get_attribute('power')

    def turn_on(self, **kwargs) -> None:
        _LOGGER.debug(f"turn_on: {kwargs}")
        self.send_request('turn_on')

    def turn_off(self, **kwargs) -> None:
        self.send_request('turn_off')
