import asyncio
import functools
from html import entities
from turtle import pd, up
from typing import Dict, List, Any, Type
from uuid import UUID

from .const import DOMAIN

from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.entity import Entity, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry
from homeassistant.helpers.device_registry import DeviceEntry, EVENT_DEVICE_REGISTRY_UPDATED
from homeassistant.helpers.entity_registry import EVENT_ENTITY_REGISTRY_UPDATED

from xaal.lib import AsyncEngine, tools, Device, Message, bindings
from xaal.schemas import devices as schemas
from xaal.monitor import Monitor, Notification
from xaal.monitor.monitor import Device as MonitorDevice

import logging

_LOGGER = logging.getLogger(__name__)
UNSUPPORTED_TYPES = ['cli','hmi','logger']


class XAALEntity(Entity):
    _attr_has_entity_name = True
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
        group_id = dev.description.get('group_id', None)
        if group_id:
            ident = "grp:" + str(group_id)
        else:
            ident = "dev:" + str(dev.address)
        name = dev.description.get("ha_dev_name",ident)
        return {
            "identifiers": {(DOMAIN, ident)},
            "name": name,
            "model": dev.description.get("product_id", None),
            "manufacturer": dev.description.get("vendor_id", None),
            "sw_version": dev.description.get("version", None),
            "hw_version": dev.description.get("hw_id", None),
            "suggested_area": dev.db.get("location",None)
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

    @property
    def address(self):
        return self._dev.address
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
        db_name = self._dev.db.get('ha_name',None)
        force_name = getattr(self,'_force_name',None)
        name = db_name or force_name or self.device_class or self.short_type()
        return name

    @property
    def unique_id(self) -> str:
        addr = str(self._dev.address).replace('-', '_')
        if hasattr(self,'_xaal_attribute'):
            return f"xaal.{addr}.{self._xaal_attribute}"
        return f"xaal.{addr}"

    def _async_registry_entry_updated(self) -> None:
        if not self.available:
            return

        kv = {}
        if self.registry_entry.name != self._dev.db.get('ha_name',None):
            kv.update({'ha_name': self.registry_entry.name})

        print(f"{self.device_registry_entry.name_by_user} != {self._dev.db.get('ha_dev_name',None)}")

        if self.device_registry_entry.name_by_user != self._dev.db.get('ha_dev_name',None):
            kv.update({'ha_dev_name': self.device_registry_entry.name_by_user})

        if kv != {}:
            _LOGGER.warning(f"{self} updating {self.registry_entry.name}")
            # FIXME: we can drop key too! 
            body = {'device':self._dev.address,'map':kv}
            print(body)
            self._bridge.ha_update_db(body)
            #self._dev.set_db(kv)
        #import pdb;pdb.set_trace()

    @property
    def device_registry_entry(self) -> DeviceEntry|None:
        device_id = self.registry_entry.device_id
        dr = device_registry.async_get(self.hass)
        return dr.async_get(device_id)


class EntityFactory(object):
    """Class that hold binding (dev_type->Entities) and add_entities callback for each platform"""

    def __init__(self, bridge: "Bridge", async_add_entitites: AddEntitiesCallback, binding: dict) -> None:
        self._bridge = bridge
        self._async_add_entitites = async_add_entitites
        self._binding = binding

    def build_entities(self, device: MonitorDevice) -> bool:
        """ return True if this factory managed to build some entities"""
        result = []
        for b_type in self._binding.keys():
            if device.dev_type.startswith(b_type):
                for k in self._binding[b_type]:
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
        self.hass = hass
        self._eng = AsyncEngine()
        self._dev = self.setup_device()
        self._mon = Monitor(self._dev, filter_msg, db_server)
        self._eng.on_start(self.on_start)
        self._eng.on_stop(self.on_stop)
        self._eng.start()
        self._entities = {}
        self._factories = []
        hass.bus.async_listen(EVENT_DEVICE_REGISTRY_UPDATED,self.device_registry_updated)
        hass.bus.async_listen(EVENT_ENTITY_REGISTRY_UPDATED,self.entity_registry_updated)

    async def device_registry_updated(self, event: Event):
        if event.data.get('action', None) != 'update': 
            return

        _LOGGER.warning(event.data)
        #import pdb;pdb.set_trace()
        device_id = event.data.get('device_id',None)

        dr = device_registry.async_get(self.hass)
        device_entry = dr.async_get(device_id)
        idents = list(device_entry.identifiers)
        if idents[0][0]!= DOMAIN:
            return

        data = idents[0][1].split(':')
        addr = tools.get_uuid(data[1])
        if data[0] == 'dev':
            addrs = [addr,]

        elif data[0] == 'grp':
            addrs = [dev.address for dev in self._mon.devices.get_with_group(addr)]

        kv = {'ha_dev_name': device_entry.name_by_user}
        for addr in addrs:
            body = {'device':addr,'map':kv}
            self.ha_update_db(body)

    async def entity_registry_updated(self, event: Event):
        if event.data.get('action', None) != 'update': 
            return

        _LOGGER.warning(event.data)
        # ugly bugfix HASS sync issue, we need to wait registry to be up to date.
        await asyncio.sleep(0.1)
        entity_id = event.data.get('entity_id',None)
        entity = self.get_entity_by_id(entity_id)

        if entity:
            name = entity.registry_entry.name
            if (name == None) and (entity._dev.db.get('ha_name',None) == None):
                # HASS and DB can be out of sync, so we push db even if everything looks
                # fine, except if there is no data
                return
            kv = {'ha_name': name}
            body = {'device':entity.address,'map':kv}
            self.ha_update_db(body)

    def get_entity_by_id(self, entity_id: str) -> XAALEntity | None:
        # This is cleary not a best way to find out entity by id, but
        # HASS doesn't seems to provide a direct way
        for addr, entities in self._entities.items():
            for entity in entities:
                if entity.entity_id == entity_id:
                    return entity
        return None

    #####################################################
    # Engine & Hooks
    #####################################################
    async def on_start(self) -> None:
        """Subscribe to Monitor events and Messages"""
        print("Subscribing..")
        self._mon.subscribe(self.monitor_event)
        self._eng.subscribe(self.monitor_notification)

    def on_stop(self) -> None:
        _LOGGER.info(f"{self._eng} stopped")

    def is_ready(self):
        return self._mon.boot_finished

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
        #_LOGGER.debug(f"new Entities: {addr} {entities}")
        _LOGGER.debug(f"new Entities: {addr} {entities}")
        self._entities.update({addr: entities})

    def remove_entities(self, addr: bindings.UUID) -> None:
        _LOGGER.debug(f"Removing entities: {addr}")
        self._entities.pop(addr)

    def get_entities(self, addr: bindings.UUID) -> list[XAALEntity] | None:
        return self._entities.get(addr, None)

    def ha_remove_device(self, ident: str) -> None:
        """ User asked to remove an HA device, we need to find out the entites """
        # TODO: add a method to extract addresses from ident
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

    def ha_update_db(self, body: dict):
        self.send_request([self._mon.db_server], 'update_keys_values', body)

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
