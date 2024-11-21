import logging
from datetime import datetime, timedelta
import cnlunar 
import re
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.util import dt
from homeassistant.helpers.event import async_track_time_change
from typing import Dict, List, Optional
import asyncio

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from .const import (
   DOMAIN,
   MAIN_SENSORS,
)

_LOGGER = logging.getLogger(__name__)

class AlmanacCache:
   def __init__(self, ttl: int = 300):
       self._cache = {}
       self._cache_time = {}
       self._ttl = ttl
   
   def get(self, key: str) -> Optional[str]:
       if key not in self._cache:
           return None
       if (datetime.now() - self._cache_time[key]).total_seconds() > self._ttl:
           del self._cache[key]
           del self._cache_time[key]
           return None
       return self._cache[key]
       
   def set(self, key: str, value: str):
       self._cache[key] = value
       self._cache_time[key] = datetime.now()

class AlmanacDevice:
   def __init__(self, entry_id: str, name: str):
       self._entry_id = entry_id
       self._name = name
       self.holidays: Dict[str, str] = {
           "2025-01-01": "元旦（天赦日）",
           "2025-01-28": "除夕（华严菩萨诞）",
           "2025-01-29": "春节（天腊之辰、弥勒佛圣诞）",
           "2025-01-30": "春节",
           "2025-01-31": "春节（万神都会、郝真人圣诞）",
           "2025-02-01": "春节",
           "2025-02-02": "春节（世界湿地日、孙祖清静元君诞）", 
           "2025-02-03": "春节",
           "2025-02-04": "春节（世界抗癌日、五行会）",
           "2025-04-04": "清明节",
           "2025-04-05": "清明节（五行会）",
           "2025-04-06": "清明节",
           "2025-05-01": "劳动节（文殊菩萨诞、日会）",
           "2025-05-02": "劳动节",
           "2025-05-03": "劳动节（世界新闻自由日）",
           "2025-05-04": "劳动节（中国青年节）",
           "2025-05-05": "劳动节（释迦牟尼佛诞、天君下降）",
           "2025-05-31": "端午节（世界无烟日、地腊之辰）",
           "2025-06-01": "端午节（国际儿童节）",
           "2025-06-02": "端午节",
           "2025-10-01": "国庆节（北斗大帝诞）",
           "2025-10-02": "国庆节（五行会）",
           "2025-10-03": "国庆节（西方五道诞）",
           "2025-10-04": "国庆节（世界动物日）",
           "2025-10-05": "国庆节",
           "2025-10-06": "中秋节（天赦日、太阴星君诞）",
           "2025-10-07": "国庆节",
           "2025-10-08": "国庆节"
       }
       self.workdays: Dict[str, str] = {
           "2025-01-26": "国际海关日（调休上班）",
           "2025-02-08": "张大帝诞日（调休上班）", 
           "2025-04-27": "调休上班",
           "2025-09-28": "调休上班",
           "2025-10-11": "调休上班"
       }
       
   @property
   def device_info(self):
       return DeviceInfo(
           identifiers={(DOMAIN, self._entry_id)},
           name=self._name,
           model="Chinese Almanac",
           manufacturer="道教",
       )

   def get_holiday(self, date_str: str, cnlunar_holidays: str) -> str:
       if date_str in self.holidays:
           return self.holidays[date_str]
       elif date_str in self.workdays:
           return self.workdays[date_str] 
       elif cnlunar_holidays:
           return cnlunar_holidays
       return "暂无节日"

def calculate_six_luminaries(lunar_month: int, lunar_day: int) -> str:
   six_luminaries = ["大安", "赤口", "先胜", "友引", "先负", "空亡"]
   index = (lunar_month + lunar_day - 1) % 6
   return six_luminaries[index]

def calculate_day_fortune(day_stem: str, day_branch: str) -> str:
    base_fortune_map = {'甲': '寅', '乙': '卯', '丙': '巳', '戊': '巳', '丁': '午', '己': '午', '庚': '申', '辛': '酉', '壬': '亥', '癸': '子'}
    heaven_stem_triad = {'甲': ['寅', '卯'], '乙': ['卯', '辰'], '丙': ['巳', '午'], '戊': ['巳', '午'], '丁': ['午', '未'], '己': ['午', '未'], '庚': ['申', '酉'], '辛': ['酉', '戌'], '壬': ['亥', '子'], '癸': ['子', '丑']}
    fortune_position = base_fortune_map.get(day_stem, '')
    is_in_triad = day_branch in heaven_stem_triad.get(day_stem, [])
    return (f"{day_branch}命进禄" if day_branch == fortune_position else f"{day_branch}命互禄" if is_in_triad else f"{day_stem}命进{fortune_position}禄")

class AlmanacSensor(SensorEntity):
    def __init__(self, device, name, sensor_type, is_main_sensor, hass):
        super().__init__()
        self._device = device
        self._type = sensor_type
        self._state = None
        self._attributes = {}
        self._available = False
        self._is_main_sensor = is_main_sensor
        self._attr_has_entity_name = True
        self._hass = hass
        self._custom_date = None
        self._custom_date_set_time = None

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
        return self._attributes if self._type in ['时辰凶吉', '时辰', '节气', '九宫飞星'] else {}

    @property
    def available(self):
        return self._available

    @property
    def icon(self):
        return 'mdi:calendar-text'

    async def _do_update(self):
        now = dt.now()
        local_now = dt.as_local(now).replace(tzinfo=None)
        if self._type == '时辰凶吉':
            await self._update_real_time(self._update_twohour_lucky, local_now)
        elif self._type == '时辰':
            await self._update_real_time(self._update_double_hour, local_now)
        else:
            await self._update_real_time(self._update_general, local_now)

    async def force_refresh(self) -> None:
        await self._do_update()
        self.async_write_ha_state()

    async def _update_real_time(self, update_func, now):
        try:
            await update_func(now)
            self._available = True
        except Exception:
            self._available = False

    async def async_update(self):
        await self._do_update()

    async def set_date(self, new_date: datetime) -> None:
        self._custom_date = new_date
        self._custom_date_set_time = datetime.now()
        local_now = dt.as_local(new_date).replace(tzinfo=None)
        if self._type == '时辰凶吉':
            await self._update_twohour_lucky(local_now)
        elif self._type == '时辰':
            await self._update_double_hour(local_now)
        else:
            await self._update_general(local_now)
        self.async_write_ha_state()

    async def _do_update(self):
        now = dt.now()
        
        if (self._custom_date and self._custom_date_set_time and 
            (datetime.now() - self._custom_date_set_time).total_seconds() < 60):
            local_now = dt.as_local(self._custom_date).replace(tzinfo=None)
        else:
            self._custom_date = None
            self._custom_date_set_time = None
            local_now = dt.as_local(now).replace(tzinfo=None)
            
        if self._type == '时辰凶吉':
            await self._update_real_time(self._update_twohour_lucky, local_now)
        elif self._type == '时辰':
            await self._update_real_time(self._update_double_hour, local_now)
        else:
            await self._update_real_time(self._update_general, local_now)

    async def _update_double_hour(self, now):
        try:
            hour, minute = now.hour, now.minute
            shichen = ['子时', '丑时', '寅时', '卯时', '辰时', '巳时',
                    '午时', '未时', '申时', '酉时', '戌时', '亥时']

            double_hour = (hour + 1) // 2 % 12
            is_first_hour = hour % 2 == 0
            ke = (minute // 15) + (1 if is_first_hour else 5)
            marks = ["初", "二", "三", "四", "五", "六", "七", "八"]
            mark = marks[ke - 1]
            self._state = f"{shichen[double_hour]}{mark}刻" if mark != "初" else f"{shichen[double_hour]}初"
            self._available = True
        except Exception:
            self._available = False
            
    async def _update_general(self, now):
        try:
            a = cnlunar.Lunar(now, godType='8char')
            formatted_date = now.strftime('%Y-%m-%d')
            lunar_holidays = []
            lunar_holidays.extend(a.get_legalHolidays())
            lunar_holidays.extend(a.get_otherHolidays())
            lunar_holidays.extend(a.get_otherLunarHolidays())
            lunar_holidays_str = self._clean_text(''.join(lunar_holidays))

            numbers = self._clean_text(self._format_dict(a.get_the9FlyStar()))
            nine_palace = numbers if numbers.isdigit() and len(numbers) == 9 else ""
            nine_palace_attrs = {}
            if numbers.isdigit() and len(numbers) == 9:
                positions = [
                    ('西北', '西北乾'), ('正北', '北坎'), ('东北', '东北艮'),
                    ('正西', '西兑'), ('中宫', '中宫'), ('正东', '东震'),
                    ('西南', '西南坤'), ('正南', '南离'), ('东南', '东南巽')
                ]
                star_colors = {
                    '1': '白', '2': '黑', '3': '碧', '4': '绿',
                    '5': '黄', '6': '白', '7': '赤', '8': '白', '9': '紫'
                }
                nine_palace_attrs = {
                    pos[0]: f"{pos[1]}{num}{star_colors[num]}" 
                    for pos, num in zip(positions, numbers)
                }

            solar_terms_dict = a.thisYearSolarTermsDic
            current_month = now.month
            current_day = now.day
            sorted_terms = sorted(solar_terms_dict.items(), key=lambda x: (x[1][0], x[1][1]))
            current_term = ""
            next_term = ""
            next_term_date = None
            
            for i, (term, (month, day)) in enumerate(sorted_terms):
                if i == len(sorted_terms) - 1:
                    if month < current_month or (month == current_month and day <= current_day):
                        current_term = term
                        next_term = sorted_terms[0][0]
                        next_month, next_day = sorted_terms[0][1]
                        next_term_date = f"{next_month}月{next_day}日"
                        break
                elif ((month < current_month) or (month == current_month and day <= current_day)) and \
                        ((sorted_terms[i+1][1][0] > current_month) or 
                        (sorted_terms[i+1][1][0] == current_month and sorted_terms[i+1][1][1] > current_day)):
                    current_term = term
                    next_term = sorted_terms[i+1][0]
                    next_month, next_day = sorted_terms[i+1][1]
                    next_term_date = f"{next_month}月{next_day}日"
                    break
                elif i == 0 and (month > current_month or (month == current_month and day > current_day)):
                    current_term = sorted_terms[-1][0]
                    next_term = term
                    next_term_date = f"{month}月{day}日"
                    break

            day_stem = a.day8Char[0]
            day_branch = a.day8Char[1]
            day_fortune = calculate_day_fortune(day_stem, day_branch)
            week_number = now.isocalendar()[1]

            dic = {
                '日期': formatted_date,
                '农历': f"{a.year8Char}({a.chineseYearZodiac})年 {a.lunarMonthCn}{a.lunarDayCn}",
                '星期': a.weekDayCn,
                '今日节日': self._device.get_holiday(formatted_date, lunar_holidays_str),
                '周数': f"{week_number}周",
                '八字': ' '.join([a.year8Char, a.month8Char, a.day8Char, a.twohour8Char]),
                '节气': current_term,
                '季节': a.lunarSeason,
                '生肖冲煞': a.chineseZodiacClash,
                '星座': a.starZodiac,
                '星次': a.todayEastZodiac,
                '彭祖百忌': self._clean_text(''.join(a.get_pengTaboo(long=4, delimit=' '))),
                '十二神': self._clean_text(' '.join(a.get_today12DayOfficer())),
                '廿八宿': self._clean_text(''.join(a.get_the28Stars())),
                '今日三合': self._clean_text(' '.join(a.zodiacMark3List)),
                '今日六合': a.zodiacMark6,
                '纳音': a.get_nayin(),
                '九宫飞星': nine_palace,
                '吉神方位': self._format_lucky_gods(a.get_luckyGodsDirection()),
                '今日胎神': a.get_fetalGod(),
                '今日吉神': self._clean_text(' '.join(a.goodGodName)),
                '今日凶煞': self._clean_text(' '.join(a.badGodName)),
                '宜忌等第': a.todayLevelName,
                '宜': self._clean_text(' '.join(a.goodThing)),
                '忌': self._clean_text(' '.join(a.badThing)),
                '时辰经络': self._clean_text(self._format_dict(a.meridians)),
                '六曜': calculate_six_luminaries(a.lunarMonth, a.lunarDay),
                '日禄': day_fortune
            }

            self._state = dic.get(self._type, "")
            if self._type == '九宫飞星' and nine_palace_attrs:
                self._attributes = nine_palace_attrs
            elif self._type == '节气' and next_term and next_term_date:
                self._attributes = {
                    "下一节气": f"{next_term} ({next_term_date})"
                }

            self._available = True
        except Exception:
            self._available = False

    async def _update_twohour_lucky(self, now):
        try:
            a = cnlunar.Lunar(now, godType='8char')
            lucky_list = a.get_twohourLuckyList()
            self._state = self._format_twohour_lucky(lucky_list, now)
            self._available = True
        except Exception:
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
        filters = [
            '上表章', '上册', '颁诏', '修置产室', '举正直', '选将', '宣政事', '冠带', '上官', '临政',
            '竖柱上梁', '修仓库', '营建', '穿井', '伐木', '畋猎', '招贤', '酝酿', '乘船渡水', '解除', 
            '缮城郭', '筑堤防', '修宫室', '安碓硙', '纳采', '针刺', '开渠', '平治道涂', '裁制', 
            '修饰垣墙', '塞穴', '庆赐', '破屋坏垣', '鼓铸', '启攒', '开仓', '纳畜', '牧养', '经络',
            '安抚边境', '选将', '布政事', '覃恩', '雪冤', '出师'
        ]
        words = text.split()
        filtered = [w for w in words if w not in filters]
        return ' '.join(filtered).strip()

async def async_setup_entry(
   hass: HomeAssistant, 
   entry: ConfigEntry, 
   async_add_entities: AddEntitiesCallback
) -> bool:
   config_data = dict(entry.data)
   entities, sensors = await setup_almanac_sensors(hass, entry.entry_id, config_data)
   
   async def update_sensors_batch(sensors_to_update):
       updates = [sensor.async_update() for sensor in sensors_to_update]
       await asyncio.gather(*updates)
       for sensor in sensors_to_update:
           sensor.async_write_ha_state()
           
   async_add_entities(entities)

   if DOMAIN not in hass.data:
       hass.data[DOMAIN] = {}
   
   if "almanac_sensors" not in hass.data[DOMAIN]:
       hass.data[DOMAIN]["almanac_sensors"] = {}
   
   hass.data[DOMAIN]["almanac_sensors"][entry.entry_id] = sensors

   return True

async def setup_almanac_sensors(hass: HomeAssistant, entry_id: str, config_data: dict):
    entities = []
    name = config_data.get("name", "中国老黄历")
    almanac_device = AlmanacDevice(entry_id, name)
    sensors = [
        AlmanacSensor(almanac_device, name, key, key in MAIN_SENSORS, hass)
        for key in [
            '日期', '农历', '星期', '今日节日', '周数', '八字', '节气',
            '季节', '时辰凶吉', '生肖冲煞', '星座', '星次',
            '彭祖百忌', '十二神', '廿八宿', '今日三合', '今日六合',
            '纳音', '九宫飞星', '吉神方位', '今日胎神', '今日吉神',
            '今日凶煞', '宜忌等第', '宜', '忌', '时辰经络', '时辰',
            '六曜', '日禄'
        ]
    ]
    entities.extend(sensors)

    async def update_sensors_batch(sensors_to_update):
        for sensor in sensors_to_update:
            await sensor._do_update()
            sensor.async_write_ha_state()

    async def midnight_update(now: datetime):
        await update_sensors_batch(sensors)

    async def quarter_hourly_update(now: datetime):
        shichen_sensors = [s for s in sensors if s._type == '时辰']
        await update_sensors_batch(shichen_sensors)

    async def two_hourly_update(now: datetime):
        lucky_sensors = [s for s in sensors if s._type == '时辰凶吉']
        await update_sensors_batch(lucky_sensors)

    async def hourly_update(now: datetime):
        date_sensors = ['日期', '农历', '八字', '今日节日']
        hourly_sensors = [s for s in sensors if s._type in date_sensors or 
                         s._type not in ['时辰凶吉', '时辰'] + date_sensors]
        await update_sensors_batch(hourly_sensors)

    async_track_time_change(hass, midnight_update, hour=0, minute=0, second=0)
    async_track_time_change(hass, quarter_hourly_update, minute=[0, 15, 30, 45], second=0)
    async_track_time_change(hass, two_hourly_update, hour=[0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22], minute=0, second=0)
    async_track_time_change(hass, hourly_update, minute=0, second=0)

    async def start_update(event=None):
        await update_sensors_batch(sensors)

    hass.bus.async_listen_once('homeassistant_started', start_update)

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    if "almanac_sensors" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["almanac_sensors"] = {}
    hass.data[DOMAIN]["almanac_sensors"][entry_id] = sensors

    return entities, sensors
