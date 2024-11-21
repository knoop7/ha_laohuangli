from datetime import datetime, timedelta
import cnlunar
import re
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant 
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.util import dt
from homeassistant.helpers.event import async_track_time_change
from typing import Dict, List, Optional, Any
import asyncio
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, MAIN_SENSORS

class OptimizedCache:
    def __init__(self, ttl: int = 300):
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._ttl = ttl
        self._lock = asyncio.Lock()
        
    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._cache:
                return None
            if (datetime.now() - self._cache_time[key]).total_seconds() > self._ttl:
                del self._cache[key]
                del self._cache_time[key] 
                return None
            return self._cache[key]

    async def set(self, key: str, value: Any):
        async with self._lock:
            self._cache[key] = value
            self._cache_time[key] = datetime.now()

class LunarCalculator:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._cache = OptimizedCache(ttl=3600)
        
    @lru_cache(maxsize=100)
    def _calculate_lunar(self, date_str: str, hour: int = 0, minute: int = 0):
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            date = date.replace(hour=hour, minute=minute)
            return cnlunar.Lunar(date, godType='8char')
        except Exception:
            return None
        
    async def get_lunar_data(self, date: datetime):
        date_str = date.strftime('%Y-%m-%d')
        hour = date.hour
        minute = date.minute
        
        cache_key = f"lunar_{date_str}_{hour:02d}_{minute:02d}"
        
        if cached_data := await self._cache.get(cache_key):
            return cached_data
            
        loop = asyncio.get_event_loop()
        try:
            lunar_data = await loop.run_in_executor(
                self._executor,
                self._calculate_lunar,
                date_str,
                hour,
                minute
            )
            if lunar_data:
                await self._cache.set(cache_key, lunar_data)
            return lunar_data
        except Exception:
            return None

class AlmanacDevice:
    def __init__(self, entry_id: str, name: str):
        self._entry_id = entry_id
        self._name = name
        self._holiday_cache = self._init_holiday_cache()
        self._workday_cache = self._init_workday_cache()
        
    def _init_holiday_cache(self) -> Dict[str, str]:
        return {
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
    
    def _init_workday_cache(self) -> Dict[str, str]:
        return {
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
            manufacturer="道教"
        )

    def get_holiday(self, date_str: str, cnlunar_holidays: str) -> str:
        return (self._holiday_cache.get(date_str) or 
                self._workday_cache.get(date_str) or 
                cnlunar_holidays or "暂无节日")

class TimeCalculator:
    @staticmethod
    def calculate_six_luminaries(lunar_month: int, lunar_day: int) -> str:
        six_luminaries = ["大安", "赤口", "先胜", "友引", "先负", "空亡"]
        index = (lunar_month + lunar_day - 1) % 6
        return six_luminaries[index]

    @staticmethod
    def calculate_day_fortune(day_stem: str, day_branch: str) -> str:
        base_fortune = {
            '甲': '寅', '乙': '卯', '丙': '巳', '戊': '巳', 
            '丁': '午', '己': '午', '庚': '申', '辛': '酉', 
            '壬': '亥', '癸': '子'
        }
        stem_triad = {
            '甲': ['寅', '卯'], '乙': ['卯', '辰'], 
            '丙': ['巳', '午'], '戊': ['巳', '午'],
            '丁': ['午', '未'], '己': ['午', '未'], 
            '庚': ['申', '酉'], '辛': ['酉', '戌'],
            '壬': ['亥', '子'], '癸': ['子', '丑']
        }
        fortune_pos = base_fortune.get(day_stem, '')
        is_in_triad = day_branch in stem_triad.get(day_stem, [])
        return (f"{day_branch}命进禄" if day_branch == fortune_pos else 
                f"{day_branch}命互禄" if is_in_triad else 
                f"{day_stem}命进{fortune_pos}禄")

class AlmanacTextProcessor:
    def __init__(self):
        self._filters = {
            '上表章', '上册', '颁诏', '修置产室', '举正直', 
            '选将', '宣政事', '冠带', '上官', '临政',
            '竖柱上梁', '修仓库', '营建', '穿井', '伐木', 
            '畋猎', '招贤', '酝酿', '乘船渡水', '解除',
            '缮城郭', '筑堤防', '修宫室', '安碓硙', '纳采', 
            '针刺', '开渠', '平治道涂', '裁制',
            '修饰垣墙', '塞穴', '庆赐', '破屋坏垣', '鼓铸', 
            '启攒', '开仓', '纳畜', '牧养', '经络',
            '安抚边境', '选将', '布政事', '覃恩', '雪冤', '出师'
        }
        
    def clean_text(self, text: str) -> str:
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'[,;，；]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        words = text.split()
        return ' '.join(w for w in words if w not in self._filters).strip()

    def format_lucky_gods(self, data: Any) -> str:
        if isinstance(data, list):
            return ' '.join(data)
        if isinstance(data, dict):
            return ' '.join(f"{k}:{v}" for k, v in data.items())
        return str(data)

    def format_dict(self, data: Any) -> str:
        if isinstance(data, dict):
            return ' '.join(f"{k}{v}" for k, v in data.items())
        return str(data)

class TimeHelper:
    SHICHEN = ['子时', '丑时', '寅时', '卯时', '辰时', '巳时',
               '午时', '未时', '申时', '酉时', '戌时', '亥时']
    
    MARKS = ["初", "一", "二", "三", "四", "五", "六", "七"]
    
    TIME_RANGES = [
        "23:00-01:00", "01:00-03:00", "03:00-05:00", "05:00-07:00",
        "07:00-09:00", "09:00-11:00", "11:00-13:00", "13:00-15:00", 
        "15:00-17:00", "17:00-19:00", "19:00-21:00", "21:00-23:00"
    ]
    
    @classmethod
    def get_shichen_start_hour(cls, hour: int) -> int:
        if hour == 23:
            return 23
        return (hour + 1) // 2 * 2 - 1

    @classmethod
    def get_current_shichen(cls, hour: int, minute: int) -> str:
        if hour == 23:
            shichen_index = 0 
        else:
            shichen_index = ((hour + 1) // 2) % 12
        shichen_start = cls.get_shichen_start_hour(hour)
        total_minutes = (hour - shichen_start) * 60 + minute        
        ke = total_minutes // 15
        ke = max(0, min(7, ke))
        if ke == 0:
            return f"{cls.SHICHEN[shichen_index]}初"
        else:
            return f"{cls.SHICHEN[shichen_index]}{cls.MARKS[ke]}刻"
    
    @classmethod
    def get_current_twohour(cls, hour: int) -> int:
        if hour == 23:
            return 0  
        return ((hour + 1) // 2) % 12
        
    @staticmethod
    def get_nine_palace_positions():
        return [
            ('西北', '西北乾'), ('正北', '北坎'), ('东北', '东北艮'),
            ('正西', '西兑'), ('中宫', '中宫'), ('正东', '东震'),
            ('西南', '西南坤'), ('正南', '南离'), ('东南', '东南巽')
        ]

    @staticmethod
    def get_star_colors():
        return {
            '1': '白', '2': '黑', '3': '碧', '4': '绿',
            '5': '黄', '6': '白', '7': '赤', '8': '白', '9': '紫'
        }

    @classmethod
    def format_twohour_lucky(cls, lucky_list, current_time):
        current_twohour = cls.get_current_twohour(current_time.hour)
        current_luck = lucky_list[current_twohour]
        return {
            'state': f"{cls.TIME_RANGES[current_twohour]} {current_luck}",
            'attributes': dict(zip(cls.TIME_RANGES, lucky_list))
        }

class SensorStateHelper:
    def __init__(self):
        self.time_helper = TimeHelper()
        self.text_processor = AlmanacTextProcessor()


class AlmanacSensor(SensorEntity):
    def __init__(self, device: AlmanacDevice, name: str, sensor_type: str, 
        is_main_sensor: bool, hass: HomeAssistant):
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
        self._lunar_calculator = LunarCalculator()
        self._state_helper = SensorStateHelper()
        self._update_lock = asyncio.Lock()
        
    @property
    def name(self): return self._type
    @property
    def unique_id(self): return f"{self._device._entry_id}_{self._type}"
    @property
    def device_info(self): return self._device.device_info
    @property
    def entity_category(self): 
        return None if self._is_main_sensor else EntityCategory.DIAGNOSTIC
    @property
    def state(self): return self._state
    @property
    def extra_state_attributes(self):
        return self._attributes if self._type in ['时辰凶吉', '时辰', '节气', '九宫飞星'] else {}
    @property
    def available(self): return self._available
    @property
    def icon(self): return 'mdi:calendar-text'

    async def _get_current_time(self) -> datetime:
        now = dt.now()
        if (self._custom_date and self._custom_date_set_time and 
            (datetime.now() - self._custom_date_set_time).total_seconds() < 60):
            return dt.as_local(self._custom_date).replace(tzinfo=None)
        self._custom_date = None
        self._custom_date_set_time = None
        return dt.as_local(now).replace(tzinfo=None)

    async def _do_update(self):
        async with self._update_lock:
            local_now = await self._get_current_time()
            update_funcs = {
                '时辰凶吉': self._update_twohour_lucky,
                '时辰': self._update_double_hour
            }
            try:
                update_func = update_funcs.get(self._type, self._update_general)
                await update_func(local_now)
                self._available = True
            except Exception:
                self._available = False

    async def force_refresh(self) -> None:
        await self._do_update()
        self.async_write_ha_state()

    async def async_update(self):
        await self._do_update()

    async def set_date(self, new_date: datetime) -> None:
        self._custom_date = new_date
        self._custom_date_set_time = datetime.now()
        await self._do_update()
        self.async_write_ha_state()

    async def _update_double_hour(self, now: datetime):
        try:
            self._state = TimeHelper.get_current_shichen(
                now.hour, now.minute
            )
            self._available = True
        except Exception:
            self._available = False

    async def _update_twohour_lucky(self, now: datetime):
        lunar_data = await self._lunar_calculator.get_lunar_data(now)  
        if not lunar_data:
            self._available = False
            return
            
        lucky_data = self._state_helper.time_helper.format_twohour_lucky(
            lunar_data.get_twohourLuckyList(), 
            now
        )
        self._state = lucky_data['state']
        self._attributes = lucky_data['attributes']
        self._available = True

    async def _process_solar_terms(self, solar_terms_dict: Dict, 
                                 current_month: int, current_day: int):
        sorted_terms = sorted(solar_terms_dict.items(), 
                            key=lambda x: (x[1][0], x[1][1]))
        current_term = next_term = next_term_date = ""
        
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
                
        return current_term, next_term, next_term_date

    async def _update_general(self, now: datetime):
        lunar_data = await self._lunar_calculator.get_lunar_data(now)  
        if not lunar_data:
            self._available = False
            return
            
        try:
            formatted_date = now.strftime('%Y-%m-%d')
            lunar_holidays = []
            lunar_holidays.extend(lunar_data.get_legalHolidays())
            lunar_holidays.extend(lunar_data.get_otherHolidays())
            lunar_holidays.extend(lunar_data.get_otherLunarHolidays())
            lunar_holidays_str = self._state_helper.text_processor.clean_text(
                ''.join(lunar_holidays)
            )

            numbers = self._state_helper.text_processor.clean_text(
                self._state_helper.text_processor.format_dict(
                    lunar_data.get_the9FlyStar()
                )
            )
            
            nine_palace_attrs = {}
            if numbers.isdigit() and len(numbers) == 9:
                positions = TimeHelper.get_nine_palace_positions()
                star_colors = TimeHelper.get_star_colors()
                nine_palace_attrs = {
                    pos[0]: f"{pos[1]}{num}{star_colors[num]}" 
                    for pos, num in zip(positions, numbers)
                }

            current_term, next_term, next_term_date = await self._process_solar_terms(
                lunar_data.thisYearSolarTermsDic,
                now.month,
                now.day
            )

            day_stem = lunar_data.day8Char[0]
            day_branch = lunar_data.day8Char[1]
            day_fortune = TimeCalculator.calculate_day_fortune(day_stem, day_branch)
            week_number = now.isocalendar()[1]

            state_dict = {
                '日期': formatted_date,
                '农历': f"{lunar_data.year8Char}({lunar_data.chineseYearZodiac})年 {lunar_data.lunarMonthCn}{lunar_data.lunarDayCn}",
                '星期': lunar_data.weekDayCn,
                '今日节日': self._device.get_holiday(formatted_date, lunar_holidays_str),
                '周数': f"{week_number}周",
                '八字': ' '.join([lunar_data.year8Char, lunar_data.month8Char, lunar_data.day8Char, lunar_data.twohour8Char]),
                '节气': current_term,
                '季节': lunar_data.lunarSeason,
                '生肖冲煞': lunar_data.chineseZodiacClash,
                '星座': lunar_data.starZodiac,
                '星次': lunar_data.todayEastZodiac,
                '彭祖百忌': self._state_helper.text_processor.clean_text(''.join(lunar_data.get_pengTaboo(long=4, delimit=' '))),
                '十二神': self._state_helper.text_processor.clean_text(' '.join(lunar_data.get_today12DayOfficer())),
                '廿八宿': self._state_helper.text_processor.clean_text(''.join(lunar_data.get_the28Stars())),
                '今日三合': self._state_helper.text_processor.clean_text(' '.join(lunar_data.zodiacMark3List)),
                '今日六合': lunar_data.zodiacMark6,
                '纳音': lunar_data.get_nayin(),
                '九宫飞星': numbers,
                '吉神方位': self._state_helper.text_processor.format_lucky_gods(lunar_data.get_luckyGodsDirection()),
                '今日胎神': lunar_data.get_fetalGod(),
                '今日吉神': self._state_helper.text_processor.clean_text(' '.join(lunar_data.goodGodName)),
                '今日凶煞': self._state_helper.text_processor.clean_text(' '.join(lunar_data.badGodName)),
                '宜忌等第': lunar_data.todayLevelName,
                '宜': self._state_helper.text_processor.clean_text(' '.join(lunar_data.goodThing)),
                '忌': self._state_helper.text_processor.clean_text(' '.join(lunar_data.badThing)),
                '时辰经络': self._state_helper.text_processor.clean_text(self._state_helper.text_processor.format_dict(lunar_data.meridians)),
                '六曜': TimeCalculator.calculate_six_luminaries(lunar_data.lunarMonth, lunar_data.lunarDay),
                '日禄': day_fortune
            }

            self._state = state_dict.get(self._type, "")

            if self._type == '九宫飞星' and nine_palace_attrs:
                self._attributes = nine_palace_attrs
            elif self._type == '节气' and next_term and next_term_date:
                self._attributes = {
                    "下一节气": f"{next_term} ({next_term_date})"
                }

            self._available = True
            
        except Exception:
            self._available = False

class SensorUpdateManager:
    def __init__(self, hass: HomeAssistant, sensors: List[AlmanacSensor]):
        self._hass = hass
        self._sensors = sensors
        self._update_lock = asyncio.Lock()
        
    async def update_sensors_batch(self, sensors_to_update: List[AlmanacSensor]):
        async with self._update_lock:
            update_tasks = [sensor._do_update() for sensor in sensors_to_update]
            await asyncio.gather(*update_tasks)
            for sensor in sensors_to_update:
                sensor.async_write_ha_state()
                
    async def setup_update_schedules(self):
        async def midnight_update(now: datetime):
            await self.update_sensors_batch(self._sensors)

        async def quarter_hourly_update(now: datetime):
            shichen_sensors = [s for s in self._sensors if s._type == '时辰']
            await self.update_sensors_batch(shichen_sensors)

        async def two_hourly_update(now: datetime):
            lucky_sensors = [s for s in self._sensors if s._type == '时辰凶吉']
            await self.update_sensors_batch(lucky_sensors)

        async def hourly_update(now: datetime):
            date_sensors = ['日期', '农历', '八字', '今日节日']
            hourly_sensors = [s for s in self._sensors if s._type in date_sensors or 
                            s._type not in ['时辰凶吉', '时辰'] + date_sensors]
            await self.update_sensors_batch(hourly_sensors)

        async_track_time_change(self._hass, midnight_update, hour=0, minute=0, second=0)
        async_track_time_change(self._hass, quarter_hourly_update, minute=[0, 15, 30, 45], second=0)
        async_track_time_change(self._hass, two_hourly_update, hour=[0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22], minute=0, second=0)
        async_track_time_change(self._hass, hourly_update, minute=0, second=0)

        self._hass.bus.async_listen_once(
            'homeassistant_started',
            lambda _: self.update_sensors_batch(self._sensors)
        )

async def setup_almanac_sensors(hass: HomeAssistant, entry_id: str, config_data: dict):
    name = config_data.get("name", "中国老黄历")
    almanac_device = AlmanacDevice(entry_id, name)
    
    sensor_keys = [
        '日期', '农历', '星期', '今日节日', '周数', '八字', '节气',
        '季节', '时辰凶吉', '生肖冲煞', '星座', '星次',
        '彭祖百忌', '十二神', '廿八宿', '今日三合', '今日六合',
        '纳音', '九宫飞星', '吉神方位', '今日胎神', '今日吉神',
        '今日凶煞', '宜忌等第', '宜', '忌', '时辰经络', '时辰',
        '六曜', '日禄'
    ]
    
    sensors = [
        AlmanacSensor(almanac_device, name, key, key in MAIN_SENSORS, hass)
        for key in sensor_keys
    ]

    update_manager = SensorUpdateManager(hass, sensors)
    await update_manager.setup_update_schedules()

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    if "almanac_sensors" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["almanac_sensors"] = {}
    hass.data[DOMAIN]["almanac_sensors"][entry_id] = sensors

    return sensors, sensors


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> bool:
    
    try:
        config_data = dict(entry.data)
        entities, sensors = await setup_almanac_sensors(
            hass, 
            entry.entry_id, 
            config_data
        )
        
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
            
        if "almanac_sensors" not in hass.data[DOMAIN]:
            hass.data[DOMAIN]["almanac_sensors"] = {}
            
        async_add_entities(entities)
        hass.data[DOMAIN]["almanac_sensors"][entry.entry_id] = sensors
        
        return True
        
    except Exception:
        return False

class AlmanacSetup:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry
        self._setup_lock = asyncio.Lock()
        
    async def async_setup(self) -> bool:
        try:
            async with self._setup_lock:
                if self.entry.entry_id in self.hass.data.get(DOMAIN, {}).get("almanac_sensors", {}):
                    return True
                    
                config_data = dict(self.entry.data)
                entities, sensors = await setup_almanac_sensors(
                    self.hass,
                    self.entry.entry_id,
                    config_data
                )
                
                if DOMAIN not in self.hass.data:
                    self.hass.data[DOMAIN] = {}
                    
                if "almanac_sensors" not in self.hass.data[DOMAIN]:
                    self.hass.data[DOMAIN]["almanac_sensors"] = {}
                    
                self.hass.data[DOMAIN]["almanac_sensors"][self.entry.entry_id] = sensors
                
                return True
                
        except Exception:
            return False
            
    async def async_unload(self) -> bool:
        try:
            if self.entry.entry_id in self.hass.data.get(DOMAIN, {}).get("almanac_sensors", {}):
                self.hass.data[DOMAIN]["almanac_sensors"].pop(self.entry.entry_id)
                
            if not self.hass.data[DOMAIN]["almanac_sensors"]:
                self.hass.data.pop(DOMAIN, None)
                
            return True
            
        except Exception:
            return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    global _SETUP_MANAGER
    if _SETUP_MANAGER is not None:
        return await _SETUP_MANAGER.async_unload_entry(entry)
    return False