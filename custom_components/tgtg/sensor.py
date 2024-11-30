import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN
from .birthday_manager import setup_birthday_sensors
from .event_manager import setup_event_sensors
from .almanac_sensor import setup_almanac_sensors
from .moon import setup_almanac_moon_sensor

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
   if DOMAIN not in hass.data:
       hass.data[DOMAIN] = {}
   if "almanac_sensors" not in hass.data[DOMAIN]:
       hass.data[DOMAIN]["almanac_sensors"] = {}

   entities = []
   
   almanac_entities, almanac_sensors = await setup_almanac_sensors(hass, entry.entry_id, entry.data)
   entities.extend(almanac_entities)
   hass.data[DOMAIN]["almanac_sensors"][entry.entry_id] = almanac_sensors
   
   if moon_entities := await setup_almanac_moon_sensor(hass, entry.entry_id, entry.data):
       entities.extend(moon_entities)
       
   if birthday_entities := await setup_birthday_sensors(hass, entry.entry_id, entry.data):
       entities.extend(birthday_entities)
       
   if event_entities := await setup_event_sensors(hass, entry.entry_id, entry.data):
       entities.extend(event_entities)

   hass.data[DOMAIN]["entities"] = entities
   
   async_add_entities(entities, True)