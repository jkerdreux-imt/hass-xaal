import logging
from typing import Any

from homeassistant.components.cover import CoverEntity, CoverDeviceClass, CoverEntityFeature, ATTR_POSITION


from .core import XAALEntity, EntityFactory, async_setup_factory

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    return async_setup_factory(hass, config_entry, async_add_entities, Factory)


class Factory(EntityFactory):

    def new_entity(self, device):
        entity = None
        
        if device.dev_type == 'shutter.basic':
            entity = Shutter(device, self._bridge)

        if device.dev_type == 'shutter.position':
            entity = ShutterPosition(device, self._bridge)

        if entity:
            self.add_entity(entity,device.address)
            return True
        return False


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
        if position:
            self.send_request('set_position',{'position':position})
