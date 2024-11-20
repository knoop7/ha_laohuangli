from __future__ import annotations
from astral import moon
import cnlunar 
import re
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.entity import DeviceInfo, EntityCategory

from .const import DOMAIN

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
        self._last_state = None
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
        self._phase_thresholds = [
            (0.5, '朔月'),
            (6.5, '峨眉月'),
            (7.5, '上弦月'),
            (13.5, '渐盈凸月'),
            (14.5, '满月'),
            (20.5, '渐亏凸月'),
            (21.5, '下弦月'),
            (27.5, '残月'),
            (float('inf'), '朔月')
        ]

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
        wuxing_ranges = [
            (6, '水'),
            (11, '木'),
            (16, '火'),
            (22, '金'),
            (float('inf'), '土')
        ]
        day = int(lunar_day)
        for threshold, element in wuxing_ranges:
            if day <= threshold:
                return element
        return '土'

    def _get_moon_phase_luck(self, lunar_day):
        day = int(lunar_day)
        luck_mappings = {
            '大吉': [1, 8, 15, 23],
            '吉': [3, 7, 13, 18, 22, 27],
            '平': [5, 10, 20, 25],
            '凶': [4, 12, 19, 26]
        }
        for luck, days in luck_mappings.items():
            if day in days:
                return luck
        return '平吉'

    def _get_night_moon_name(self, lunar_day):
        night_moon_names = {
            15: '望月',
            16: '既望月',
            17: '立待月',
            18: '居待月',
            19: '寝待月'
        }
        if lunar_day == 30:
            return '晦月'
        if lunar_day in night_moon_names:
            return night_moon_names[lunar_day]
        return f"{self._cn_number(lunar_day)}夜月"

    def _cn_number(self, num):
        if 1 <= num <= 10:
            return ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十'][num - 1]
        elif 11 <= num <= 19:
            return f"十{self._cn_number(num - 10)}"
        elif num == 20:
            return '二十'
        else:
            return f"二十{self._cn_number(num - 20)}"

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
        return descriptions.get(phase, '')

    def _get_lunar_day(self, lunar):
        lunar_day_cn = lunar.lunarDayCn
        cn_day_map = {}
        for i in range(1, 31):
            if i <= 10:
                cn_day_map[f"初{self._cn_number(i)}"] = i
            elif i < 20:
                cn_day_map[f"十{self._cn_number(i-10)}"] = i
            elif i == 20:
                cn_day_map['二十'] = i
            else:
                cn_day_map[f"廿{self._cn_number(i-20)}"] = i
        cn_day_map['三十'] = 30
        return cn_day_map.get(lunar_day_cn, 1)

    def _calculate_phase_change_interval(self, current_phase, state):
        for threshold, phase in self._phase_thresholds:
            if state < threshold:
                time_to_threshold = (threshold - state) * 24 * 60  
                return timedelta(minutes=min(time_to_threshold, 5))
        return timedelta(minutes=5)

    async def async_update(self) -> None:
        now = dt.now().replace(tzinfo=None)
        state = moon.phase(now.date())
        
        lunar = cnlunar.Lunar(now, godType='8char')
        lunar_day = self._get_lunar_day(lunar)

        current_phase = None
        for threshold, phase in self._phase_thresholds:
            if state < threshold:
                current_phase = phase
                break

        if current_phase != self._last_state:
            self._state = current_phase
            percentage = (state / 29.53) * 100
            night_moon = self._get_night_moon_name(lunar_day)

            self._attributes = {
                '月龄': lunar_day,
                '夜月': night_moon,
                '月相百分比': f"{percentage:.1f}%",
                '月相说明': self._get_moon_phase_description(current_phase),
                '阴阳': '阴' if lunar_day > 15 else '阳',
                '五行': self._get_moon_phase_wuxing(lunar_day),
                '吉凶': self._get_moon_phase_luck(lunar_day)
            }
            self._available = True
            self._last_state = current_phase

        self._last_update = now
        return self._calculate_phase_change_interval(current_phase, state)

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
        interval = await moon_sensor.async_update()
        if interval:
            async_track_time_interval(hass, update_moon_phase, interval)

    await update_moon_phase(None)
    return entities