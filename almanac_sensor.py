import logging
import asyncio, re, time
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Dict, List, Optional
from collections import defaultdict
import cnlunar
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback 
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from .const import DOMAIN, MAIN_SENSORS
from .services import async_setup_date_service

_LOGGER = logging.getLogger(__name__)

class TextProcessor:
    _FILTERS = {'上表章','上册','颁诏','修置产室','举正直','选将','宣政事','冠带','上官','临政','竖柱上梁','修仓库','营建','穿井','伐木','畋猎','招贤','酝酿','乘船渡水','解除','缮城郭','筑堤防','修宫室','安碓硙','纳采','针刺','开渠','平治道涂','裁制','修饰垣墙','塞穴','庆赐','破屋坏垣','鼓铸','启攒','开仓','纳畜','牧养','经络','安抚边境','选将','布政事','覃恩','雪冤','出师'}

    @staticmethod 
    def clean_text(text): return ' '.join(w for w in re.sub(r'\[.*?\]|[,;，；]', ' ', text).split() if w not in TextProcessor._FILTERS).strip()

    @staticmethod
    def format_lucky_gods(data): return ' '.join(data) if isinstance(data, list) else ' '.join(f"{k}:{v}" for k,v in data.items()) if isinstance(data, dict) else str(data)

    @staticmethod
    def format_dict(data): return ' '.join(f"{k}{v}" for k,v in data.items()) if isinstance(data, dict) else str(data)

class TimeHelper:
    SHICHEN = ['子时','丑时','寅时','卯时','辰时','巳时','午时','未时','申时','酉时','戌时','亥时']
    MARKS = ["初","一","二","三","四","五","六","七"]
    TIME_RANGES = ["23:00-01:00","01:00-03:00","03:00-05:00","05:00-07:00","07:00-09:00","09:00-11:00","11:00-13:00","13:00-15:00","15:00-17:00","17:00-19:00","19:00-21:00","21:00-23:00"]

    @staticmethod
    def get_current_shichen(hour, minute):
        shichen_index = 0 if hour == 23 else ((hour + 1) // 2) % 12
        total_minutes = (hour - (23 if hour == 23 else (hour + 1) // 2 * 2 - 1)) * 60 + minute
        ke = min(7, total_minutes // 15)
        return f"{TimeHelper.SHICHEN[shichen_index]}{'初' if ke == 0 else TimeHelper.MARKS[ke]}刻"

    @staticmethod
    def get_current_twohour(hour): return 0 if hour == 23 else ((hour + 1) // 2) % 12

    @staticmethod
    def format_twohour_lucky(lucky_list, current_time):
        i = TimeHelper.get_current_twohour(current_time.hour)
        return {'state': f"{TimeHelper.TIME_RANGES[i]} {lucky_list[i]}", 'attributes': dict(zip(TimeHelper.TIME_RANGES, lucky_list))}

class AlmanacDevice:
    def __init__(self, entry_id, name):
        self._entry_id = entry_id
        self._name = name
        self._holiday_cache = {"2025-01-01":"元旦（天赦日）","2025-01-28":"除夕（华严菩萨诞）","2025-01-29":"春节（天腊之辰、弥勒佛圣诞）","2025-01-30":"春节","2025-01-31":"春节（万神都会、郝真人圣诞）","2025-02-01":"春节","2025-02-02":"春节（世界湿地日、孙祖清静元君诞）","2025-02-03":"春节","2025-02-04":"春节（世界抗癌日、五行会）","2025-04-06":"清明节","2025-05-01":"劳动节（文殊菩萨诞、日会）","2025-05-02":"劳动节","2025-05-03":"劳动节（世界新闻自由日）","2025-05-04":"劳动节（中国青年节）","2025-05-05":"劳动节（释迦牟尼佛诞、天君下降）","2025-05-31":"端午节（世界无烟日、地腊之辰）","2025-06-01":"端午节（国际儿童节）","2025-06-02":"端午节","2025-10-01":"国庆节（北斗大帝诞）","2025-10-02":"国庆节（五行会）","2025-10-03":"国庆节（西方五道诞）","2025-10-04":"国庆节（世界动物日）","2025-10-05":"国庆节","2025-10-06":"中秋节（天赦日、太阴星君诞）","2025-10-07":"国庆节","2025-10-08":"国庆节"}
        self._workday_cache = {"2025-01-26":"国际海关日（调休上班）","2025-02-08":"张大帝诞日（调休上班）","2025-04-27":"调休上班","2025-09-28":"调休上班","2025-10-11":"调休上班"}

    @property
    def device_info(self): return DeviceInfo(identifiers={(DOMAIN, self._entry_id)}, name=self._name, model="Chinese Almanac", manufacturer="道教")

    def get_holiday(self, date_str, cnlunar_holidays): return self._holiday_cache.get(date_str) or self._workday_cache.get(date_str) or cnlunar_holidays or "暂无节日"

class UpdateManager:
    def __init__(self):
        self._last_update = {}
        self._lock = asyncio.Lock()
        self._update_counts = defaultdict(int)
        self._last_reset = datetime.now()

    async def can_update(self, sensor_type):
        now = datetime.now()
        if (now - self._last_reset).total_seconds() > 3600:
            self._update_counts.clear()
            self._last_reset = now
        if self._update_counts[sensor_type] >= 120: return False
        last = self._last_update.get(sensor_type)
        if not last or (now - last) >= timedelta(seconds=5):
            self._last_update[sensor_type] = now
            self._update_counts[sensor_type] += 1
            return True
        return False

class AlmanacSensor(SensorEntity):
    _shared_lunar_cache = {}  
    _cache_lock = asyncio.Lock()  
    _MAX_CACHE_SIZE = 24 
    
    def __init__(self, device, name, sensor_type, is_main_sensor, hass):
        self._device, self._type, self._hass = device, sensor_type, hass
        self._is_main_sensor = is_main_sensor
        self._state = self._last_state = self._last_update = None
        self._attributes = {}
        self._available, self._cleanup_called, self._updating = True, False, False
        self._attr_has_entity_name = True
        self._custom_date = self._custom_date_set_time = None
        self._update_lock = asyncio.Lock()
        self._text_processor, self._time_helper = TextProcessor(), TimeHelper()

    @property
    def name(self): return self._type
    @property
    def unique_id(self): return f"{self._device._entry_id}_{self._type}"
    @property
    def device_info(self): return self._device.device_info
    @property
    def entity_category(self): return None if self._is_main_sensor else EntityCategory.DIAGNOSTIC
    @property
    def state(self): return self._state
    @property
    def extra_state_attributes(self): return self._attributes if self._type in ['时辰凶吉','时辰','节气','九宫飞星'] else {}
    @property
    def available(self): return self._available
    @property
    def icon(self): return 'mdi:calendar-text'
    
    @classmethod
    async def _get_lunar_data(cls, date):
        key = date.strftime('%Y-%m-%d_%H')  
        
        async with cls._cache_lock:
            if key in cls._shared_lunar_cache:
                return cls._shared_lunar_cache[key]
            try:
                data = cnlunar.Lunar(date, godType='8char')
                cls._shared_lunar_cache[key] = data
                
                if len(cls._shared_lunar_cache) > cls._MAX_CACHE_SIZE:
                    oldest = min(cls._shared_lunar_cache.keys())  
                    cls._shared_lunar_cache.pop(oldest)
                return data
            except Exception as e:
                _LOGGER.error(f"计算数据时出错: {e}")
                return None

    async def _get_current_time(self):
        if (self._custom_date and self._custom_date_set_time and 
            (datetime.now() - self._custom_date_set_time).total_seconds() < 60):
            return dt.as_local(self._custom_date).replace(tzinfo=None)
            
        self._custom_date = self._custom_date_set_time = None
        return dt.as_local(dt.now()).replace(tzinfo=None)

    async def async_update(self):
        if self._cleanup_called: return
        
        now = datetime.now()
        try:
            async with self._update_lock:
                try:
                    self._updating = True
                    current_time = await self._get_current_time()
                    
                    update_map = {'时辰凶吉': self._update_twohour_lucky, 
                                '时辰': self._update_double_hour}
                    update_func = update_map.get(self._type, self._update_general)
                    
                    new_state = await update_func(current_time)
                    if new_state != self._last_state:
                        self._state = self._last_state = new_state
                        self._available = True
                        self._last_update = now
                finally:
                    self._updating = False
        except Exception as e:
            _LOGGER.error(f"更新传感器时出错 {self._type}: {e}")
            self._available = False

    async def cleanup(self):
        try:
            self._cleanup_called = True
            self._updating = False
            self._available = False
            
            if self._update_lock.locked():
                self._update_lock.release()
                
            self._attributes.clear()
            self._state = None
            
        except Exception as e:
            _LOGGER.error(f"清理时出错: {e}")

    async def _update_double_hour(self, now):
        try:
            self._state = self._time_helper.get_current_shichen(now.hour, now.minute)
            self._available = True
            return self._state
        except: 
            self._available = False
            return None

    async def _update_twohour_lucky(self, now):
        try:
            lunar_data = await self._get_lunar_data(now)
            if lunar_data:
                lucky_data = self._time_helper.format_twohour_lucky(lunar_data.get_twohourLuckyList(), now)
                self._state, self._attributes, self._available = lucky_data['state'], lucky_data['attributes'], True
                return self._state
            self._available = False
            return None
        except:
            self._available = False
            return None

    async def _process_solar_terms(self, solar_terms_dict, current_month, current_day):
        terms = sorted(solar_terms_dict.items(), key=lambda x: (x[1][0], x[1][1]))
        for i, (term, (month, day)) in enumerate(terms):
            if i == len(terms) - 1:
                if month < current_month or (month == current_month and day <= current_day):
                    return term, terms[0][0], f"{terms[0][1][0]}月{terms[0][1][1]}日"
            elif ((month < current_month) or (month == current_month and day <= current_day)) and ((terms[i+1][1][0] > current_month) or (terms[i+1][1][0] == current_month and terms[i+1][1][1] > current_day)):
                return term, terms[i+1][0], f"{terms[i+1][1][0]}月{terms[i+1][1][1]}日"
            elif i == 0 and (month > current_month or (month == current_month and day > current_day)):
                return terms[-1][0], term, f"{month}月{day}日"
        return "", "", ""

    async def set_date(self, new_date):
        self._custom_date, self._custom_date_set_time = new_date, datetime.now()
        await self.async_update()
        self.async_write_ha_state()

    async def _update_general(self, now):
        try:
            lunar_data = await self._get_lunar_data(now)
            if not lunar_data:
                self._available = False
                return
                
            formatted_date = now.strftime('%Y-%m-%d')
            
            lunar_holidays = (lunar_data.get_legalHolidays() + 
                          lunar_data.get_otherHolidays() + 
                          lunar_data.get_otherLunarHolidays())
            lunar_holidays_str = self._text_processor.clean_text(''.join(lunar_holidays))
            
            numbers = self._text_processor.clean_text(
                self._text_processor.format_dict(lunar_data.get_the9FlyStar()))
            nine_palace_attrs = {}
            
            if numbers.isdigit() and len(numbers) == 9:
                positions = ['西北乾','北坎','东北艮','西兑','中宫','东震','西南坤','南离','东南巽']
                pos_short = ['西北','正北','东北','正西','中宫','正东','西南','正南','东南']  
                star_colors = {'1':'白','2':'黑','3':'碧','4':'绿','5':'黄','6':'白','7':'赤','8':'白','9':'紫'}
                nine_palace_attrs.update({s: f"{p}{n}{star_colors[n]}" for s,p,n in zip(pos_short,positions,numbers) if n in star_colors})

            term, next_term, next_date = await self._process_solar_terms(lunar_data.thisYearSolarTermsDic, now.month, now.day)
            
            stem, branch = lunar_data.day8Char[0], lunar_data.day8Char[1]
            six_idx = (lunar_data.lunarMonth + lunar_data.lunarDay - 1) % 6
            
            base_luck = {'甲':'寅','乙':'卯','丙':'巳','戊':'巳','丁':'午','己':'午','庚':'申','辛':'酉','壬':'亥','癸':'子'}
            stem_group = {'甲':['寅','卯'],'乙':['卯','辰'],'丙':['巳','午'],'戊':['巳','午'],'丁':['午','未'],'己':['午','未'],'庚':['申','酉'],'辛':['酉','戌'],'壬':['亥','子'],'癸':['子','丑']}
            luck_pos = base_luck.get(stem, '')
            
            day_fortune = (f"{branch}命进禄" if branch == luck_pos else
                         f"{branch}命互禄" if branch in stem_group.get(stem, []) else
                         f"{stem}命进{luck_pos}禄")

            state_map = {
                '日期': formatted_date,
                '农历': f"{lunar_data.year8Char}({lunar_data.chineseYearZodiac})年 {lunar_data.lunarMonthCn}{lunar_data.lunarDayCn}",
                '星期': lunar_data.weekDayCn,
                '周数': f"{now.isocalendar()[1]}周",
                '今日节日': self._device.get_holiday(formatted_date, lunar_holidays_str),
                '八字': f"{lunar_data.year8Char} {lunar_data.month8Char} {lunar_data.day8Char} {lunar_data.twohour8Char}",
                '节气': term,
                '季节': lunar_data.lunarSeason,
                '生肖冲煞': lunar_data.chineseZodiacClash,
                '星座': lunar_data.starZodiac,
                '星次': lunar_data.todayEastZodiac,
                '彭祖百忌': self._text_processor.clean_text(''.join(lunar_data.get_pengTaboo(long=4,delimit=' '))),
                '十二神': self._text_processor.clean_text(' '.join(lunar_data.get_today12DayOfficer())),
                '廿八宿': self._text_processor.clean_text(''.join(lunar_data.get_the28Stars())),
                '今日三合': self._text_processor.clean_text(' '.join(lunar_data.zodiacMark3List)),
                '今日六合': lunar_data.zodiacMark6,
                '纳音': lunar_data.get_nayin(),
                '九宫飞星': numbers,
                '吉神方位': self._text_processor.format_lucky_gods(lunar_data.get_luckyGodsDirection()),
                '今日胎神': lunar_data.get_fetalGod(),
                '今日吉神': self._text_processor.clean_text(' '.join(lunar_data.goodGodName)),
                '今日凶煞': self._text_processor.clean_text(' '.join(lunar_data.badGodName)),
                '宜忌等第': lunar_data.todayLevelName,
                '宜': self._text_processor.clean_text(' '.join(lunar_data.goodThing)),
                '忌': self._text_processor.clean_text(' '.join(lunar_data.badThing)),
                '时辰经络': self._text_processor.clean_text(self._text_processor.format_dict(lunar_data.meridians)),
                '六曜': ["大安","赤口","先胜","友引","先负","空亡"][six_idx],
                '日禄': day_fortune
            }

            self._state = state_map.get(self._type, '')
            
            if self._type == '九宫飞星' and nine_palace_attrs:
                self._attributes = nine_palace_attrs
            elif self._type == '节气' and next_term and next_date:
                self._attributes = {"下一节气": f"{next_term} ({next_date})"}
                
            self._available = True
            return self._state
            
        except Exception:
            self._available = False
            return None

def setup_sensor_updates(hass: HomeAssistant, sensors):
    UNSUB_KEY = "almanac_unsubs"
    update_mgr = UpdateManager()
    
    if DOMAIN in hass.data:
        if UNSUB_KEY in hass.data[DOMAIN]:
            [unsub() for unsub in hass.data[DOMAIN][UNSUB_KEY]]
            hass.data[DOMAIN][UNSUB_KEY] = []

    async def process_updates(sensors_to_update, group_type):
        async with update_mgr._lock:
            if not await update_mgr.can_update(group_type): return
            [await s.async_update() or s.async_write_ha_state() for s in sensors_to_update if not s._updating and not s._cleanup_called]

    @callback
    def create_update_cb(group_sensors, group_type):
        async def _cb(*_): await process_updates(group_sensors, group_type)
        @callback
        def _handler(*args): hass.async_create_task(_cb())
        return _handler

    sensor_groups = {
        'shichen': [s for s in sensors if s._type == '时辰'],
        'other': [s for s in sensors if s._type not in ['时辰', '时辰凶吉', '日期']]
    }

    update_times = {
        'shichen': {'minute': [0,15,30,45]},
        'other': {'hour': '*', 'minute': 0}
    }

    for group, group_sensors in sensor_groups.items():
        if group_sensors:
            hass.data.setdefault(DOMAIN, {}).setdefault(UNSUB_KEY, []).append(
                async_track_time_change(hass, create_update_cb(group_sensors, group), **update_times[group]))

async def setup_almanac_sensors(hass, entry_id, config_data):
    if DOMAIN not in hass.data: hass.data[DOMAIN] = {}
    if "almanac_sensors" not in hass.data[DOMAIN]: hass.data[DOMAIN]["almanac_sensors"] = {}
    
    if entry_id in hass.data[DOMAIN]["almanac_sensors"]:
        [await s.cleanup() for s in hass.data[DOMAIN]["almanac_sensors"][entry_id]]
        hass.data[DOMAIN]["almanac_sensors"][entry_id] = []

    device = AlmanacDevice(entry_id, config_data.get("name", "中国老黄历"))
    
    SENSOR_KEYS = ['日期','农历','星期','今日节日','周数','八字','节气','季节','时辰凶吉','生肖冲煞',
                   '星座','星次','彭祖百忌','十二神','廿八宿','今日三合','今日六合','纳音','九宫飞星',
                   '吉神方位','今日胎神','今日吉神','今日凶煞','宜忌等第','宜','忌','时辰经络','时辰',
                   '六曜','日禄']
    
    sensors = [AlmanacSensor(device, config_data.get("name", "中国老黄历"), key, key in MAIN_SENSORS, hass) for key in SENSOR_KEYS]
    setup_sensor_updates(hass, sensors)
    hass.data[DOMAIN]["almanac_sensors"][entry_id] = sensors
    return sensors, sensors

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> bool:
    try:
        if entry.entry_id in hass.data.get(DOMAIN, {}).get("almanac_sensors", {}): return True
            
        entities, sensors = await setup_almanac_sensors(hass, entry.entry_id, dict(entry.data))
        if DOMAIN not in hass.data: hass.data[DOMAIN] = {}
        if "almanac_sensors" not in hass.data[DOMAIN]: hass.data[DOMAIN]["almanac_sensors"] = {}
            
        await async_setup_date_service(hass)
        async_add_entities(entities)
        hass.data[DOMAIN]["almanac_sensors"][entry.entry_id] = sensors
        return True
    except Exception: return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if DOMAIN not in hass.data: return True
    try:
        if "almanac_unsubs" in hass.data[DOMAIN]:
            [unsub() for unsub in hass.data[DOMAIN]["almanac_unsubs"]]
            hass.data[DOMAIN]["almanac_unsubs"] = []
            
        if "almanac_sensors" in hass.data[DOMAIN]:
            [await s.cleanup() for s in hass.data[DOMAIN]["almanac_sensors"].get(entry.entry_id, [])]
            hass.data[DOMAIN]["almanac_sensors"].pop(entry.entry_id, None)
            
        if not hass.data[DOMAIN]["almanac_sensors"]:
            hass.data.pop(DOMAIN, None)
        return True
    except Exception: return False
