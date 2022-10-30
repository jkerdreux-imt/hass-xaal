# xAAL bridge for Home Assistant #

A bridge to provide access to xAAL Bus in Home-Assistant

## Important:
- Don't use this in production! only for test right now
- Missing config entry: Right now, there is no configuration for this addon
- Integration on start: If you want to add a new device, you have to restart hass
- Slow startup: The addon search for devices at startup, this can take some time.

##Install:
Simply copy the xaal folder in the Home-Assistant custom-component folder. Go
to configuration/integration panel and add xAAL. That's all.


## Notes:
Hass does some strange things with entity.unique_id, entity_name and so on.
Read carefully : 
- entity.unique_id is a "xaal." + device.address 
- entity_name is xAAL name/nickname OR a short-string-from-address (Monitor.display_name)
- entity_id (used in UI, script and so on) is build from unique_id or entity_name if provided
- changes in xAAL nickname only affect entity_name, entity_id will not change. This is the 
  way HASS works. 

xALL Device => Entities / Devices
- For a given device_type you can have more than one Entity (powermeter => power/current/voltage)
- One Entity is always bounded to single HASS device
- If more than one entity is used, they bellow to the same HASS device
- If xAAL group is used (ie: smart plug), the binding groups them in a HASS device.

DB Server:
- The bridge try to save devices and entities renamed throught the UI in DB server w/ key ha_name/ha_dev_name
- ha_name = Entity name / ha_dev_name = Device 
- All Entities (xAAL Device) from a device should have the same ha_dev_name
- **WARNING**: if ha_dev_name is set to None and ha_name not changed, ha_dev_name will be unchanged in metadata because HA will not call *async_registry_entry_updated*.
