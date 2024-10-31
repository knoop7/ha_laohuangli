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
    data = entry.data
    entities = []

    almanac_entities, almanac_sensors = await setup_almanac_sensors(hass, entry.entry_id, data)
    entities.extend(almanac_entities)

    moon_entities = await setup_almanac_moon_sensor(hass, entry.entry_id, data)
    if moon_entities:
        entities.extend(moon_entities)

    birthday_entities = await setup_birthday_sensors(hass, entry.entry_id, data)
    if birthday_entities:
        entities.extend(birthday_entities)

    event_entities = await setup_event_sensors(hass, entry.entry_id, data)
    if event_entities:
        entities.extend(event_entities)

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN]["entities"] = entities
    hass.data[DOMAIN]["almanac_sensors"] = almanac_sensors

    async_add_entities(entities, True)