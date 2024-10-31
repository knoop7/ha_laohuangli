import logging
from datetime import datetime, timedelta
import cnlunar
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.util import dt

from .const import (
    DOMAIN,
    DATA_FORMAT,
)

_LOGGER = logging.getLogger(__name__)

class BirthdayDevice:
    def __init__(self, entry_id: str):
        self._entry_id = entry_id

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry_id}_birthday")},
            name="生日管理",
            model="Birthday Tracker",
            manufacturer="道教",
        )

class BirthdaySensor(SensorEntity):
    def __init__(self, hass, device, person, sensor_type):
            self.hass = hass
            self._device = device
            self._person = person
            self._name = person["name"]
            self._type = sensor_type
            birthday = datetime.strptime(person["birthday"], DATA_FORMAT)
            self._birthday = birthday.replace(tzinfo=None)
            
            self._notification_service = person.get("notification_service")
            self._notification_message = person.get("notification_message")
            
            self._available = True
            self._attr_has_entity_name = True
            self._attributes = {}
            self._last_notification_date = None
            self._state = None

            if self._type in ["星座", "幸运色", "今日运势", "生存天数", "周岁"]:
                self._attr_entity_category = EntityCategory.DIAGNOSTIC
                self._attr_entity_registry_enabled_default = False

        

    def _calculate_lucky_color(self, birth_date):
        date_str = birth_date.strftime("%Y%m%d%H")
        num_sum = sum(int(digit) for digit in date_str)
        while num_sum > 9:
            num_sum = sum(int(digit) for digit in str(num_sum))
        color_map = {
            1: "红色", 2: "红色",
            3: "绿色", 4: "绿色",
            5: "黄色", 6: "黄色",
            7: "蓝色", 8: "蓝色",
            9: "白色", 0: "白色"
        }
        return color_map[num_sum]

    def _get_zodiac_sign(self, birth_date):
        month = birth_date.month
        day = birth_date.day
        zodiac_dates = [
            ((1, 20), (2, 18), "水瓶座"), ((2, 19), (3, 20), "双鱼座"),
            ((3, 21), (4, 19), "白羊座"), ((4, 20), (5, 20), "金牛座"),
            ((5, 21), (6, 20), "双子座"), ((6, 21), (7, 22), "巨蟹座"),
            ((7, 23), (8, 22), "狮子座"), ((8, 23), (9, 22), "处女座"),
            ((9, 23), (10, 22), "天秤座"), ((10, 23), (11, 21), "天蝎座"),
            ((11, 22), (12, 21), "射手座"), ((12, 22), (1, 19), "摩羯座")
        ]
        
        for (start_month, start_day), (end_month, end_day), sign in zodiac_dates:
            if (month == start_month and day >= start_day) or (month == end_month and day <= end_day):
                return sign
        return "摩羯座"

    def _get_element_attributes(self, lunar_info):
        elements = {
            "甲": "木", "乙": "木",
            "丙": "火", "丁": "火",
            "戊": "土", "己": "土",
            "庚": "金", "辛": "金",
            "壬": "水", "癸": "水"
        }
        element = elements[lunar_info.day8Char[0]]
        attributes = {
            "木": "生长、向上、清雅",
            "火": "温暖、活力、激情",
            "土": "稳重、包容、务实",
            "金": "坚毅、果断、正直",
            "水": "智慧、灵活、适应"
        }
        return f"{element}({attributes[element]})"

    def _analyze_daily_fortune(self, birth_lunar, today_lunar):
        gan_relations = {
            ("甲", "己"): "合", ("乙", "庚"): "合", ("丙", "辛"): "合",
            ("丁", "壬"): "合", ("戊", "癸"): "合",
            ("甲", "庚"): "刑", ("乙", "辛"): "刑", ("丙", "壬"): "刑",
            ("丁", "癸"): "刑", ("戊", "己"): "刑",
            ("甲", "辛"): "冲", ("乙", "壬"): "冲", ("丙", "癸"): "冲",
            ("丁", "庚"): "冲", ("戊", "辛"): "冲"
        }
        
        zhi_relations = {
            ("子", "午"): "冲", ("丑", "未"): "冲", ("寅", "申"): "冲",
            ("卯", "酉"): "冲", ("辰", "戌"): "冲", ("巳", "亥"): "冲",
            ("寅", "巳", "申", "亥"): "刑", ("子", "卯", "未"): "刑",
            ("丑", "戌", "未"): "刑", ("辰", "酉", "午"): "刑",
            ("亥", "子"): "合", ("寅", "亥"): "合", ("卯", "戌"): "合",
            ("辰", "酉"): "合", ("巳", "申"): "合", ("午", "未"): "合"
        }

        birth_gan = birth_lunar.day8Char[0]
        birth_zhi = birth_lunar.day8Char[1]
        today_gan = today_lunar.day8Char[0]
        today_zhi = today_lunar.day8Char[1]

        relations = []
        fortune_details = {
            "合": {
                "level": "吉",
                "detail": "今日贵人相助，诸事顺遂，适合社交和谈判。财运：收入稳中有升，适合投资和理财规划。外出：出行顺利，适合商务或社交活动。人际：贵人相助，人际关系顺畅，适合拓展人脉。感情：感情融洽，适合与伴侣沟通感情。家庭：家庭和谐，适合与家人共度时光",
                "advice": "把握机会，主动出击"
            },
            "刑": {
                "level": "凶",
                "detail": "易有口舌是非，情绪波动较大。财运：财务需谨慎，避免冲动消费。外出：不宜远行，出行需注意安全。人际：易有口舌是非，需注意言辞。感情：易有误解，需冷静沟通。家庭：家庭关系紧张，需避免冲突",
                "advice": "谨言慎行，避免冲突"
            },
            "冲": {
                "level": "凶",
                "detail": "运势起伏较大，易有意外变动。财运：不宜进行高风险投资，易有财务波动。外出：出行计划易有变动，需小心应对。人际：人际关系不稳，需避免冲突。感情：感情易有波折，需多关心伴侣。家庭：家庭关系需多维护，避免摩擦",
                "advice": "稳妥行事，避免冒险"
            },
            "平": {
                "level": "平",
                "detail": "日常平稳，无特殊吉凶。财运：财运平稳，适合保持现有的理财策略。外出：日常出行平顺，无特殊情况。人际：人际关系无明显波动。感情：感情平稳，适合共处时光。家庭：家庭氛围和谐，无明显波动",
                "advice": "保持平常心，按部就班处事"
            }
        }

        for (g1, g2), rel in gan_relations.items():
            if (birth_gan == g1 and today_gan == g2) or (birth_gan == g2 and today_gan == g1):
                relations.append(f"天干{rel}")

        for zhi_group, rel in zhi_relations.items():
            if birth_zhi in zhi_group and today_zhi in zhi_group:
                relations.append(f"地支{rel}")

        relation = relations[0] if relations else "平"
        fortune = fortune_details[relation.replace("天干", "").replace("地支", "")]

        return {
            "state": relation,
            "attributes": {
                "运势等级": fortune["level"],
                "运势详解": fortune["detail"],
                "行动建议": fortune["advice"],
                "日元": birth_lunar.day8Char,
                "今日天干地支": today_lunar.day8Char
            }
        }

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
    def extra_state_attributes(self):
        return self._attributes

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

            elif self._type == "生日提醒_农":
                today = dt.now().replace(tzinfo=None)
                
                birth_lunar = cnlunar.Lunar(self._birthday, godType='8char')
                birth_lunar_month = birth_lunar.lunarMonth
                birth_lunar_day = birth_lunar.lunarDay
                birth_is_leap = birth_lunar.isLunarLeapMonth
                
                today_lunar = cnlunar.Lunar(today, godType='8char')
                today_year = today_lunar.lunarYear
                this_year_birthday = None
                next_year_birthday = None
                
                for year in [today_year, today_year + 1]:
                    for month in range(1, 13):  
                        test_date = datetime(year, month, 1) 
                        while test_date.year == year:
                            lunar_test = cnlunar.Lunar(test_date, godType='8char')
                            if (lunar_test.lunarMonth == birth_lunar_month and 
                                lunar_test.lunarDay == birth_lunar_day and 
                                lunar_test.isLunarLeapMonth == birth_is_leap):
                                if year == today_year:
                                    this_year_birthday = test_date
                                else:
                                    next_year_birthday = test_date
                                break
                            test_date = test_date + timedelta(days=1)
                        if (year == today_year and this_year_birthday) or (year == today_year + 1 and next_year_birthday):
                            break
                
                if this_year_birthday and this_year_birthday.date() >= today.date():
                    next_birthday = this_year_birthday
                else:
                    next_birthday = next_year_birthday
                
                if next_birthday:
                    days_until = (next_birthday.date() - today.date()).days
                    
                    if days_until == 0:
                        self._state = "今天是生日"
                        if (self._notification_service and 
                            (self._last_notification_date is None or 
                            self._last_notification_date != today.date())):
                            await self.hass.services.async_call(
                                "notify",
                                self._notification_service.replace("notify.", ""),
                                {
                                    "title": "中国老黄历 · Home Assistant",
                                    "message": self._notification_message
                                }
                            )
                            self._last_notification_date = today.date()
                    else:
                        self._state = f"农历生日还有{days_until}天"
                    
                    self._attributes.update({
                        "下个生日": next_birthday.strftime("%Y-%m-%d")
                    })

            elif self._type == "生日提醒_阳":
                today = dt.now().replace(tzinfo=None)
                birthday_this_year = self._birthday.replace(year=today.year)
                
                if birthday_this_year.date() < today.date():
                    birthday_this_year = birthday_this_year.replace(year=today.year + 1)
                
                days_until = (birthday_this_year.date() - today.date()).days
                
                if days_until == 0:
                    self._state = "今天是生日"
                    if (self._notification_service and
                        (self._last_notification_date is None or
                        self._last_notification_date != today.date())):
                        await self.hass.services.async_call(
                            "notify",
                            self._notification_service.replace("notify.", ""),
                            {
                                "title": "中国老黄历 · Home Assistant",
                                "message": self._notification_message
                            }
                        )
                        self._last_notification_date = today.date()
                else:
                    self._state = f"阳历生日还有{days_until}天"

            elif self._type == "星座":
                self._state = self._get_zodiac_sign(self._birthday)

            elif self._type == "幸运色":
                lunar = cnlunar.Lunar(self._birthday, godType='8char')
                element_attr = self._get_element_attributes(lunar)
                lucky_color = self._calculate_lucky_color(self._birthday)
                self._state = f"{lucky_color}，五行：{element_attr}"

            elif self._type == "今日运势":
                current_time = dt.now().replace(tzinfo=None)  
                birth_lunar = cnlunar.Lunar(self._birthday.replace(tzinfo=None), godType='8char')
                today_lunar = cnlunar.Lunar(current_time, godType='8char')
                fortune_result = self._analyze_daily_fortune(birth_lunar, today_lunar)
                self._state = fortune_result["state"]
                self._attributes = fortune_result["attributes"]

            elif self._type == "生存天数":
                try:
                    today = dt.now().replace(tzinfo=None)
                    birth_date = self._birthday.date()  
                    current_date = today.date()
                    days_lived = (current_date - birth_date).days
                    self._state = f"您在地球存活了 {days_lived} 天"
                except Exception:
                    pass
                
            elif self._type == "周岁":
                today = dt.now().replace(tzinfo=None)
                years = today.year - self._birthday.year
                if today.month < self._birthday.month or (today.month == self._birthday.month and today.day < self._birthday.day):
                    years -= 1
                self._state = f"{years}岁"
            
            self._available = True
        except Exception as e:
            _LOGGER.error("更新生日传感器时出错: %s", e)
            self._available = False

async def setup_birthday_sensors(hass: HomeAssistant, entry_id: str, config_data: dict):
    entities = []
    if config_data.get("birthday_enabled", False):
        birthday_device = BirthdayDevice(entry_id)
        person_count = sum(1 for key in config_data if key.startswith("person") and key.endswith("_name"))
        
        for i in range(1, person_count + 1):
            name = config_data.get(f"person{i}_name")
            birthday = config_data.get(f"person{i}_birthday")
            
            if name and birthday:
                person = {
                    "name": name,
                    "birthday": birthday,
                    "notification_service": config_data.get(f"person{i}_notification_service"),
                    "notification_message": config_data.get(f"person{i}_notification_message")
                }
                
                for sensor_type in [
                    "阳历生日", "农历生日", "八字", "生日提醒_农", "生日提醒_阳",
                    "星座", "幸运色", "今日运势", "生存天数", "周岁"
                ]:
                    sensor = BirthdaySensor(hass, birthday_device, person, sensor_type)
                    entities.append(sensor)
    
    return entities