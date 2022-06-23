
import asyncio
from homeassistant.core import HomeAssistant
from xaal.lib import  AsyncEngine, tools
from xaal.schemas import devices as schemas
from xaal.monitor import Monitor, Notification

import logging
_LOGGER = logging.getLogger(__name__)

#DB_SERVER = tools.get_uuid('d28fbc27-190f-4ee5-815a-fe05233400a2')
DB_SERVER = tools.get_uuid('9064ccbc-84ea-11e8-80cc-82ed25e6aaaa')

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



class Bridge:

    def __init__(self, hass: HomeAssistant) -> None:
        """Init dummy hub."""
        self._hass = hass
        self._eng = AsyncEngine()
        self._dev = self.setup_device()
        self._mon = Monitor(self._dev, db_server=DB_SERVER)
        self._mon.subscribe (self.monitor_event)
        self._eng.start()
        self._eng.on_start(self.on_start)
        self._eng.on_stop(self.on_stop)
        self._entities = {}

    @property
    def engine(self):
        return self._eng

    def on_start(self):
        _LOGGER.warning(f"{self._eng} started")

    def on_stop(self):
        _LOGGER.warning(f"{self._eng} stopped")


    def add_entity(self, addr, entity):
        self._entities.update({addr:entity})

    def remove_entity(self, addr):
        self._entities.pop(addr)


    def setup_device(self):
        dev = schemas.hmi()
        dev.dev_type = 'hmi.hass'
        dev.vendor_id = 'IMT Atlantique'
        dev.product_id = 'xAAL to HASS Brigde'
        self._eng.add_device(dev)
        return dev

    def send_request(self, targets,action, body=None):
        self._mon.engine.send_request(self._dev, targets, action, body)

    async def wait_is_ready(self) -> bool:
        while 1:        
            if self._mon.boot_finished == True:
                return True
            await asyncio.sleep(1)
        return False

    def monitor_event(self,event,dev):
        _LOGGER.info(f"New event {event} {dev}")

        entity = self._entities.get(dev.address, None)
        #if entity == None or entity.hass is None:
        #    return
        if entity == None:
            return

        # if event == Notification.new_device:
        if event in [Notification.attribute_change]:
            entity.async_schedule_update_ha_state()

        # FIXME: monitor_event isn't a coroutine. 
        # if event in [Notification.description_change, Notification.metadata_change]:
        #    await entity.async_device_update()
