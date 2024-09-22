## 暂时不更新

#from homeassistant.components.text import TextEntity
#from homeassistant.config_entries import ConfigEntry
#from homeassistant.core import HomeAssistant
#from homeassistant.helpers.entity_platform import AddEntitiesCallback
#from datetime import datetime
#import logging
#import cnlunar

#_LOGGER = logging.getLogger(__name__)

#DOMAIN = "tgtg"

#async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
#    """Set up the text input entity from a config entry."""
#    date_input = DateInputEntity(entry.entry_id)
#    async_add_entities([date_input], True)

#class DateInputEntity(TextEntity):
#    def __init__(self, entry_id):
#        """Initialize the text entity."""
#        self._attr_name = "日期输入"
#        self._attr_unique_id = f"chinese_almanac_date_input_{entry_id}"
#        self._input_value = datetime.now().strftime("%Y%m%d")
#        self._attr_mode = "text"
#        self._attr_native_min = 8
#        self._attr_native_max = 1000
#        self._log_messages = []
#        self._attr_extra_state_attributes = {}

#    @property
#    def native_value(self):
#        """Return the value of the text, including log messages."""
#        return f"{self._input_value}"

#    def _inject_log(self, message: str):
#        """Inject a log message into the entity's value."""
#        if len(self._log_messages) >= 5:
#            self._log_messages.pop(0)
#        self._log_messages.append(message)
#        self.async_write_ha_state()

#    async def async_set_value(self, value: str) -> None:
#        """Set the value of the text."""
#        if len(value) == 10 and value.isdigit():
#            try:
#                date = datetime.strptime(value[:8], "%Y%m%d")
#                self._input_value = value
#                await self._async_update_eight_chars(value)
#            except ValueError:
#                pass

#    async def _async_update_eight_chars(self, input_text):
#        """Update eight characters based on input."""
#        try:
#            date = datetime.strptime(input_text[:8], "%Y%m%d")
#            a = cnlunar.Lunar(date, godType='8char')
#            eight_chars = ' '.join([a.year8Char, a.month8Char, a.day8Char, a.twohour8Char])
#            self._attr_extra_state_attributes["八字"] = eight_chars
#        except Exception:
#            self._attr_extra_state_attributes["八字"] = "计算错误"