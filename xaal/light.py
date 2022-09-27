import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_HS_COLOR, ATTR_COLOR_TEMP, LightEntity, ColorMode
from homeassistant.util import color as color_util

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
        if device.dev_type.startswith('lamp.'):
            entity = Lamp(device, self._bridge)
            self.add_entity(entity,device.address)
            return True
        return False


class Lamp(XAALEntity, LightEntity):

    @property
    def supported_color_modes(self) -> str:
        dev_type = self._dev.dev_type
        if dev_type in ['lamp.color']:
            return {"brightness", "hs", "color_temp"}
        if dev_type in ['lamp.dimmer']:
            return {"brightness"}

    @property
    def color_mode(self) -> ColorMode | str | None:
        mode = self.get_attribute('mode')
        if mode == 'white':
            return 'color_temp'
        elif mode == 'color':
            return 'hs'
        # FIXME: xAAL don't have this kind of lamp
        return 'brightness'

    @property
    def brightness(self) -> int | None:
        brightness = self.get_attribute('brightness',0)
        return round(255 * (int(brightness) / 100))


    @property
    def hs_color(self) -> tuple[float, float] | None:
        hsv = self.get_attribute('hsv')
        if hsv:
            return (hsv[0], hsv[1]*100)

    @property
    def color_temp(self) -> int | None:
        white_temp = self.get_attribute('white_temperature')
        if white_temp:
            return color_util.color_temperature_kelvin_to_mired(white_temp)

    @property
    def is_on(self) -> bool | None:
        return self.get_attribute('light')

    def turn_on(self, **kwargs) -> None:
        color = kwargs.get(ATTR_HS_COLOR, None)
        brightness = kwargs.get(ATTR_BRIGHTNESS, None)
        color_temp = kwargs.get(ATTR_COLOR_TEMP, None)

        # FIX: support duration
        # duration   = kwargs.get('duration',None)

        if color_temp:
            white_temp = color_util.color_temperature_mired_to_kelvin(color_temp)
            self.send_request('set_white_temperature', {'white_temperature': white_temp})

        if brightness:
            brightness = int(brightness / 255 * 100)
            self.send_request('set_brightness', {'brightness': brightness})

        if color:
            h = int(color[0])
            s = color[1] / 100
            v = self.get_attribute('brightness', 100) / 100
            self.send_request('set_hsv', {'hsv': [h, s, v]})

        # if not self.is_on:
        self.send_request('turn_on')

    def turn_off(self, **kwargs) -> None:
        self.send_request('turn_off')
