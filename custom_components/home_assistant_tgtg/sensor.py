import logging
from datetime import datetime, timedelta
import voluptuous as vol
import asyncio
import cnlunar
import re
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.util import dt
from homeassistant.helpers.event import async_track_time_interval


from .const import (
    DOMAIN,
    MIN_TIME_BETWEEN_UPDATES,
    MIN_TIME_BETWEEN_TWOHOUR_UPDATES,
    MAIN_SENSORS,
    DATA_FORMAT,
    EVENT_DATE_FORMAT,
    CONF_BIRTHDAY_ENABLED,
    CONF_EVENT_ENABLED,
)

_LOGGER = logging.getLogger(__name__)

class DeviceBase:
    def __init__(self, entry_id: str):
        self._entry_id = entry_id

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers=self._get_identifiers(),
            name=self._get_name(),
            model=self._get_model(),
            manufacturer="道教",
        )

    def _get_identifiers(self):
        return {(DOMAIN, self._entry_id)}

    def _get_name(self):
        raise NotImplementedError

    def _get_model(self):
        raise NotImplementedError

class AlmanacDevice(DeviceBase):
    def __init__(self, entry_id: str, name: str):
        super().__init__(entry_id)
        self._name = name

    def _get_name(self):
        return self._name

    def _get_model(self):
        return "Chinese Almanac"

class GuanyinSignDevice(DeviceBase):
    def _get_identifiers(self):
        return {(DOMAIN, f"{self._entry_id}_guanyin")}

    def _get_name(self):
        return "观音签"

    def _get_model(self):
        return "Guanyin Sign"

class BirthdayDevice(DeviceBase):
    def _get_identifiers(self):
        return {(DOMAIN, f"{self._entry_id}_birthday")}

    def _get_name(self):
        return "生日管理"

    def _get_model(self):
        return "Birthday Tracker"


class EventDevice(DeviceBase):
    def _get_identifiers(self):
        return {(DOMAIN, f"{self._entry_id}_event")}

    def _get_name(self):
        return "事件管理"

    def _get_model(self):
        return "Event Tracker"

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


###################  感谢 @LOVE2CMOL 提供时辰刻度, 修复整为初
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
##################  感谢 @LOVE2CMOL 提供时辰刻度, 修复整为初
    async def _update_general(self, now):
        try:
            a = cnlunar.Lunar(now, godType='8char')
            dic = {
                '日期': a.date,
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

class BirthdaySensor(SensorEntity):
    def __init__(self, device, person, sensor_type):
        self._device = device
        self._person = person
        self._name = person["name"]
        self._type = sensor_type
        self._birthday = datetime.strptime(person["birthday"], DATA_FORMAT)
        self._state = None
        self._available = True
        self._attr_has_entity_name = True

    @property
    def name(self):
        return f"{self._name}_{self._type}"

    @property
    def unique_id(self):
        return f"birthday_{self._person['name']}_{self._type}"

    @property
    def device_info(self):
        return self._device.device_info

    @property
    def state(self):
        return self._state

    @property
    def available(self):
        return self._available

    @property
    def icon(self):
        return 'mdi:calendar-star'

    async def async_update(self):
        try:
            if self._type == "阳历生日":
                self._state = self._birthday.strftime("%y年%m月%d日")
            elif self._type == "农历生日":
                lunar = cnlunar.Lunar(self._birthday)
                self._state = f"{lunar.lunarMonthCn}{lunar.lunarDayCn}"
            elif self._type == "八字":
                lunar = cnlunar.Lunar(self._birthday, godType='8char')
                self._state = f"{lunar.year8Char}年{lunar.month8Char}月{lunar.day8Char}日{lunar.twohour8Char}时"
            elif self._type == "生日提醒":
                today = dt.now().replace(tzinfo=None)
                birthday_this_year = self._birthday.replace(year=today.year)
                
                if birthday_this_year.date() < today.date():
                    birthday_this_year = birthday_this_year.replace(year=today.year + 1)
                    
                days_until = (birthday_this_year.date() - today.date()).days
                
                if days_until == 0:
                    self._state = "今天是生日"
                else:
                    self._state = f"还有{days_until}天"
            
            self._available = True
            
        except Exception as e:
            _LOGGER.error("更新生日传感器时出错: %s", e)
            self._available = False

class EventSensor(SensorEntity):
    def __init__(self, device, event_name, event_date, event_desc):
        self._device = device
        self._name = event_name
        self._event_date = datetime.strptime(event_date, EVENT_DATE_FORMAT)
        self._event_desc = event_desc
        self._state = None
        self._available = True
        self._attr_has_entity_name = True

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"event_{self._name}"

    @property
    def device_info(self):
        return self._device.device_info

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return {
            "描述": self._event_desc,
            "日期": self._event_date.strftime(EVENT_DATE_FORMAT)
        }

    @property
    def available(self):
        return self._available

    @property
    def icon(self):
        return 'mdi:calendar-clock'

    async def async_update(self):
        try:
            today = dt.now().replace(tzinfo=None)
            days_until = (self._event_date.date() - today.date()).days
            
            if days_until < 0:
                self._state = "已过期"
            elif days_until == 0:
                self._state = "今天"
            else:
                self._state = f"还有{days_until}天"
            
            self._available = True
        except Exception as e:
            _LOGGER.error("更新事件传感器时出错: %s", e)
            self._available = False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    data = entry.data
    entities = []
    
    name = data.get(CONF_NAME, "中国老黄历")
    almanac_device = AlmanacDevice(entry.entry_id, name)

    
    almanac_sensors = [
        AlmanacSensor(almanac_device, name, key, key in MAIN_SENSORS) 
        for key in [
            '日期', '农历', '星期', '今日节日', '八字', '今日节气',
            '下一节气', '季节', '时辰凶吉', '生肖冲煞', '星座', '星次',
            '彭祖百忌', '十二神', '廿八宿', '今日三合', '今日六合',
            '纳音', '九宫飞星', '吉神方位', '今日胎神', '今日吉神',
            '今日凶煞', '宜忌等第', '宜', '忌', '时辰经络','时辰'
        ]
    ]
    entities.extend(almanac_sensors)

    if data.get(CONF_BIRTHDAY_ENABLED, False):
        birthday_device = BirthdayDevice(entry.entry_id)
        person_count = sum(1 for key in data if key.startswith("person") and key.endswith("_name"))
        
        for i in range(1, person_count + 1):
            name = data.get(f"person{i}_name")
            birthday = data.get(f"person{i}_birthday")
            
            if name and birthday:
                person = {"name": name, "birthday": birthday}
                for sensor_type in ["阳历生日", "农历生日", "八字", "生日提醒"]:
                    entities.append(BirthdaySensor(birthday_device, person, sensor_type))
                    
    if data.get(CONF_EVENT_ENABLED, False):
        event_device = EventDevice(entry.entry_id)
        event_count = sum(1 for key in data if key.startswith("event") and key.endswith("_name"))
        
        for i in range(1, event_count + 1):
            name = data.get(f"event{i}_name")
            date = data.get(f"event{i}_date")
            desc = data.get(f"event{i}_desc", "")
            
            if name and date:
                entities.append(EventSensor(event_device, name, date, desc))
    
    async_add_entities(entities, True)

    async def update_twohour_lucky(now):
        for sensor in almanac_sensors:
            if sensor._type == '时辰凶吉':
                await sensor.async_update()

    async def update_double_hour(now):
        for sensor in almanac_sensors:
            if sensor._type == '时辰':
                await sensor.async_update()


    async_track_time_interval(
        hass,  
        update_twohour_lucky,
        MIN_TIME_BETWEEN_TWOHOUR_UPDATES
    )

    async_track_time_interval(
        hass,
        update_double_hour,
        timedelta(minutes=1)
    )

def validate_date(date_str: str, is_event: bool = False) -> str:
    try:
        if is_event:
            datetime.strptime(date_str, EVENT_DATE_FORMAT)
        else:
            datetime.strptime(date_str, DATA_FORMAT)
        return date_str
    except ValueError:
        raise vol.Invalid("invalid_date_format")



    async def async_step_event(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors = {}
        event_count = sum(1 for key in self.data if key.startswith("event") and key.endswith("_name"))

        if event_count >= MAX_EVENTS:
            return await self.async_step_name()

        if user_input is not None:
            try:
                validate_date(user_input["date"], is_event=True)
                event_count += 1
                self.data[f"event{event_count}_name"] = user_input["name"]
                self.data[f"event{event_count}_date"] = user_input["date"]
                self.data[f"event{event_count}_desc"] = user_input.get("description", "")
                
                if not user_input.get("add_another") or event_count >= MAX_EVENTS:
                    return await self.async_step_name()
                    
                return await self.async_step_event()
                
            except vol.Invalid:
                errors["date"] = "invalid_event_date_format"

        schema = {
            vol.Required("name"): str,
            vol.Required("date"): str,
            vol.Optional("description", default=""): str,
        }
        
        if event_count < MAX_EVENTS - 1:
            schema[vol.Optional("add_another", default=False)] = bool

        return self.async_show_form(
            step_id="event",
            data_schema=vol.Schema(schema),
            errors=errors,
        )

    async def async_step_birthday(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors = {}
        
        if user_input is not None:
            try:
                validate_date(user_input["birthday"])
                self.current_person += 1
                self.data[f"person{self.current_person}_name"] = user_input["name"]
                self.data[f"person{self.current_person}_birthday"] = user_input["birthday"]
                
                if not user_input.get("add_another") or self.current_person >= MAX_BIRTHDAYS:
                    if self.data.get(CONF_EVENT_ENABLED):
                        return await self.async_step_event()
                    return await self.async_step_name()
                    
                return await self.async_step_birthday()
                
            except vol.Invalid:
                errors["birthday"] = "invalid_date_format"

        schema = {
            vol.Required("name"): str,
            vol.Required("birthday"): str,
        }
        
        if self.current_person < MAX_BIRTHDAYS - 1:
            schema[vol.Optional("add_another", default=False)] = bool

        return self.async_show_form(
            step_id="birthday",
            data_schema=vol.Schema(schema),
            errors=errors,
        )

    async def async_step_name(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        if user_input is not None:
            self.data[CONF_NAME] = user_input[CONF_NAME]
            return self.async_create_entry(title=user_input[CONF_NAME], data=self.data)

        return self.async_show_form(
            step_id="name",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default="中国老黄历"): str,
            })
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)