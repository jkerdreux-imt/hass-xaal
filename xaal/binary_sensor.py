from xaal.lib import helpers
import logging
import functools

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.const import STATE_ON, STATE_OFF

from .const import DOMAIN
from .core import XAALEntity, EntityFactory

_LOGGER = logging.getLogger(__name__)


class Factory(EntityFactory):

    def new_entity(self, device):
        entity = None

        if device.dev_type.startswith('motion.'):
            entity = Motion(device, self._bridge)

        if device.dev_type.startswith('contact.'):
            entity = Contact(device, self._bridge)

        if device.dev_type.startswith('switch.'):
            entity = Switch(device, self._bridge)

        if device.dev_type.startswith('button.'):
            entity = Button(device, self._bridge)

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


class Motion(XAALEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.MOTION

    @property
    def state(self):
        value = self._dev.attributes.get('presence', None)
        return STATE_ON if value else STATE_OFF


class Contact(XAALEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.OPENING

    @property
    def state(self):
        value = self._dev.attributes.get('detected', None)
        # return STATE_OPEN if value else STATE_CLOSED
        return STATE_ON if value else STATE_OFF


class Switch(XAALEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.POWER

    @property
    def state(self):
        value = self._dev.attributes.get('position', None)
        # return STATE_OPEN if value else STATE_CLOSED
        return STATE_ON if value else STATE_OFF


class Button(XAALEntity, BinarySensorEntity):

    @property
    def state(self):
        return False

    def click_event(self, click_type):
        # TODO change this sig, to hande several button types..
        _LOGGER.warning(f"Button event: {self.entity_id}")
        self.hass.bus.fire("xaal_event", {'entity_id': self.entity_id, "click_type": click_type})


    def handle_notification(self, msg):
        if msg.action == 'click':
            self.click_event('single')
        if msg.action == 'double_click':
            self.click_event('double')
