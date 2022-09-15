
import asyncio

from homeassistant.core import HomeAssistant
from xaal.lib import AsyncEngine, tools, MessageType
from xaal.schemas import devices as schemas
from xaal.monitor import Monitor, Notification

import logging
_LOGGER = logging.getLogger(__name__)

#DB_SERVER = tools.get_uuid('d28fbc27-190f-4ee5-815a-fe05233400a2')
DB_SERVER = tools.get_uuid('9064ccbc-84ea-11e8-80cc-82ed25e6aaaa')
# DB_SERVER = tools.get_uuid('d28fbc27-190f-4ee5-815a-fe05233400a2')


def filter_msg(msg):
    if msg.source == DB_SERVER:
        return True
    if msg.dev_type.startswith('lamp.'):
        return True
    if msg.dev_type.startswith('powerrelay.'):
        return True
    if msg.dev_type.startswith('thermometer.'):
        return True
    if msg.dev_type.startswith('hygrometer.'):
        return True
    if msg.dev_type.startswith('battery.'):
        return True

    return False


class Bridge(object):

    def __init__(self, hass: HomeAssistant) -> None:
        """Init dummy hub."""
        self._hass = hass
        self._eng = AsyncEngine()
        self._dev = self.setup_device()
        self._mon = Monitor(self._dev, db_server=DB_SERVER)
        self._eng.start()
        self._eng.on_start(self.on_start)
        self._eng.on_stop(self.on_stop)
        self._entities = {}
        self._handlers = []

    @property
    def engine(self):
        return self._eng

    async def on_start(self):
        _LOGGER.warning(f"{self._eng} started")
        await self.wait_is_ready()
        print("Subscribing..")
        self._mon.subscribe(self.monitor_event)
        self._eng.subscribe(self.notification_handler)

    def on_stop(self):
        _LOGGER.warning(f"{self._eng} stopped")

    def add_entity(self, addr, entity):
        self._entities.update({addr: entity})

    def remove_entity(self, addr):
        self._entities.pop(addr)

    def get_entity(self, addr):
        return self._entities.get(addr, None)

    def add_handler(self,handler):
        print(handler)
        self._handlers.append(handler)

    def remove_handler(self,handler):
        self._handlers.remove(handler)

    def setup_device(self):
        dev = schemas.hmi()
        dev.dev_type = 'hmi.hass'
        dev.vendor_id = 'IMT Atlantique'
        dev.product_id = 'xAAL to HASS Brigde'
        self._eng.add_device(dev)
        return dev

    def send_request(self, targets, action, body=None):
        self._mon.engine.send_request(self._dev, targets, action, body)

    async def wait_is_ready(self) -> bool:
        while 1:
            if self._mon.boot_finished:
                return True
            await asyncio.sleep(1)
        return False

    def monitor_event(self, event, dev):
        entity = self.get_entity(dev.address)

        if entity is None:
            for h in self._handlers:
                r = h.new_entity(dev)
                if r:
                    _LOGGER.debug(f"New entity for {dev.address}")
                    return
            _LOGGER.warning(f"Unable to find handler for {dev.address}")
            return

        if event in [Notification.attribute_change, Notification.metadata_change]:
            _LOGGER.debug(f"{event} {entity}")
            entity.async_write_ha_state()
            return

    def notification_handler(self, msg):
        # right now the monitor doesn't send event on notification, so the bridge deals w/
        # both monitor events & messages.
        if (not msg.is_notify()) or msg.is_alive() or msg.is_attributes_change():
            return
        entity = self.get_entity(msg.source)
        if entity and hasattr(entity, 'handle_notification'):
            msg.dump()
            entity.handle_notification(msg)

