import logging

from homeassistant.components.sensor import SensorEntity

from homeassistant.const import (
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_HUMIDITY,
    TEMP_CELSIUS,
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_ILLUMINANCE,
    PERCENTAGE,
    POWER_WATT,
)


from .const import DOMAIN
from .core import XAALEntity


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities ):
    bridge = hass.data[DOMAIN][config_entry.entry_id]
    for dev in bridge._mon.devices:
        entity = None
        if dev.dev_type.startswith('thermometer.'):
            entity = Thermometer(dev,bridge)

        if dev.dev_type.startswith('hygrometer.'):
            entity = Hygrometer(dev,bridge)

        if dev.dev_type.startswith('battery.'):
            entity = Battery(dev,bridge)

        if dev.dev_type.startswith('powermeter.'):
            entity = PowerMeter(dev,bridge)

        if entity:
            async_add_entities([entity])
            bridge.add_entity(dev.address, entity)




class Thermometer(XAALEntity, SensorEntity):
    device_class = DEVICE_CLASS_TEMPERATURE
    _attr_unit_of_measurement = TEMP_CELSIUS

    @property
    def unique_id(self) -> str:
        return f'sensor.{str(self._dev.address)}_temperature'

    @property
    def name(self) -> str:
        return 'xAAL Thermometer:' + str(self._dev.address)

    @property
    def state(self):
        return self._dev.attributes.get('temperature',None)


class Hygrometer(XAALEntity, SensorEntity):
    device_class = DEVICE_CLASS_HUMIDITY
    _attr_unit_of_measurement = PERCENTAGE

    @property
    def unique_id(self) -> str:
        return f'sensor.{str(self._dev.address)}_humidity'

    @property
    def state(self):
        return self._dev.attributes.get('humidity',None)


class Battery(XAALEntity, SensorEntity):
    device_class = DEVICE_CLASS_BATTERY
    _attr_unit_of_measurement = PERCENTAGE

    @property
    def unique_id(self) -> str:
        return f'sensor.{str(self._dev.address)}_battery'

    @property
    def state(self):
        return self._dev.attributes.get('level',None)


class PowerMeter(XAALEntity, SensorEntity):
    device_class = DEVICE_CLASS_POWER
    _attr_unit_of_measurement = POWER_WATT

    @property
    def unique_id(self) -> str:
        return f'sensor.{str(self._dev.address)}_power'

    @property
    def state(self):
        return self._dev.attributes.get('power',None)

