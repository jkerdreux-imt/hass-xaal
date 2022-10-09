import asyncio
import functools
from typing import Dict, List, Any, Type

from .const import DOMAIN

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry


from xaal.lib import AsyncEngine, tools, Device, Message, bindings
from xaal.schemas import devices as schemas
from xaal.monitor import Monitor, Notification
from xaal.monitor.monitor import Device as MonitorDevice

import logging

_LOGGER = logging.getLogger(__name__)
UNSUPPORTED_TYPES = ['cli','hmi','windgauge',]


class XAALEntity(Entity):
    #_attr_has_entity_name = True
    _attr_available: bool = False
    _attr_should_poll: bool = False

    def __init__(self, dev: MonitorDevice, bridge: "Bridge") -> None:
        self._dev = dev
        self._bridge = bridge
        self.setup()

    #####################################################
    # Init
    #####################################################
    def setup(self):
        """ Use setup to tweak a entity at creation """
        pass

    async def async_added_to_hass(self) -> None:
        """call by HASS when entity is ready"""
        self._attr_available = True

    #####################################################
    # HASS Device
    #####################################################
    @property
    def device_info(self) -> DeviceInfo | None :
        dev = self._dev
        ident = "dev:" + str(dev.address)

        group_id = dev.description.get('group_id', None)
        if group_id:
            ident = "grp:" + str(group_id)

        return {
            "identifiers": {(DOMAIN, ident)},
            "name": dev.display_name,            
            "model": dev.description.get("product_id", None),
            "manufacturer": dev.description.get("vendor_id", None),
            "sw_version": dev.description.get("version", None),
            "hw_version": dev.description.get("hw_id", None),
            "suggested_area" : dev.db.get("location",None)
        }

    #####################################################
    # xAAL helpers
    #####################################################
    def send_request(self, action: str, body: Dict[str, Any] | None =None) -> None:
        _LOGGER.debug(f"{self} {action} {body}")
        self._bridge.send_request([self._dev.address, ], action, body)

    def get_attribute(self, name: str, default: Dict[str, Any] =None) -> Any:
        """ return a attribute for xAAL device"""
        return self._dev.attributes.get(name, default)

    #####################################################
    # Entity properties
    #####################################################
    def short_type(self) -> str:
        """ return a fake device class for entity that doesn't have one """
        # this apply for light, button
        # NOTE: I don't know why some entities don't have a device class
        return self._dev.dev_type.split('.')[0]

    @property
    def name(self) -> str | None:
        force_name = getattr(self,'_force_name',None)
        dev_class = force_name or self.device_class or self.short_type()
        return f"{dev_class} {self._dev.display_name}"

    @property
    def unique_id(self) -> str:
        addr = str(self._dev.address).replace('-', '_')
        if hasattr(self,'_xaal_attribute'):
            return f"xaal.{addr}.{self._xaal_attribute}"
        return f"xaal.{addr}"
        

class EntityFactory(object):
    """Class that hold binding (dev_type->Entities) and add_entities callback for each platform"""

    def __init__(self, bridge: "Bridge", async_add_entitites: AddEntitiesCallback, binding: dict) -> None:
        self._bridge = bridge
        self._async_add_entitites = async_add_entitites
        self._map = binding

    def build_entities(self, device: MonitorDevice) -> bool:
        """ return True if this factory managed to build some entities"""
        result = []
        for b_type in self._map.keys():
            if device.dev_type.startswith(b_type):
                for k in self._map[b_type]:
                    entity = k(device, self._bridge)
                    result.append(entity)
                # an factory can match only one dev_type
                self._async_add_entitites(result)
                self._bridge.add_entities(device.address, result)
                return True
        return False


def async_setup_factory(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    binding: dict ) -> None:

    bridge: Bridge = hass.data[DOMAIN][config_entry.entry_id]
    factory = EntityFactory(bridge, async_add_entities, binding)
    bridge.add_factory(factory)

    for dev in bridge._mon.devices:
        if dev.is_ready():
            factory.build_entities(dev)


def filter_msg(msg: Message) -> bool:
    m_type = msg.dev_type.split('.')[0]
    if m_type in UNSUPPORTED_TYPES:
        return False
    return True


class Bridge(object):

    def __init__(self, hass: HomeAssistant, db_server) -> None:
        """Init xAAL bridge."""
        self._hass = hass
        self._eng = AsyncEngine()
        self._dev = self.setup_device()
        self._mon = Monitor(self._dev, filter_msg, db_server)
        self._eng.on_start(self.on_start)
        self._eng.on_stop(self.on_stop)
        self._eng.start()
        self._entities = {}
        self._factories = []

    #####################################################
    # Engine & Hooks
    #####################################################
    async def on_start(self) -> None:
        """Subscribe to Monitor events and Messages"""
        #await self.wait_is_ready()
        print("Subscribing..")
        self._mon.subscribe(self.monitor_event)
        self._eng.subscribe(self.monitor_notification)

    def on_stop(self) -> None:
        _LOGGER.info(f"{self._eng} stopped")

    async def wait_is_ready(self) -> bool:
        """Wait the monitor to received all devices infos """
        while 1:
            if self._mon.boot_finished:
                return True
            await asyncio.sleep(0.2)
        return False

    #####################################################
    # Entities
    #####################################################
    def build_entities(self,dev: MonitorDevice) -> None:
        """search factories to build a new entities"""
        cnt = 0
        for fact in self._factories:
            r = fact.build_entities(dev)
            if r:
                cnt = cnt + 1
        if cnt==0:
            self.warm_once(f"Unable to find entity for {dev.address} {dev.dev_type} ")
       
    def add_entities(self, addr: bindings.UUID, entities: list[XAALEntity]) -> None:
        """register a some entities (called from factories)"""
        _LOGGER.debug(f"new Entities: {addr} {entities}")
        self._entities.update({addr: entities})

    def remove_entities(self, addr: bindings.UUID) -> None:
        _LOGGER.debug(f"Removing entities: {addr}")
        self._entities.pop(addr)

    def get_entities(self, addr: bindings.UUID) -> list[XAALEntity] | None:
        return self._entities.get(addr, None)

    def ha_remove_device(self, ident: str) -> None:
        """ User asked to remove an HA device, we need to find out the entites """
        tmp = ident.split(':')
        addr = tools.get_uuid(tmp[1])
        # is it a xAAL device, if so remove it's address
        if tmp[0] == 'dev':
            self.remove_entities(addr)
        else:
            # it's a group, remove all associated stuff
            devs = self._mon.devices.get_with_group(addr)
            for d in devs:
                self.remove_entities(d.address)

    #####################################################
    # Factories
    #####################################################
    def add_factory(self, factory: EntityFactory):
        """ register a new platform factory"""
        self._factories.append(factory)

    def remove_factory(self, factory: EntityFactory):
        self._factories.remove(factory)

    #####################################################
    # xAAL
    #####################################################
    def setup_device(self) -> Device:
        """setup a new device need by the Monitor"""
        dev = schemas.hmi()
        dev.dev_type = 'hmi.hass'
        dev.vendor_id = 'IMT Atlantique'
        dev.product_id = 'xAAL to HASS Brigde'
        # never use this terrible hack to gain access to brigde throught aioconsole
        #dev.new_attribute('bridge',self)
        self._eng.add_device(dev)
        return dev

    def send_request(self, targets: List[bindings.UUID], action: str, body: Dict[str, Any] | None =None):
        """send a xAAL request (queueing it)"""
        self._eng.send_request(self._dev, targets, action, body)

    #####################################################
    # Monitor events & callbacks
    #####################################################
    def monitor_event(self, notif: Notification, dev: MonitorDevice):
        entities = self.get_entities(dev.address)
        # update entities if found
        if entities and (notif in [Notification.attribute_change, Notification.description_change, Notification.metadata_change]):
            for ent in entities:
                if ent.available:
                    ent.schedule_update_ha_state()
            return
        # Not found, so it's a new entity 
        if entities is None and dev.is_ready():
            self.build_entities(dev)

    def monitor_notification(self, msg: Message):
        # right now the monitor doesn't send event on notification, so the bridge deals w/
        # both monitor events & messages.
        if (not msg.is_notify()) or msg.is_alive() or msg.is_attributes_change():
            return
        entities = self.get_entities(msg.source)
        if entities :
            for ent in entities:
                if hasattr(ent, 'handle_notification'):
                    msg.dump()
                    ent.handle_notification(msg)

    #####################################################
    # Miscs
    #####################################################
    @functools.lru_cache(maxsize=128)
    def warm_once(self, msg: str):
        _LOGGER.warning(msg)
