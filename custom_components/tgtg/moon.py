from __future__ import annotations
from astral import moon
import cnlunar 
import logging
import math
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.util import dt
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class AlmanacMoonSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.ENUM
    
    def __init__(self, device, sensor_type):
        self._device = device
        self._type = sensor_type
        self._state = None
        self._attributes = {}
        self._available = False
        self._last_update = None
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
        return self._moon_icons.get(self._state, 'mdi:moon-full') if self._type == '月相' else 'mdi:calendar-text'

    def _get_moon_phase_wuxing(self, d):
        return next(e for t, e in [(6, '水'), (11, '木'), (16, '火'), (22, '金'), (float('inf'), '土')] if int(d) <= t)

    def _get_moon_phase_luck(self, d):
        luck_days = {
            '大吉': [1, 3, 8, 11, 15, 16, 23, 28],  
            '吉': [2, 7, 13, 18, 22, 27, 29, 30],   
            '平': [5, 9, 10, 14, 20, 24, 25],       
            '凶': [4, 6, 12, 17, 19, 21, 26]      
        }
        
        day = int(d)
        for luck, days in luck_days.items():
            if day in days:
                return luck
        return '平吉'
        
    def _cn_number(self, n):
        if 1 <= n <= 10:
            return ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十'][n-1]
        elif 11 <= n <= 19:
            return f"十{self._cn_number(n-10)}"
        elif n == 20:
            return '二十'
        else:
            return f"二十{self._cn_number(n-20)}"

    def _get_night_moon_name(self, d):
        special_names = {
            15: '望月',
            16: '既望月',
            17: '立待月',
            18: '居待月',
            19: '寝待月',
            30: '晦月'
        }
        return special_names.get(d, f"{self._cn_number(d)}夜月")

    def _get_moon_phase_description(self, p):
        descriptions = {
            '朔月': '月亮完全不可见，月亮与太阳位于同一方向。此时月亮运行至日月同黄经之位，为农历每月初一。道教称此时阴阳相交，万物启始，适合静修、存想。',
            '峨眉月': '月亮呈细弧形，东方傍晚可见。峨眉之名取自娥眉新月之意，象征新生之气开始萌动。道家认为此时阳气初升，宜修炼内丹。此时可见约20%月面',
            '上弦月': '月亮外侧发亮，呈现半圆形。月球位于黄道上，与太阳相差90度，为农历七、八日前后。道教视其为阳气上升之象，契合人体小周天运行',
            '渐盈凸月': '月亮大部分可见，接近圆形。此时月相渐盈，寓意阳气渐盛，道教认为此乃天地之气由升而合，为修行采气之良时。',
            '满月': '月亮完整可见，呈现圆形。为农历十五、十六日前后，月亮运行至日月对照之位。道教认为此时阴阳交泰，天人合一，为修道采药、存想打坐的最佳时机。',
            '渐亏凸月': '月亮开始减亏，仍近似圆形。象征阳气开始收敛，阴气渐生。道教以此时为炼己修身、收心养性的时节。',
            '下弦月': '月亮内侧发亮，呈现半圆形。月球位于黄道上，为农历二十二、二十三日前后。道教视其为阴气上升之象，与人体经脉运行相应。',
            '残月': '月亮呈细弧形，清晨西方可见。此为月相将尽之象，道教认为此时天地之气归藏，适合收功打坐，为新月蓄势。'
        }
        return descriptions.get(p, '')

    def _get_lunar_day(self, l):
        cn = self._cn_number
        d = {}
        for i in range(1, 31):
            if i <= 10:
                d[f"初{cn(i)}"] = i
            elif i < 20:
                d[f"十{cn(i-10)}"] = i
            elif i == 20:
                d['二十'] = i
            else:
                d[f"廿{cn(i-20)}"] = i
        d['三十'] = 30
        return d.get(l.lunarDayCn, 1)

    def _calculate_phase_change_interval(self, c, s):
        return timedelta(minutes=min((next((t for t, p in self._phase_thresholds if s < t)) - s) * 24 * 60, 5))

    async def async_update(self) -> None:
        try:
            from math import sin, cos, asin, acos, radians, degrees, log10
            now = dt.now().replace(tzinfo=None)
            y, m, d = now.year, now.month, now.day
            h, mi, s = now.hour, now.minute, now.second
            
            if m <= 2:
                y -= 1
                m += 12
                
            a = y // 100
            b = 2 - a + a // 4
            jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5 + (h + mi/60 + s/3600)/24
            t = (jd - 2451545.0) / 36525
            
            L0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
            M = 357.52911 + 35999.05029 * t - 0.0001537 * t * t
            e = 0.016708634 - 0.000042037 * t - 0.0000001267 * t * t
            
            C = (1.914602 - 0.004817 * t - 0.000014 * t * t) * sin(radians(M)) + \
                (0.019993 - 0.000101 * t) * sin(radians(2 * M)) + 0.000289 * sin(radians(3 * M))
            L = L0 + C
            
            Lp = 218.3164477 + 481267.88123421 * t
            D = 297.8501921 + 445267.1114034 * t
            F = 93.272095 + 483202.0175233 * t
            
            phase = ((jd - 2451550.1) / 29.530588853)
            moon_age = phase * 29.530588853 % 29.530588853
            i = degrees(acos(cos(radians(D))))
            k = (1 + cos(radians(i))) / 2
            phase_percent = k * 100
            
            distance = 385000.56 * (1.0 - 0.0549 * cos(radians(D)))
            mag = -12.74 + 5 * log10(distance / 384400)
            theta = degrees(2 * asin(1737.1 / distance))
            deg = int(theta)
            minu = int((theta - deg) * 60)
            sec = ((theta - deg) * 60 - minu) * 60
            
            lunar = cnlunar.Lunar(now, godType='8char')
            lunar_day = self._get_lunar_day(lunar)
            current_phase = next((p for t, p in self._phase_thresholds if moon_age < t))
            
            if current_phase != self._last_state:
                self._state = current_phase
                self._attributes = {
                    '月龄': f"{moon_age:.1f} 天",
                    '夜月': self._get_night_moon_name(lunar_day),
                    '照亮度': f"{phase_percent:.1f}%",
                    '目视星等': f"{mag:.1f}",
                    '大小': f"{deg}° {minu}' {sec:.1f}\"",
                    '月相说明': self._get_moon_phase_description(current_phase),
                    '阴阳': '阴' if lunar_day > 15 else '阳',
                    '五行': self._get_moon_phase_wuxing(lunar_day),
                    '吉凶': self._get_moon_phase_luck(lunar_day)
                }
                self._available = True
                self._last_state = current_phase
                
            self._last_update = now
            return self._calculate_phase_change_interval(current_phase, moon_age)
            
        except Exception as e:
            _LOGGER.error(f"更新月相时出错: {str(e)}")
            raise

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
    name = config_data.get("name", "中国老黄历")
    almanac_device = AlmanacDevice(entry_id, name)
    moon_sensor = AlmanacMoonSensor(almanac_device, "月相")
    
    unsubscribe = None
    start_time = dt.now()

    async def update_moon_phase(now):
        nonlocal unsubscribe
        if (dt.now() - start_time).total_seconds() > 12 * 3600:
            if unsubscribe:
                unsubscribe()
            return

        try:
            interval = await moon_sensor.async_update()
            if interval:
                if unsubscribe:
                    unsubscribe()
                unsubscribe = async_track_time_interval(hass, update_moon_phase, interval)
        except Exception as e:
            _LOGGER.error(f"月相更新错误: {e}")

    async def async_remove():
        if unsubscribe:
            unsubscribe()

    moon_sensor.async_remove = async_remove
    await update_moon_phase(None)
    
    return [moon_sensor]
