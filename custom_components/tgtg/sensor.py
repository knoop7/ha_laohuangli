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

    if "registered_names" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["registered_names"] = {}
        
    if "almanac_sensors" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["almanac_sensors"] = {}

    entities = []
    registered_names = hass.data[DOMAIN]["registered_names"].get(entry.entry_id, set())

    if almanac_result := await setup_almanac_sensors(hass, entry.entry_id, entry.data):
        almanac_entities, almanac_sensors = almanac_result
        entities.extend(almanac_entities)
        hass.data[DOMAIN]["almanac_sensors"][entry.entry_id] = almanac_sensors

    if moon_entities := await setup_almanac_moon_sensor(hass, entry.entry_id, entry.data):
        for entity in moon_entities:
            if entity.name not in registered_names:
                entities.append(entity)
                registered_names.add(entity.name)

    if birthday_entities := await setup_birthday_sensors(hass, entry.entry_id, entry.data):
        entities.extend(birthday_entities)

    if event_entities := await setup_event_sensors(hass, entry.entry_id, entry.data):
        entities.extend(event_entities)

    hass.data[DOMAIN]["registered_names"][entry.entry_id] = registered_names
    if entities:
        async_add_entities(entities, True)