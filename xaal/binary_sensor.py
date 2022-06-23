import logging
import functools

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.const import STATE_ON, STATE_OFF

from .const import DOMAIN
from .core import XAALEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities ):
    bridge = hass.data[DOMAIN][config_entry.entry_id]
    for dev in bridge._mon.devices:
        entity = None

        if dev.dev_type.startswith('motion.'):
            entity = Motion(dev,bridge)

        if dev.dev_type.startswith('contact.'):
            entity = Contact(dev,bridge)

        if dev.dev_type.startswith('switch.'):
            entity = Switch(dev,bridge)

        if dev.dev_type.startswith('button.'):
            entity = Button(dev,bridge)

        if entity:
            async_add_entities([entity])
            bridge.add_entity(dev.address, entity)

    ptr = functools.partial(buttons_handler,bridge)
    bridge._eng.subscribe(ptr)


def buttons_handler(bridge,msg):
    if msg.dev_type.startswith('button.'):
        entity = bridge._entities.get(msg.source, None)
        if entity:
            entity.fire_event("xaal.click")


class Motion(XAALEntity,  BinarySensorEntity):
    device_class = BinarySensorDeviceClass.MOTION
    
    @property
    def unique_id(self) -> str:
        return f'binary_sensor.{str(self._dev.address)}_motion'

    @property
    def state(self):
        value =self._dev.attributes.get('presence',None) 
        return STATE_ON if value else STATE_OFF


class Contact(XAALEntity,  BinarySensorEntity):
    device_class = BinarySensorDeviceClass.OPENING
    
    @property
    def unique_id(self) -> str:
        return f'binary_sensor.{str(self._dev.address)}_contact'

    @property
    def state(self):
        value = self._dev.attributes.get('detected',None)
        #return STATE_OPEN if value else STATE_CLOSED
        return STATE_ON if value else STATE_OFF


class Switch(XAALEntity,  BinarySensorEntity):
    
    @property
    def unique_id(self) -> str:
        return f'binary_sensor.{str(self._dev.address)}_switch'

    @property
    def state(self):
        value = self._dev.attributes.get('position',None)
        #return STATE_OPEN if value else STATE_CLOSED
        return STATE_ON if value else STATE_OFF


class Button(XAALEntity,  BinarySensorEntity):
    
    @property
    def unique_id(self) -> str:
        return f'binary_sensor.{str(self._dev.address)}_button'

    @property
    def state(self):
        return False

    def fire_event(self,event):
        _LOGGER.warning(f"Button event: {event} {self.entity_id}")
        self.hass.bus.fire("xaal_event", {'entity_id': self.entity_id, "click_type": "single"})