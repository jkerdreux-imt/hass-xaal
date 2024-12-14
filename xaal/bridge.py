import asyncio
import functools
import logging
from typing import Any, Dict, List

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.helpers.device_registry import EVENT_DEVICE_REGISTRY_UPDATED, DeviceEntry
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import EVENT_ENTITY_REGISTRY_UPDATED

from xaal.lib import AsyncEngine, Device, Message, bindings, tools
from xaal.monitor import Monitor, Notification
from xaal.monitor.monitor import Device as MonitorDevice

from . import utils
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
UNSUPPORTED_TYPES = ['cli', 'hmi', 'logger']

UPDATE_NOTIFICATIONS = [
    Notification.attribute_change,
    Notification.description_change,
    Notification.metadata_change,
]


class XAALEntity(Entity):
    _attr_has_entity_name = True
    _attr_available: bool = False
    _attr_should_poll: bool = False

    def __init__(self, dev: MonitorDevice, bridge: "Bridge") -> None:
        self._dev = dev
        self._bridge = bridge
        self.setup()

    #####################################################
    # Life cycle
    #####################################################
    def setup(self):
        """Use setup to tweak a entity at creation"""
        pass

    async def async_added_to_hass(self) -> None:
        """call by HASS when entity is ready"""
        self._attr_available = True

    def auto_wash(self) -> None:
        """Monitor device has been auto washed, so entity isn't available"""
        # Note: we don't release the _dev weakref because we still need
        # it. If the device is back, it will be release w/ the fix_device()
        self._attr_available = False

    def fix_device(self, device: MonitorDevice) -> None:
        """The xAAL device is back after an auto-wash, so we need to switch,
        to the new MonitorDevice.
        """
        self._dev = device
        self._attr_available = True

    #####################################################
    # HASS Device
    #####################################################
    @property
    def device_info(self) -> DeviceInfo | None:
        dev = self._dev
        ident = self._bridge.device_to_ident(dev)
        name = dev.db.get("ha_dev_name", ident)
        return {
            "identifiers": {(DOMAIN, ident)},
            "name": name,
            "model": dev.description.get("product_id"),
            "manufacturer": dev.description.get("vendor_id"),
            "sw_version": dev.description.get("version"),
            "hw_version": dev.description.get("hw_id"),
            "suggested_area": dev.db.get("location"),
        }

    #####################################################
    # xAAL helpers
    #####################################################
    def send_request(self, action: str, body: Dict[str, Any] | None = None) -> None:
        _LOGGER.debug(f"{self} {action} {body}")
        self._bridge.send_request(
            [self._dev.address],
            action,
            body,
        )

    def get_attribute(self, name: str, default: Dict[str, Any] = None) -> Any:
        """return a attribute for xAAL device"""
        return self._dev.attributes.get(name, default)

    @property
    def address(self):
        return self._dev.address

    #####################################################
    # Entity properties
    #####################################################
    def short_type(self) -> str:
        """return a fake device class for entity that doesn't have one"""
        # this apply for light, button
        # NOTE: I don't know why some HASS entities don't have a device class
        return self._dev.dev_type.split('.')[0]

    @property
    def name(self) -> str | None:
        db_name = self._dev.db.get('ha_name')
        dev_name = self._dev.db.get('ha_dev_name')
        if dev_name and db_name:
            db_name = db_name.removeprefix(f"{dev_name} ")

        force_name = getattr(self, '_force_name', None)
        name = db_name or force_name or self.device_class or self.short_type()
        # print(f"{dev_name} =>{db_name} => {name}")
        return name.capitalize()

    @property
    def unique_id(self) -> str:
        addr = str(self._dev.address).replace('-', '_')
        if hasattr(self, '_xaal_attribute'):
            return f"xaal.{addr}.{self._xaal_attribute}"
        return f"xaal.{addr}"

    @property
    def device_registry_entry(self) -> DeviceEntry | None:
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
        """return True if this factory managed to build some entities"""
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
    binding: dict,
) -> None:
    bridge: Bridge = hass.data[DOMAIN][config_entry.entry_id]
    factory = EntityFactory(bridge, async_add_entities, binding)
    bridge.add_factory(factory)

    for dev in bridge._mon.devices:
        if dev.is_ready():
            factory.build_entities(dev)


def filter_msg(msg: Message) -> bool:
    if msg.dev_type is None:
        # This should not happen
        return False
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
        self._entities: Dict[bindings.UUID, List[XAALEntity]] = {}
        self._factories: List[EntityFactory] = []
        hass.bus.async_listen(EVENT_DEVICE_REGISTRY_UPDATED, self.device_registry_updated)
        hass.bus.async_listen(EVENT_ENTITY_REGISTRY_UPDATED, self.entity_registry_updated)

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
        """Wait the monitor to received all devices infos"""
        while 1:
            if self._mon.boot_finished:
                return True
            await asyncio.sleep(0.2)
        return False

    #####################################################
    # xAAL stuffs
    #####################################################
    def setup_device(self) -> Device:
        """setup a new device need by the Monitor"""
        dev = Device('hmi.hass')
        dev.address = tools.get_random_uuid()
        dev.vendor_id = 'IMT Atlantique'
        dev.product_id = 'xAAL to HASS Brigde'
        # never use this terrible hack to gain access to brigde throught aioconsole
        # dev.new_attribute('bridge', self)
        self._eng.add_device(dev)
        return dev

    def send_request(self, targets: List[bindings.UUID], action: str, body: Dict[str, Any] | None = None):
        """send a xAAL request (queueing it)"""
        self._eng.send_request(self._dev, targets, action, body)

    def ha_update_db(self, body: dict):
        if self._mon.db_server:
            self.send_request([self._mon.db_server], 'update_keys_values', body)

    #####################################################
    # xAAL Monitor events & callbacks
    #####################################################
    def monitor_event(self, notif: Notification, dev: MonitorDevice):
        entities = self.get_entities(dev.address)
        # update entities if found
        if entities:
            # First we need to check if this device isn't an old auto-washed one
            if notif in UPDATE_NOTIFICATIONS:
                for ent in entities:
                    if ent._dev != dev and dev.is_ready():
                        ent.fix_device(dev)
                        _LOGGER.debug(f"Recovering {ent}")

            # is it a change
            if notif in UPDATE_NOTIFICATIONS:
                for ent in entities:
                    if ent.available:
                        ent.schedule_update_ha_state()
                return
            # is it a dropped device
            if notif in [Notification.drop_device]:
                for ent in entities:
                    _LOGGER.debug(f"Entity {ent} isn't available right now")
                    ent.auto_wash()
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
        if entities:
            for ent in entities:
                if hasattr(ent, 'handle_notification'):
                    msg.dump()
                    ent.handle_notification(msg)

    #####################################################
    # Entities
    #####################################################
    def build_entities(self, dev: MonitorDevice) -> None:
        """search factories to build a new entities"""
        cnt = 0
        for fact in self._factories:
            r = fact.build_entities(dev)
            if r:
                cnt = cnt + 1
        if cnt == 0:
            self.warm_once(f"Unable to find entity for {dev.address} {dev.dev_type} ")

    def add_entities(self, addr: bindings.UUID, entities: List[XAALEntity]) -> None:
        """register some entities (called from factories)"""
        _LOGGER.debug(f"new Entities: {addr} {entities}")
        self._entities.update({addr: entities})

    def remove_entities(self, addr: bindings.UUID) -> None:
        """remove entities for a given xAAL address"""
        _LOGGER.debug(f"Removing entities: {addr}")
        try:
            self._entities.pop(addr)
            self._mon.devices.remove(addr)
        except KeyError:
            # device already auto-washed or
            # and old entity
            _LOGGER.warning(f"Unknow entity w/ addr {addr}")

    def get_entities(self, addr: bindings.UUID) -> List[XAALEntity] | None:
        """return entities for a given xAAL address"""
        return self._entities.get(addr)

    def get_entity_by_id(self, entity_id: str) -> XAALEntity | None:
        """return a entity for a given entity_id"""
        # This is cleary not a best way to find out entity by id, but
        # HASS doesn't seems to provide a direct way
        for addr, entities in self._entities.items():
            for entity in entities:
                if entity.entity_id == entity_id:
                    return entity
        return None

    #####################################################
    # HA devices
    #####################################################
    def device_to_ident(self, device: MonitorDevice) -> str:
        group_id = device.description.get('group_id')
        if group_id:
            return "grp:" + str(group_id)
        else:
            return "dev:" + str(device.address)

    def ident_to_address(self, ident: str) -> List[bindings.UUID]:
        tmp = ident.split(':')
        addr = tools.get_uuid(tmp[1])
        # is it a xAAL device, if so remove it's address
        if tmp[0] == 'dev':
            return [addr]
        else:
            # it's a group
            return [dev.address for dev in self._mon.devices.get_with_group(addr)]

    def ha_remove_device(self, ident: str) -> None:
        """User asked to remove an HA device, we need to find out the entites"""
        for addr in self.ident_to_address(ident):
            self.remove_entities(addr)

    #####################################################
    # Factories
    #####################################################
    def add_factory(self, factory: EntityFactory):
        """register a new platform factory"""
        self._factories.append(factory)

    def remove_factory(self, factory: EntityFactory):
        self._factories.remove(factory)

    #####################################################
    # HA Event listening
    #####################################################
    async def device_registry_updated(self, event: Event):
        """store the new device name in DB if changed"""
        if event.data.get('action') != 'update':
            return
        # is it a xAAL device
        device_id = event.data.get('device_id')
        dr = device_registry.async_get(self.hass)
        device_entry = dr.async_get(device_id)
        (domain, dev_ident) = utils.get_dev_identifiers(device_entry.identifiers)
        if domain != DOMAIN:
            return

        _LOGGER.info(event.data)
        addrs = self.ident_to_address(dev_ident)
        kv = {'ha_dev_name': device_entry.name_by_user, 'location': device_entry.area_id}
        for addr in addrs:
            body = {'device': addr, 'map': kv}
            self.ha_update_db(body)

    async def entity_registry_updated(self, event: Event):
        """store the new entity name in DB if changed"""
        if event.data.get('action') != 'update':
            return
        # ugly bugfix HASS sync issue, we need to wait registry to be up to date.
        await asyncio.sleep(0.1)
        # is it xAAL entity ?
        entity_id = event.data.get('entity_id')
        er = entity_registry.async_get(self.hass)
        entity_entry = er.async_get(entity_id)
        if entity_entry.platform != DOMAIN:
            return

        _LOGGER.info(event.data)
        entity = self.get_entity_by_id(entity_id)
        if entity:
            name = entity.registry_entry.name
            if 'name' not in event.data.get('changes', {}).keys():
                return
            kv = {'ha_name': name}
            body = {'device': entity.address, 'map': kv}
            self.ha_update_db(body)
        else:
            _LOGGER.info(f"Unable to find entiy {entity_id}")

    #####################################################
    # Miscs
    #####################################################
    @functools.lru_cache(maxsize=128)
    def warm_once(self, msg: str):
        _LOGGER.warning(msg)
