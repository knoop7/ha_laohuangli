from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant  
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN, CONF_GUANYIN_ENABLED

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    if not entry.data.get(CONF_GUANYIN_ENABLED, False):
        return
        
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    button = GuanyinButton(coordinator)
    async_add_entities([button])

class GuanyinButton(ButtonEntity):
    def __init__(self, coordinator):
        self._coordinator = coordinator
        self._attr_has_entity_name = True
        self._attr_name = "抽签"
        self._attr_unique_id = f"{coordinator.entry_id}_guanyin_button"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self._coordinator.entry_id}_guanyin")},
            "name": "观音签",
            "manufacturer": "佛教",
            "model": "观世音菩萨",
        }

    @property
    def icon(self):
        return "mdi:cards"

    async def async_press(self):
        if self._coordinator.enabled:
            await self._coordinator.async_update_sign()