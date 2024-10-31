
# https://github.com/home-assistant/core/blob/dev/homeassistant/components/moon/sensor.py 

from __future__ import annotations
from astral import moon
import cnlunar 
import re
import logging
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.entity import DeviceInfo, EntityCategory

from .const import (
    DOMAIN,
    MIN_TIME_BETWEEN_UPDATES,
    MIN_TIME_BETWEEN_TWOHOUR_UPDATES,
    MAIN_SENSORS,
)

_LOGGER = logging.getLogger(__name__)

class AlmanacMoonSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(self, device, name, sensor_type, is_main_sensor):
        self._device = device
        self._type = sensor_type
        self._state = None
        self._attributes = {}
        self._available = False
        self._is_main_sensor = is_main_sensor
        self._last_update = None
        self._attr_has_entity_name = True
        self._moon_icons = {
            '朔月': 'mdi:moon-new',
            '峨眉月': 'mdi:moon-waxing-crescent',
            '上弦月': 'mdi:moon-first-quarter',
            '渐盈凸月': 'mdi:moon-waxing-gibbous',
            '满月': 'mdi:moon-full',
            '渐亏凸月': 'mdi:moon-waning-gibbous',
            '下弦月': 'mdi:moon-last-quarter',
            '残月': 'mdi:moon-waning-crescent'
        }

    @property
    def name(self):
        return self._type

    @property 
    def unique_id(self):
        return f"{self._device._entry_id}_{self._type}"

    @property
    def device_info(self):
        return self._device.device_info

    @property
    def entity_category(self):
        return EntityCategory.DIAGNOSTIC

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    @property
    def available(self):
        return self._available

    @property
    def icon(self):
        if self._type == '月相':
            return self._moon_icons.get(self._state, 'mdi:moon-full')
        return 'mdi:calendar-text'

    def _get_moon_phase_wuxing(self, lunar_day):
        try:
            day = int(lunar_day)
            if day <= 6:
                return '水'
            elif day <= 11:
                return '木'
            elif day <= 16:
                return '火'
            elif day <= 22:
                return '金'
            else:
                return '土'
        except (ValueError, TypeError):
            return '未知'

    def _get_moon_phase_luck(self, lunar_day):
        try:
            day = int(lunar_day)
            if day in [1, 8, 15, 23]:
                return '大吉'
            elif day in [3, 7, 13, 18, 22, 27]:
                return '吉'
            elif day in [5, 10, 20, 25]:
                return '平'
            elif day in [4, 12, 19, 26]:
                return '凶'
            else:
                return '平吉'
        except (ValueError, TypeError):
            return '未知'

    def _get_moon_phase_description(self, phase):
        descriptions = {
            '朔月': '月亮完全不可见，月亮与太阳位于同一方向。此时月亮运行至日月同黄经之位，为农历每月初一。道教称此时阴阳相交，万物启始，适合静修、存想',
            '峨眉月': '月亮呈细弧形，东方傍晚可见。峨眉之名取自娥眉新月之意，象征新生之气开始萌动。道家认为此时阳气初升，宜修炼内丹',
            '上弦月': '月亮外侧发亮，呈现半圆形。月球位于黄道上，与太阳相差90度，为农历七、八日前后。道教视其为阳气上升之象，契合人体小周天运行',
            '渐盈凸月': '月亮大部分可见，接近圆形。此时月相渐盈，寓意阳气渐盛，道教认为此乃天地之气由升而合，为修行采气之良时',
            '满月': '月亮完整可见，呈现圆形。为农历十五、十六日前后，月亮运行至日月对照之位。道教认为此时阴阳交泰，天人合一，为修道采药、存想打坐的最佳时机',
            '渐亏凸月': '月亮开始减亏，仍近似圆形。象征阳气开始收敛，阴气渐生。道教以此时为炼己修身、收心养性的时节',
            '下弦月': '月亮内侧发亮，呈现半圆形。月球位于黄道上，与太阳相差270度，为农历二十二、二十三日前后。道教视其为阴气上升之象，与人体经脉运行相应',
            '残月': '月亮呈细弧形，清晨西方可见。此为月相将尽之象，道教认为此时天地之气归藏，适合收功打坐，为新月蓄势'
        }
        return descriptions.get(phase, '未知月相')

    def _get_lunar_day(self, lunar):
        try:
            match = re.search(r'\d+', lunar.lunarDayCn)
            if match:
                return int(match.group())
            return 1
        except (AttributeError, ValueError):
            _LOGGER.error("无法解析农历日期")
            return 1

    async def async_update(self) -> None:
        try:
            now = dt.now().replace(tzinfo=None)
            if (self._last_update is not None and 
                now - self._last_update < MIN_TIME_BETWEEN_UPDATES):
                return

            state = moon.phase(now.date())
            
            try:
                lunar = cnlunar.Lunar(now, godType='8char')
                lunar_day = self._get_lunar_day(lunar)
            except Exception as e:
                _LOGGER.error(f"获取农历信息失败: {e}")
                lunar_day = 1

            if state < 0.5 or state > 27.5:
                phase = '朔月'
            elif state < 6.5:
                phase = '峨眉月'
            elif state < 7.5:
                phase = '上弦月'
            elif state < 13.5:
                phase = '渐盈凸月'
            elif state < 14.5:
                phase = '满月'
            elif state < 20.5:
                phase = '渐亏凸月'
            elif state < 21.5:
                phase = '下弦月'
            else:
                phase = '残月'

            self._state = phase
            percentage = (state / 29.53) * 100 

            self._attributes = {
                '月龄': lunar_day,
                '月相百分比': f"{percentage:.1f}%",
                '月相说明': self._get_moon_phase_description(phase),
                '阴阳': '阴' if lunar_day > 15 else '阳',
                '五行': self._get_moon_phase_wuxing(lunar_day),
                '吉凶': self._get_moon_phase_luck(lunar_day)
            }
            self._available = True
            self._last_update = now

        except Exception as e:
            _LOGGER.error(f"更新月相传感器时出错: {e}")
            self._available = False

class AlmanacDevice:
    def __init__(self, entry_id: str, name: str):
        self._entry_id = entry_id
        self._name = name

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=self._name,
            model="Chinese Almanac",
            manufacturer="道教",
        )

async def setup_almanac_moon_sensor(
    hass: HomeAssistant, 
    entry_id: str, 
    config_data: dict
) -> list:
    entities = []
    name = config_data.get("name", "中国老黄历")
    almanac_device = AlmanacDevice(entry_id, name)
    moon_sensor = AlmanacMoonSensor(almanac_device, name, "月相", True)
    entities.append(moon_sensor)
    async def update_moon_phase(now):
        await moon_sensor.async_update()
    async_track_time_interval(hass, update_moon_phase, timedelta(hours=1))
    return entities