import logging
import random
import time
from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt
from homeassistant.helpers.network import get_url
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    image = GuanyinImage(coordinator, hass)
    coordinator.image_entity = image
    async_add_entities([image])


class GuanyinImage(ImageEntity):
    def __init__(self, coordinator, hass: HomeAssistant):
        super().__init__(hass)
        self._coordinator = coordinator
        self._hass = hass
        self._attr_has_entity_name = True
        self._attr_name = "解签工具"
        self._current_sign = None
        self._last_index = None
        self._base_url = get_url(hass, allow_internal=True)
        self._signs = self._init_signs()
        self._attr_should_poll = False
        self._is_resetting = False
        self._timestamp = time.time()
        self._access_token = None
        self._attr_frame_interval = 0

    def _init_signs(self):
        signs = []
        for i in range(1, 101):
            name = self._get_sign_name(i)
            signs.append({
                "number": i,
                "name": f"{name}签",
                "url": f"{self._base_url}/local/guanyin/{i}.gif"
            })
        return signs

    def _get_sign_name(self, num):
        if num <= 9:
            return f"第{self._number_to_chinese(num)}"
        elif num == 10:
            return "十"
        elif num == 100:
            return "一百"
        else:
            tens, ones = divmod(num, 10)
            if tens == 1:
                tens_str = "十"
            else:
                tens_str = f"{self._number_to_chinese(tens)}十"
            if ones == 0:
                return tens_str
            return f"{tens_str}{self._number_to_chinese(ones)}"

    def _number_to_chinese(self, num):
        chinese_nums = "一二三四五六七八九"
        if 1 <= num <= 9:
            return chinese_nums[num-1]
        return str(num)

    @property
    def unique_id(self):
        return f"{self._coordinator.entry_id}_guanyin_image"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self._coordinator.entry_id}_guanyin")},
            "name": "观音签",
            "manufacturer": "佛教",
            "model": "观世音菩萨",
        }

    async def async_image(self):
        if self._is_resetting:
            return await self._hass.async_add_executor_job(
                self._read_local_file, "blank.gif"
            )
        if self._current_sign:
            return await self._hass.async_add_executor_job(
                self._read_local_file, f"{self._current_sign['number']}.gif"
            )
        return None

    def _read_local_file(self, filename):
        try:
            with open(f"{self._hass.config.path('www/guanyin/')}{filename}", "rb") as file:
                return file.read()
        except Exception as e:
            _LOGGER.error("Error reading image file: %s", str(e))
            return None

    @property
    def entity_picture(self):
        if self._is_resetting:
            return f"local/guanyin/blank.gif?t={self._timestamp}"
        if self._current_sign:
            return f"local/guanyin/{self._current_sign['number']}.gif?t={self._timestamp}"
        return None

    @property
    def content_type(self):
        return "image/gif"

    @property
    def image_url(self):
        if self._is_resetting:
            return f"{self._base_url}/local/guanyin/dd.jpg?t={self._timestamp}"
        if self._current_sign:
            return f"{self._current_sign['url']}?t={self._timestamp}"
        return None

    @property
    def state(self):
        if self._is_resetting:
            return "正在摇签..."
        if self._current_sign:
            return self._current_sign["name"]
        return "等待抽签"

    @property
    def extra_state_attributes(self):
        attributes = {
            "last_updated": self._timestamp,
        }
        if not self._is_resetting and self._current_sign:
            attributes.update({
                "签号": self._current_sign["number"],
                "图片地址": self._current_sign["url"]
            })
        return attributes

    async def async_update_sign(self):
        try:
            self._timestamp = time.time()
            self._is_resetting = True
            self.async_write_ha_state()
            
            await self._hass.async_add_executor_job(time.sleep, 0.1)
            
            while True:
                sign = random.choice(self._signs)
                if sign["number"] != self._last_index:
                    self._last_index = sign["number"]
                    self._current_sign = sign
                    break
            
            self._timestamp = time.time()
            self._is_resetting = False
            self.async_write_ha_state()
            
        except Exception as e:
            self._is_resetting = False
            _LOGGER.error("抽签失败: %s", str(e))