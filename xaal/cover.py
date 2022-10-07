import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.cover import CoverEntity, CoverDeviceClass, CoverEntityFeature, ATTR_POSITION

from .bridge import XAALEntity, async_setup_factory

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    binding = { 'shutter.position' : [ShutterPosition], 
                'shutter.'         : [Shutter,] }
    return async_setup_factory(hass, config_entry, async_add_entities, binding)


class Shutter(XAALEntity, CoverEntity):
    _attr_device_class= CoverDeviceClass.SHUTTER

    @property
    def supported_features(self) -> int:
        return CoverEntityFeature.OPEN|CoverEntityFeature.CLOSE|CoverEntityFeature.STOP

    @property
    def is_closed(self) -> bool | None:
        return None

    def open_cover(self, **kwargs: Any) -> None:
        self.send_request('up')

    def close_cover(self, **kwargs: Any) -> None:
        self.send_request('down')

    def stop_cover(self, **kwargs: Any) -> None:
        self.send_request('stop')

class ShutterPosition(Shutter):

    @property
    def supported_features(self) -> int:
        return super().supported_features|CoverEntityFeature.SET_POSITION

    @property
    def is_closed(self) -> bool | None:
        if self.get_attribute('position') == 0:
            return True
        return False

    @property
    def is_closing(self) -> bool | None:
        if self.get_attribute('action') == 'down':
            return True
        return False
    
    @property
    def is_opening(self) -> bool | None:
        if self.get_attribute('action') == 'up':
            return True
        return False

    @property
    def current_cover_position(self) -> int | None:
        return self.get_attribute('position')

    def set_cover_position(self, **kwargs: Any) -> None:
        position = kwargs.get(ATTR_POSITION, None)
        if position != None:
            self.send_request('set_position',{'position':position})
