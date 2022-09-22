import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass

from homeassistant.const import (
    TEMP_CELSIUS,
    PERCENTAGE,
    POWER_WATT,
)

from .const import DOMAIN
from .core import XAALEntity, EntityFactory


_LOGGER = logging.getLogger(__name__)


class Factory(EntityFactory):

    def new_entity(self, device):
        entity = None
        if device.dev_type.startswith('thermometer.'):
            entity = Thermometer(device, self._bridge)

        if device.dev_type.startswith('hygrometer.'):
            entity = Hygrometer(device, self._bridge)

        if device.dev_type.startswith('battery.'):
            entity = Battery(device, self._bridge)

        if device.dev_type.startswith('powermeter.'):
            entity = PowerMeter(device, self._bridge)

        if device.dev_type.startswith('wifimeter.'):
            entity = WifiMeter(device, self._bridge)

        if entity:
            self.add_entity(entity, device.address)
            return True
        return False


async def async_setup_entry(hass, config_entry, async_add_entities):
    bridge = hass.data[DOMAIN][config_entry.entry_id]
    factory = Factory(bridge, async_add_entities)
    for dev in bridge._mon.devices:
        if dev.is_ready():
            factory.new_entity(dev)


class Thermometer(XAALEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = TEMP_CELSIUS

    @property
    def state(self):
        return self._dev.attributes.get('temperature', None)


class Hygrometer(XAALEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def state(self):
        return self._dev.attributes.get('humidity', None)


class Battery(XAALEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_unit_of_measurement = PERCENTAGE

    @property
    def state(self):
        return self._dev.attributes.get('level', None)


class PowerMeter(XAALEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = POWER_WATT

    @property
    def state(self):
        return self._dev.attributes.get('power', None)


class WifiMeter(XAALEntity, SensorEntity):
    _attr_device_class: SensorDeviceClass.SIGNAL_STRENGTH

    @property
    def state(self):
        return self._dev.attributes.get('rssi', None)
