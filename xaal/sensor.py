import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity

from homeassistant import const

from .core import XAALEntity, EntityFactory, async_setup_factory


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    return async_setup_factory(hass, config_entry, async_add_entities, Factory)


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

        if device.dev_type.startswith('luxmeter.'):
            entity = LuxMeter(device, self._bridge)

        if entity:
            self.add_entity(entity, device.address)
            return True
        return False


class XAALSensorEntity(XAALEntity, SensorEntity):

    @property
    def native_value(self):
        target = getattr(self,'_xaal_attribute')
        return self.get_attribute(target)


class Thermometer(XAALSensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = const.TEMP_CELSIUS
    _xaal_attribute = 'temperature'


class Hygrometer(XAALSensorEntity):
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = const.PERCENTAGE
    _xaal_attribute = 'humidity'


class Battery(XAALSensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_unit_of_measurement = const.PERCENTAGE
    _xaal_attribute = 'level'


class PowerMeter(XAALSensorEntity):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = const.POWER_WATT
    _xaal_attribute = 'power'


class WifiMeter(XAALSensorEntity):
    _attr_device_class= SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = const.SIGNAL_STRENGTH_DECIBELS
    _xaal_attribute = 'rssi'


class LuxMeter(XAALSensorEntity):
    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_native_unit_of_measurement = const.LIGHT_LUX
    _xaal_attribute = 'illuminance'