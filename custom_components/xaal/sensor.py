import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant import const
from homeassistant import util

from .bridge import XAALEntity, async_setup_factory
from .const import XAAL_TTS_SCHEMA


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    binding = {
        'thermometer.': [Thermometer],
        'hygrometer.': [Hygrometer],
        'barometer.': [Barometer],
        'battery.': [Battery],
        'powermeter.extended': [PowerMeter, EnergyMeter, CurrentMeter, VoltMeter],
        'ampmeter.': [CurrentMeter],
        'powermeter.': [PowerMeter, EnergyMeter],
        'voltmeter.': [VoltMeter],
        'wifimeter.': [WifiMeter],
        'luxmeter.': [LuxMeter],
        'co2meter.': [CO2Meter],
        'soundmeter.': [SoundMeter],
        'linkquality.': [LinkQualityMeter],
        'gateway.': [GatewayEmbedded, GatewayInactive],
        'tts.': [TTS],
    }

    return async_setup_factory(hass, config_entry, async_add_entities, binding)


class XAALSensorEntity(XAALEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Any:
        target = getattr(self, '_xaal_attribute')
        return self.get_attribute(target)


class Thermometer(XAALSensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = const.UnitOfTemperature.CELSIUS
    _xaal_attribute = 'temperature'


class Hygrometer(XAALSensorEntity):
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = const.PERCENTAGE
    _xaal_attribute = 'humidity'


class Barometer(XAALSensorEntity):
    _attr_device_class = SensorDeviceClass.PRESSURE
    _attr_native_unit_of_measurement = const.UnitOfPressure.HPA
    _xaal_attribute = 'pressure'


class Battery(XAALSensorEntity):
    _attr_state_class = None
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = const.PERCENTAGE
    _xaal_attribute = 'level'


class PowerMeter(XAALSensorEntity):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = const.UnitOfPower.WATT
    _xaal_attribute = 'power'


class EnergyMeter(XAALSensorEntity):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = const.UnitOfEnergy.KILO_WATT_HOUR
    _xaal_attribute = 'energy'


class CurrentMeter(XAALSensorEntity):
    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_native_unit_of_measurement = const.UnitOfElectricCurrent.AMPERE
    _xaal_attribute = 'current'


class VoltMeter(XAALSensorEntity):
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = const.UnitOfElectricPotential.VOLT
    _xaal_attribute = 'voltage'


class WifiMeter(XAALSensorEntity):
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = const.SIGNAL_STRENGTH_DECIBELS
    _xaal_attribute = 'rssi'


class LuxMeter(XAALSensorEntity):
    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_native_unit_of_measurement = const.LIGHT_LUX
    _xaal_attribute = 'illuminance'


class CO2Meter(XAALSensorEntity):
    _attr_device_class = SensorDeviceClass.CO2
    _attr_native_unit_of_measurement = const.CONCENTRATION_PARTS_PER_MILLION
    _xaal_attribute = 'co2'


class SoundMeter(XAALSensorEntity):
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = const.SIGNAL_STRENGTH_DECIBELS
    _force_name = 'sound'
    _xaal_attribute = 'sound'
    _attr_icon: str | None = "mdi:music-circle-outline"


class LinkQualityMeter(XAALSensorEntity):
    # This device doesn't have device class because, signal strength is db/dbm
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = const.PERCENTAGE
    _attr_device_class = None
    _xaal_attribute = 'level'


# class Gateway(XAALSensorEntity):
#     _attr_native_unit_of_measurement = "embedded"
#     _attr_icon: str | None = "mdi:swap-horizontal"

#     @property
#     def native_value(self) -> Any:
#         embs = self.get_attribute("embedded")
#         return len(embs) if embs else 0

#     @property
#     def name(self) -> str | None:
#         return self._dev.description.get('product_id', 'gateway')


class GatewayEmbedded(XAALSensorEntity):
    _attr_icon = "mdi:swap-horizontal"
    _attr_native_unit_of_measurement = 'devices'
    _xaal_attribute = 'embedded'

    @property
    def native_value(self) -> int:
        embs = self.get_attribute('embedded')
        return len(embs) if embs else 0

    @property
    def name(self) -> str | None:
        return f"{self._dev.description.get('product_id', 'gateway')} embedded"


class GatewayInactive(XAALSensorEntity):
    _attr_icon = "mdi:alert-circle-outline"
    _attr_native_unit_of_measurement = 'devices'
    _xaal_attribute = 'inactive'

    @property
    def native_value(self) -> int:
        inactives = self.get_attribute('inactive')
        return len(inactives) if inactives else 0

    @property
    def name(self) -> str | None:
        return f"{self._dev.description.get('product_id', 'gateway')} inactive"


class TTS(XAALEntity):
    _attr_native_value = 1

    def setup(self):
        name = util.slugify(self.name)
        self._bridge.hass.services.async_register("notify", name, self.say, XAAL_TTS_SCHEMA)

    def say(self, service):
        msg = service.data['message'].template
        self.send_request('say', {'msg': msg})

    @property
    def name(self) -> str | None:
        return self._dev.description.get('info', 'tts')
