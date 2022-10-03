import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.siren import SirenEntity, SirenEntityFeature, ATTR_DURATION


from .core import XAALEntity, EntityFactory, MonitorDevice, async_setup_factory

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    return async_setup_factory(hass, config_entry, async_add_entities, Factory)


class Factory(EntityFactory):

    def new_entity(self, device: MonitorDevice) -> bool:
        if device.dev_type.startswith('siren.'):
            entity = Siren(device, self._bridge)
            self.add_entity(entity,device.address)
            return True
        return False


class Siren(XAALEntity, SirenEntity):

    @property
    def supported_features(self) -> int:
        return SirenEntityFeature.TURN_ON|SirenEntityFeature.TURN_OFF|SirenEntityFeature.DURATION

    def turn_on(self, **kwargs: Any) -> None:
        self.send_request('play')

    def turn_off(self, **kwargs: Any) -> None:
        self.send_request('stop')

