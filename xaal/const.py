import homeassistant.helpers.config_validation as cv
import voluptuous as vol

DOMAIN = "xaal"
CONF_DB_SERVER = "db_server"

XAAL_TTS_SCHEMA = vol.Schema({
    vol.Optional("title"): cv.template,
    vol.Required("message"): cv.template,
})

XAAL_TTS_SCHEMA = vol.Schema({
    vol.Required("message"): cv.template,
})

