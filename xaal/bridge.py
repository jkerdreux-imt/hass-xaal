
import asyncio

from homeassistant.core import HomeAssistant
from xaal.lib import AsyncEngine, tools, MessageType
from xaal.schemas import devices as schemas
from xaal.monitor import Monitor, Notification

import logging
_LOGGER = logging.getLogger(__name__)

#DB_SERVER = tools.get_uuid('d28fbc27-190f-4ee5-815a-fe05233400a2')
DB_SERVER = tools.get_uuid('9064ccbc-84ea-11e8-80cc-82ed25e6aaaa')

UNSUPPORTED_TYPES = ['cli','hmi','gateway','windgauge','barometer','soundmeter']


def filter_msg(msg):
    m_type = msg.dev_type.split('.')[0]
    if m_type in UNSUPPORTED_TYPES:
        return False
    return True


class Bridge(object):

    def __init__(self, hass: HomeAssistant) -> None:
        """Init dummy hub."""
        self._hass = hass
        self._eng = AsyncEngine()
        self._dev = self.setup_device()
        self._mon = Monitor(self._dev, filter_msg, db_server=DB_SERVER)
        self._eng.on_start(self.on_start)
        self._eng.on_stop(self.on_stop)
        self._eng.start()
        self._entities = {}
        self._factories = []

    @property
    def engine(self):
        return self._eng

    async def on_start(self):
        _LOGGER.info(f"{self._eng} started")
        #await self.wait_is_ready()
        print("Subscribing..")
        self._mon.subscribe(self.monitor_event)
        self._eng.subscribe(self.monitor_notification)

    def on_stop(self):
        _LOGGER.info(f"{self._eng} stopped")

    def add_entity(self, addr, entity):
        _LOGGER.debug(f"new Entity {addr} {entity}")
        self._entities.update({addr: entity})

    def remove_entity(self, addr):
        self._entities.pop(addr)

    def get_entity(self, addr):
        return self._entities.get(addr, None)

    def add_factory(self, klass):
        self._factories.append(klass)

    def remove_factory(self, klass):
        self._factories.remove(klass)

    def setup_device(self):
        dev = schemas.hmi()
        dev.dev_type = 'hmi.hass'
        dev.vendor_id = 'IMT Atlantique'
        dev.product_id = 'xAAL to HASS Brigde'
        # never use this terrible hack to gain access to brigde throught aioconsole
        #dev.new_attribute('bridge',self)
        self._eng.add_device(dev)
        return dev

    def send_request(self, targets, action, body=None):
        self._mon.engine.send_request(self._dev, targets, action, body)

    async def wait_is_ready(self) -> bool:
        while 1:
            if self._mon.boot_finished:
                return True
            await asyncio.sleep(0.5)
        return False

    def monitor_event(self, event, dev):
        # DB_SERVER keep spamming us
        if dev.address == DB_SERVER: return

        entity = self.get_entity(dev.address)
        #_LOGGER.debug(f"{event} {dev.address} {dev.is_ready()} => {entity}")

        # WARNING, never call ha_state update on a newly created entity, 
        # hass will block on this task (tricks: asyncio.sleep can fix that)
        if entity and (event == Notification.attribute_change):
            _LOGGER.debug(f"{event} {dev.address} => {entity}")
            entity.schedule_update_ha_state()
            return

        if entity is None and dev.is_ready():
            cnt = 0
            for h in self._factories:
                r = h.new_entity(dev)
                if r:
                    #_LOGGER.info(f"New entity for {dev.address}")
                    cnt = cnt + 1
            if cnt==0:
                _LOGGER.warning(f"Unable to find entity for {dev.address} {dev.dev_type} ")


    def monitor_notification(self, msg):
        # right now the monitor doesn't send event on notification, so the bridge deals w/
        # both monitor events & messages.
        if (not msg.is_notify()) or msg.is_alive() or msg.is_attributes_change():
            return
        entity = self.get_entity(msg.source)
        if entity and hasattr(entity, 'handle_notification'):
            msg.dump()
            entity.handle_notification(msg)
