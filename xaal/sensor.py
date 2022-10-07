import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant import const

from .bridge import XAALEntity, EntityFactory, async_setup_factory

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    return async_setup_factory(hass, config_entry, async_add_entities, Factory)


class Factory(EntityFactory):

    @property
    def mapping(self):
        return {'thermometer.'  : [Thermometer ],
                'hygrometer.'   : [Hygrometer],
                'barometer.'    : [Barometer],
                'battery.'      : [Battery],
                'powermeter.'   : [PowerMeter,CurrentMeter, VoltMeter],
                'wifimeter.'    : [WifiMeter],
                'luxmeter.'     : [LuxMeter],
                'co2meter.'     : [CO2Meter],
                'soundmeter.'   : [SoundMeter],
                'gateway.'      : [Gateway],
                'tts.'          : [TTS],
               }

class XAALSensorEntity(XAALEntity, SensorEntity):

    @property
    def native_value(self) -> Any:
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


class Barometer(XAALSensorEntity):
    _attr_device_class = SensorDeviceClass.PRESSURE
    _attr_native_unit_of_measurement = const.PRESSURE_HPA
    _xaal_attribute = 'pressure'


class Battery(XAALSensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_unit_of_measurement = const.PERCENTAGE
    _xaal_attribute = 'level'


class PowerMeter(XAALSensorEntity):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = const.POWER_WATT
    _xaal_attribute = 'power'

class CurrentMeter(XAALSensorEntity):
    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_native_unit_of_measurement = const.ELECTRIC_CURRENT_AMPERE
    _xaal_attribute = 'current'

class VoltMeter(XAALSensorEntity):
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = const.ELECTRIC_POTENTIAL_VOLT
    _xaal_attribute = 'voltage'


class WifiMeter(XAALSensorEntity):
    _attr_device_class= SensorDeviceClass.SIGNAL_STRENGTH
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


class Gateway(XAALEntity, SensorEntity):
    _attr_native_unit_of_measurement = "embedded"
    _attr_icon: str | None = "mdi:swap-horizontal"

    @property
    def native_value(self) -> Any:
        embs = self.get_attribute("embedded")
        return len(embs) if embs else 0

    @property
    def name(self) -> str | None:
        return self._dev.description.get('product_id','gateway')


class TTS(XAALEntity,SensorEntity):
    _attr_native_value = 1

    def setup(self):
        import voluptuous as vol
        import homeassistant.helpers.config_validation as cv
        XAAL_NOTIF_SCHEMA =  vol.Schema(
                                {
                                    vol.Required("message"): cv.template,
                                    vol.Optional("title"): cv.template,
                                }
                            )
        self._bridge._hass.services.async_register("notify",self._dev.display_name, self.notify, schema=XAAL_NOTIF_SCHEMA)

    def notify(self, service):
        msg = service.data['message'].template
        self.send_request('say',{'msg':msg})