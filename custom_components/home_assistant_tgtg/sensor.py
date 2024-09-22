import logging
from datetime import timedelta
import voluptuous as vol
import asyncio

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorEntity,
    SensorDeviceClass,
    SensorEntityDescription,
)
from homeassistant.const import CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo, EntityCategory

import datetime
import cnlunar

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(hours=1)
MIN_TIME_BETWEEN_TWOHOUR_UPDATES = timedelta(minutes=10)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default="中国老黄历"): cv.string,
})

DOMAIN = "tgtg"

MAIN_SENSORS = ['日期', '农历', '八字']

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up the Chinese Almanac sensor from config entry."""
    name = entry.data.get(CONF_NAME, "中国老黄历")
    
    device = ChineseAlmanacDevice(name, entry.entry_id)
    
    sensors = [
        ChineseAlmanacSensor(device, name, key, key in MAIN_SENSORS) for key in [
            '日期', '农历', '星期', '今日节日', '八字', '今日节气',
            '下一节气', '季节', '时辰凶吉', '生肖冲煞',
            '星座', '星次', '彭祖百忌', '十二神', '廿八宿',
            '今日三合', '今日六合', '纳音', '九宫飞星', '吉神方位',
            '今日胎神', '今日吉神', '今日凶煞', '宜忌等第', '宜', '忌', '时辰经络'
        ]
    ]
    
    async_add_entities(sensors, True)  

    async def update_twohour_lucky(now):
        for sensor in sensors:
            if sensor._type == '时辰凶吉':
                await sensor.async_update()

    hass.helpers.event.async_track_time_interval(update_twohour_lucky, MIN_TIME_BETWEEN_TWOHOUR_UPDATES)

class ChineseAlmanacDevice:
    """Representation of a Chinese Almanac device."""

    def __init__(self, name, entry_id):
        """Initialize the device."""
        self._name = name
        self._entry_id = entry_id

    @property
    def device_info(self):
        """Return device information about this Chinese Almanac device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=self._name,
            manufacturer="cnlunar",
            model="Chinese Almanac",
            entry_type="service",
        )

class ChineseAlmanacSensor(SensorEntity):
    def __init__(self, device, name, sensor_type, is_main_sensor):
        self._device = device
        self._name = name
        self._type = sensor_type
        self._state = None
        self._attributes = {}
        self._available = False
        self._is_main_sensor = is_main_sensor
        self._last_update = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} {self._type}"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"chinese_almanac_{self._type}"

    @property
    def device_info(self):
        """Return device information about this Chinese Almanac sensor."""
        return self._device.device_info

    @property
    def entity_category(self):
        """Return the entity category."""
        return None if self._is_main_sensor else EntityCategory.DIAGNOSTIC

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes if self._type == '时辰凶吉' else {}

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return 'mdi:calendar-text'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """Fetch new state data for the sensor."""
        now = datetime.datetime.now()
        
        if self._type == '时辰凶吉':
            await self._update_twohour_lucky(now)
        else:
            await self._update_general(now)

    async def _update_general(self, now):
        try:
            a = cnlunar.Lunar(now, godType='8char')
            
            dic = {
                '日期': a.date,
                '农历': f"{a.lunarYearCn}{a.year8Char}{a.chineseYearZodiac}年{a.lunarMonthCn}{a.lunarDayCn}",
                '星期': a.weekDayCn,
                '今日节日': self._clean_text(''.join(a.get_legalHolidays() + a.get_otherHolidays() + a.get_otherLunarHolidays())) or "暂无节日",
                '八字': ' '.join([a.year8Char, a.month8Char, a.day8Char, a.twohour8Char]),
                '今日节气': a.todaySolarTerms,
                '下一节气': a.nextSolarTerm,
                '季节': a.lunarSeason,
                '生肖冲煞': a.chineseZodiacClash,
                '星座': a.starZodiac,
                '星次': a.todayEastZodiac,
                '彭祖百忌': self._clean_text(''.join(a.get_pengTaboo())),
                '十二神': self._clean_text(' '.join(a.get_today12DayOfficer())),
                '廿八宿': self._clean_text(''.join(a.get_the28Stars())),
                '今日三合': self._clean_text(' '.join(a.zodiacMark3List)),
                '今日六合': a.zodiacMark6,
                '纳音': a.get_nayin(),
                '九宫飞星': self._clean_text(self._format_dict(a.get_the9FlyStar())),
                '吉神方位': self._format_lucky_gods(a.get_luckyGodsDirection()),
                '今日胎神': a.get_fetalGod(),
                '今日吉神': self._clean_text(' '.join(a.goodGodName)),
                '今日凶煞': self._clean_text(' '.join(a.badGodName)),
                '宜忌等第': a.todayLevelName,
                '宜': self._clean_text(' '.join(a.goodThing)),
                '忌': self._clean_text(' '.join(a.badThing)),
                '时辰经络': self._clean_text(self._format_dict(a.meridians))
            }

            self._state = dic.get(self._type, "")
            self._available = True
            self._last_update = now
        except Exception as e:
            _LOGGER.error(f"Error updating Chinese Almanac sensor: {e}")
            self._available = False

    @Throttle(MIN_TIME_BETWEEN_TWOHOUR_UPDATES)
    async def _update_twohour_lucky(self, now):
        try:
            a = cnlunar.Lunar(now, godType='8char')
            lucky_list = a.get_twohourLuckyList()
            self._state = self._format_twohour_lucky(lucky_list, now)
            self._available = True
            self._last_update = now
        except Exception as e:
            _LOGGER.error(f"Error updating twohour lucky sensor: {e}")
            self._available = False

    def _format_twohour_lucky(self, lucky_list, current_time):
        time_ranges = [
            "23:00-01:00", "01:00-03:00", "03:00-05:00", "05:00-07:00",
            "07:00-09:00", "09:00-11:00", "11:00-13:00", "13:00-15:00",
            "15:00-17:00", "17:00-19:00", "19:00-21:00", "21:00-23:00",
            "23:00-01:00"
        ]

        current_hour = current_time.hour
        current_twohour = current_hour // 2
        if current_hour == 23 or current_hour < 1:
            current_twohour = 0
        else:
            current_twohour = ((current_hour - 1) // 2 + 1) % 12

        current_luck = lucky_list[current_twohour]
        self._attributes = {
            time_range: lucky for time_range, lucky in zip(time_ranges, lucky_list)
        }
        return f"{time_ranges[current_twohour]} {current_luck}"

    def _format_lucky_gods(self, data):
        if isinstance(data, list):
            return ' '.join(data)
        elif isinstance(data, dict):
            return ' '.join([f"{k}:{v}" for k, v in data.items()])
        return str(data)

    def _format_dict(self, data):
        if isinstance(data, dict):
            return ' '.join([f"{k}{v}" for k, v in data.items()])
        return str(data)

    def _clean_text(self, text):
        import re
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'[,;，；]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()