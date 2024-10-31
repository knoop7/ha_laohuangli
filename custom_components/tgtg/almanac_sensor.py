import logging
from datetime import datetime, timedelta
import cnlunar 
import re
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.util import dt
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    MIN_TIME_BETWEEN_UPDATES,
    MIN_TIME_BETWEEN_TWOHOUR_UPDATES,
    MAIN_SENSORS,
)

_LOGGER = logging.getLogger(__name__)

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

class AlmanacSensor(SensorEntity):
    def __init__(self, device, name, sensor_type, is_main_sensor):
        self._device = device
        self._type = sensor_type
        self._state = None
        self._attributes = {}
        self._available = False
        self._is_main_sensor = is_main_sensor
        self._last_update = None
        self._attr_has_entity_name = True

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
        return None if self._is_main_sensor else EntityCategory.DIAGNOSTIC

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes if self._type in ['时辰凶吉', '时辰'] else {}

    @property
    def available(self):
        return self._available

    @property
    def icon(self):
        return 'mdi:calendar-text'

    async def async_update(self):
        now = dt.now().replace(tzinfo=None)
        
        if (self._last_update is not None and 
            now - self._last_update < MIN_TIME_BETWEEN_UPDATES and
            self._type not in ['时辰凶吉', '时辰']):
            return

        if self._type == '时辰凶吉':
            await self._update_twohour_lucky(now)
        elif self._type == '时辰':
            await self._update_double_hour(now)
        else:
            await self._update_general(now)

        self._last_update = now

    async def _update_double_hour(self, now):
        try:
            hour = now.hour
            minute = now.minute
            double_hour = int((hour + 1 + (0.5 if minute >= 30 else 0)) // 2 % 12)
            shichen = ['子时', '丑时', '寅时', '卯时', '辰时', '巳时', '午时', '未时', '申时', '酉时', '戌时', '亥时']
            quarter = ['初', '一刻', '二刻', '三刻'] 
            self._state = shichen[double_hour] + (quarter[int(minute // 15)] if minute // 15 < len(quarter) else '')
            self._available = True
            self._last_update = now
        except Exception as e:
            _LOGGER.error(f"更新： {e}")
            self._available = False

    async def _update_general(self, now):
        try:
            a = cnlunar.Lunar(now, godType='8char')
            formatted_date = now.strftime('%Y-%m-%d %H:%M')
            dic = {
                '日期': formatted_date,
                '农历': f"{a.year8Char}({a.chineseYearZodiac})年 {a.lunarMonthCn}{a.lunarDayCn}",
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
        except Exception as e:
            _LOGGER.error("更新Chinese Almanac传感器时出错: %s", e)
            self._available = False

    async def _update_twohour_lucky(self, now):
        try:
            a = cnlunar.Lunar(now, godType='8char')
            lucky_list = a.get_twohourLuckyList()
            self._state = self._format_twohour_lucky(lucky_list, now)
            self._available = True
        except Exception as e:
            _LOGGER.error("更新2小时传感器时出错: %s", e)
            self._available = False



    def _format_twohour_lucky(self, lucky_list, current_time):
        time_ranges = [
            "23:00-01:00", "01:00-03:00", "03:00-05:00", "05:00-07:00",
            "07:00-09:00", "09:00-11:00", "11:00-13:00", "13:00-15:00",
            "15:00-17:00", "17:00-19:00", "19:00-21:00", "21:00-23:00"
        ]

        current_hour = current_time.hour
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
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'[,;，；]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

async def setup_almanac_sensors(hass: HomeAssistant, entry_id: str, config_data: dict):
    entities = []
    name = config_data.get("name", "中国老黄历")
    almanac_device = AlmanacDevice(entry_id, name)

    sensors = [
        AlmanacSensor(almanac_device, name, key, key in MAIN_SENSORS) 
        for key in [
            '日期', '农历', '星期', '今日节日', '八字', '今日节气',
            '下一节气', '季节', '时辰凶吉', '生肖冲煞', '星座', '星次',
            '彭祖百忌', '十二神', '廿八宿', '今日三合', '今日六合',
            '纳音', '九宫飞星', '吉神方位', '今日胎神', '今日吉神',
            '今日凶煞', '宜忌等第', '宜', '忌', '时辰经络','时辰'
        ]
    ]
    entities.extend(sensors)

    async def update_twohour_lucky(now):
        for sensor in sensors:
            if sensor._type == '时辰凶吉':
                await sensor.async_update()

    async def update_double_hour(now):
        for sensor in sensors:
            if sensor._type == '时辰':
                await sensor.async_update()

    async_track_time_interval(hass, update_twohour_lucky, MIN_TIME_BETWEEN_TWOHOUR_UPDATES)
    async_track_time_interval(hass, update_double_hour, timedelta(minutes=1))
    
    return entities, sensors