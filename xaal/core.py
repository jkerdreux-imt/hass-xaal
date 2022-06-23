from .const import DOMAIN


from homeassistant.helpers.entity import Entity

class XAALEntity(Entity):
    def __init__(self, dev, bridge):
        self._dev = dev
        self._bridge = bridge

    @property
    def device_info(self):
        print(f"DB: {self.unique_id} {self._dev.db}")
        dev = self._dev
        group_id = dev.description.get('group_id', None)
        if group_id:
            ident = str(group_id)
        else:
            ident = str(dev.address)

        return {
            "identifiers": {(DOMAIN, ident)},
            # If desired, the name for the device could be different to the entity
            #"name": dev.description.get("info", ""),
             "name": dev.display_name,
            #"sw_version": dev.description[""],
            "model": dev.description.get("product_id", ""),
            "manufacturer": dev.description.get("vendor_id", ""),
        }

    def send_request(self, action, body=None):
        self._bridge.send_request([self._dev.address,], action, body)

    @property
    def available(self) -> bool:
        return True

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    #@property
    #def name(self) -> str:
    #    return f"xAAL {self.__class__.__name__} {str(self._dev.address)}"
