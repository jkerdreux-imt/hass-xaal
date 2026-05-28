import logging

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bridge import XAALEntity, async_setup_factory

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:

    binding = {'lamp.': [Lamp]}
    return async_setup_factory(hass, config_entry, async_add_entities, binding)


class Lamp(XAALEntity, LightEntity):
    @property
    def supported_color_modes(self) -> ColorMode | set[str] | None:
        dev_type = self._dev.dev_type
        if dev_type in ['lamp.color']:
            if self._supports_white_temperature():
                return {ColorMode.HS, ColorMode.COLOR_TEMP}
            return {ColorMode.HS}
        if dev_type in ['lamp.dimmer']:
            if self._supports_white_temperature():
                return {ColorMode.COLOR_TEMP}
            return {ColorMode.BRIGHTNESS}
        return {ColorMode.ONOFF}

    def _supports_white_temperature(self) -> bool:
        desc = self._dev.description
        unsupported_methods = desc.get('unsupported_methods', [])
        unsupported_attributes = desc.get('unsupported_attributes', [])
        return (
            'set_white_temperature' not in unsupported_methods
            and 'white_temperature' not in unsupported_attributes
        )

    @property
    def color_mode(self) -> ColorMode | str | None:
        dev_type = self._dev.dev_type
        mode = self.get_attribute('mode')

        if dev_type == 'lamp.color':
            if mode == 'white':
                return ColorMode.COLOR_TEMP
            if mode == 'color':
                return ColorMode.HS
            return ColorMode.HS if not self._supports_white_temperature() else ColorMode.COLOR_TEMP

        if dev_type == 'lamp.dimmer':
            if mode == 'white' and self._supports_white_temperature():
                return ColorMode.COLOR_TEMP
            return ColorMode.BRIGHTNESS

        return ColorMode.ONOFF

    @property
    def min_color_temp_kelvin(self) -> int | None:
        if ColorMode.COLOR_TEMP in self.supported_color_modes:
            return 2000
        return None

    @property
    def max_color_temp_kelvin(self) -> int | None:
        if ColorMode.COLOR_TEMP in self.supported_color_modes:
            return 6536
        return None

    @property
    def brightness(self) -> int | None:
        brightness = self.get_attribute('brightness', 0)
        return round(255 * (int(brightness) / 100))

    @property
    def hs_color(self) -> tuple[float, float] | None:
        hsv = self.get_attribute('hsv')
        if hsv:
            return (hsv[0], hsv[1] * 100)

    @property
    def color_temp_kelvin(self) -> int | None:
        white_temp = self.get_attribute('white_temperature')
        if white_temp:
            return white_temp

    @property
    def is_on(self) -> bool | None:
        return self.get_attribute('light')

    def turn_on(self, **kwargs) -> None:
        color = kwargs.get(ATTR_HS_COLOR, None)
        brightness = kwargs.get(ATTR_BRIGHTNESS, None)
        color_temp = kwargs.get(ATTR_COLOR_TEMP_KELVIN, None)

        # FIX: support duration
        # duration   = kwargs.get('duration',None)

        if color_temp:
            self.send_request('set_white_temperature', {'white_temperature': color_temp})

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
