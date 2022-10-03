import logging

from typing import Any, Dict, TYPE_CHECKING
from .const import DOMAIN

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import Entity, DeviceInfo

from xaal.lib import bindings
from xaal.monitor.monitor import Device as MonitorDevice

if TYPE_CHECKING:
    # Bridge import for type check produce a circular import 
    # error, to avoid this we use this trick.
    from .bridge import Bridge


_LOGGER = logging.getLogger(__name__)

class XAALEntity(Entity):
    # _attr_has_entity_name = True
    _attr_available: bool = False

    def __init__(self, dev: MonitorDevice, bridge: "Bridge") -> None:
        self._dev = dev
        self._bridge = bridge

    @property
    def device_info(self) -> DeviceInfo | None :
        dev = self._dev
        ident = "dev:" + str(dev.address)

        group_id = dev.description.get('group_id', None)
        if group_id:
            ident = "grp:" + str(group_id)

        #_LOGGER.warning(ident)

        return {
            "identifiers": {(DOMAIN, ident)},
            "name": dev.display_name,            
            "model": dev.description.get("product_id", ""),
            "manufacturer": dev.description.get("vendor_id", ""),
            "sw_version": dev.description.get("version", ""),
            #"hw_version": dev.description.get("hw_id", ""),
        }

    def send_request(self, action: str, body: Dict[str, Any] | None =None) -> None:
        _LOGGER.debug(f"{self} {action} {body}")
        self._bridge.send_request([self._dev.address, ], action, body)

    def get_attribute(self, name: str, default: Dict[str, Any] =None) -> Any:
        return self._dev.attributes.get(name, default)

    def short_type(self) -> str:
        """ return a fake device class for entity that doesn't have one """
        # this apply for light, button
        # NOTE: I don't know why some entities don't have a device class
        return self._dev.dev_type.split('.')[0]

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

    @property
    def name(self) -> str | None:
        dev_class = self.device_class or self.short_type()
        return f"{dev_class} {self._dev.display_name}"

    @property
    def unique_id(self) -> str:
        addr = str(self._dev.address).replace('-', '_')
        return f"xaal.{addr}"

    async def async_added_to_hass(self) -> None:
        """call by HASS when entity is ready"""
        self._attr_available = True
        

class EntityFactory(object):

    def __init__(self, bridge: "Bridge", async_add_entitites: AddEntitiesCallback) -> None:
        self._bridge = bridge
        self._async_add_entitites = async_add_entitites
        self._bridge.add_factory(self)


    def add_entity(self, entity: Entity, address: bindings.UUID) -> None:
        self._async_add_entitites([entity])
        self._bridge.add_entity(address, entity)


def async_setup_factory(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    factory_class: EntityFactory
    ) -> None:

    bridge = hass.data[DOMAIN][config_entry.entry_id]
    factory = factory_class(bridge, async_add_entities)
    for dev in bridge._mon.devices:
        if dev.is_ready():
            factory.new_entity(dev)
