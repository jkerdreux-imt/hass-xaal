import logging

from typing import Literal

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.const import STATE_ON, STATE_OFF

from .bridge import XAALEntity, async_setup_factory
from xaal.lib import Message

_LOGGER = logging.getLogger(__name__)

# https://www.home-assistant.io/integrations/binary_sensor/

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback)  -> None:

    binding = {'motion.' : [Motion],
               'contact.': [Contact],
               'switch.' : [Switch],
               'button.' : [Button], }
    return async_setup_factory(hass, config_entry, async_add_entities, binding)


class XAALBinarySensorEntity(XAALEntity, BinarySensorEntity):

    @property
    def state(self) -> Literal["on", "off"] | None:
        try:
            attr = getattr(self,'_xaal_attribute')
            value = self.get_attribute(attr)
            return STATE_ON if value else STATE_OFF
        except:
            return None


class Motion(XAALBinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.MOTION
    _xaal_attribute = 'presence'


class Contact(XAALBinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.OPENING
    _xaal_attribute = 'detected'


class Switch(XAALBinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.POWER
    _xaal_attribute = 'position'


class Button(XAALBinarySensorEntity):

    @property
    def entity_registry_visible_default(self):
        return False

    def click_event(self, click_type):
        # TODO change this sig, to hande several button types..
        _LOGGER.warning(f"Button event: {self.entity_id}")
        self.hass.bus.fire("xaal_event", {'entity_id': self.entity_id, "click_type": click_type})

    def handle_notification(self, msg: Message):
        if msg.action == 'click':
            self.click_event('single')
        if msg.action == 'double_click':
            self.click_event('double')
