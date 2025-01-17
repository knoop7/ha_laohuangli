import logging
from datetime import datetime, timedelta
import cnlunar
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers import entity_registry as er
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
    def __init__(self, hass, device, person, sensor_type, entry_id):
        self.hass = hass
        self._device = device
        self._person = person
        self._name = person["name"]
        self._type = sensor_type
        self._entry_id = entry_id
        birthday = datetime.strptime(person["birthday"], DATA_FORMAT)
        self._birthday = birthday.replace(tzinfo=None)
        
        self._notification_service = person.get("notification_service")
        self._notification_message = person.get("notification_message")
        
        self._available = True
        self._attr_has_entity_name = True
        self._attributes = {}
        self._last_notification_date = None
        self._state = None

        if self._type in ["星座", "喜用神", "今日运势", "生存天数", "周岁"]:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            registry = er.async_get(hass)
            existing_entity_id = f"sensor.{self._name}_{self._type}"
            if existing_entry := registry.async_get(existing_entity_id):
                self._attr_entity_registry_enabled_default = not existing_entry.disabled
            else:
                self._attr_entity_registry_enabled_default = False

    @property 
    def name(self):
        return f"{self._name}_{self._type}"

    @property
    def unique_id(self):
        return f"birthday_{self._entry_id}_{self._person['name'].lower()}_{self._type}"

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

        today = dt.now().replace(tzinfo=None)
        birth_date = self._birthday
        years = today.year - birth_date.year
        if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
            years -= 1

        fortune_details = {
            "合": {
                "level": "吉",
                # 3岁以下
                "detail_toddler": f"今日{self._name}运势良好。注意事项：1) 午睡时间建议在11:30-14:00之间，有助于身心发展；2) 今日尤其适合进行亲子活动，可多进行语言互动和感知训练；3) 饮食方面胃口较好，建议适量添加新的辅食品类；4) 今日情绪稳定，是进行日常体检或打疫苗的良好时机。",
                # 3-7岁
                "detail_child": f"今日{self._name}运势良好。上午适合进行认知学习活动，下午可进行适度户外活动。提醒家长：1) 注意防晒防感；2) 社交活动顺畅，是培养同伴交往的好时机；3) 今日精力充沛，可适当增加户外运动时间，但需注意安全。",
                # 7-18岁
                "detail_youth": f"{self._name}今日运势大吉。学习方面思维活跃，适合进行数学等逻辑学科的学习。体能状态良好，课间运动可适当增加强度。人际互动顺畅，团队活动中易获得好评。提醒注意：1) 保持适度运动强度；2) 及时补充水分；3) 午休对今日学习效率很重要。",
                # 18-50岁
                "detail_adult": "今日贵人相助，诸事顺遂。财运：收入稳中有升，适合投资和理财规划。外出：出行顺利，适合商务或社交活动。人际：贵人相助，人际关系顺畅。感情：感情融洽，适合沟通。家庭：家庭和谐，适合共处时光。",
                # 50岁之后
                "detail_elderly": "今日运程平顺，诸事皆宜。健康：气血调和，适宜进补养生。建议进行适度运动，以柔和缓慢为主。财运：财务平稳，依循既定计划行事。外出：短途无碍，长途需慎重。人际：与亲朋好友相处如常，可进行日常交往。家居：居家平安，适合进行日常起居活动。",
                "advice_toddler": "宜：体检、户外、亲子活动\n忌：过度疲劳、剧烈运动",
                "advice_child": "宜：户外活动、认知学习、同伴交往\n忌：过度劳累、受凉着凉",
                "advice_youth": "宜：课业学习、体育活动、团队合作\n忌：过度用眼、熬夜",
                "advice_adult": "把握机会，主动出击",
                "advice_elderly": "宜：居家调养、稳妥处事\n忌：远行冒险、激烈运动"
            },
            "刑": {
                "level": "刑",
                "detail_toddler": f"今日{self._name}运势欠佳。注意事项：1) 容易出现不安情绪，建议调整作息至最舒适节律；2) 饮食方面可能挑食，建议不要强求；3) 户外活动时间宜适当缩短，注意保暖；4) 陌生环境容易产生应激，建议保持熟悉的生活环境；5) 需要特别注意容易碰撞的区域，加强看护。",
                "detail_child": f"今日{self._name}运势较弱。活动时需要特别注意安全，建议减少剧烈运动。提醒家长：1) 情绪可能不稳定，应该耐心倾听和开导；2) 容易出现身体不适，建议清淡饮食；3) 同伴互动中可能遇到小摩擦，需要适时引导。",
                "detail_youth": f"{self._name}今日运势欠佳。学习较易出现注意力分散，课业需要更多专注。体能状态一般，体育活动应以安全为先。人际交往中宜谨慎，避免卷入是非。提醒注意：1) 保持良好作息；2) 课间运动强度适中；3) 遇到问题及时寻求师长帮助。",
                "detail_adult": "易有口舌是非，情绪波动较大。财运：理财需谨慎，避免冲动消费。外出：不宜远行，注意安全。人际：易生口舌，需谨言慎行。感情：易生误会，宜保持耐心。家庭：家庭关系需要维护。",
                "detail_elderly": "今日诸事需谨慎。健康：身体易有不适，需特别关注心脑血管、消化系统。建议及时就医检查。财运：理财需谨慎，防范意外损失。外出：行程多变，不宜远行，建议改期。人际：避免参与琐事纷争，谨防外人相扰。家居：居所需注意安全，防范跌倒或意外事故。",
                "advice_toddler": "宜：调整作息、清淡饮食、保持安静\n忌：环境变动、强迫进食",
                "advice_child": "宜：轻度活动、亲子陪伴、早睡\n忌：剧烈运动、情绪激动",
                "advice_youth": "宜：独立学习、充足休息\n忌：剧烈运动、争执",
                "advice_adult": "谨言慎行，避免冲突",
                "advice_elderly": "宜：居家调养、稳妥处事\n忌：远行冒险、激烈运动"
            },
            "冲": {
                "level": "冲",
                "detail_toddler": f"今日{self._name}运势冲克。注意事项：1) 睡眠质量可能不佳，建议采用舒缓音乐或轻柔拍背助眠；2) 易出现过敏反应，新食物引入需谨慎；3) 乘车易出现不适，建议避免不必要的远途移动；4) 大型公共场所可能加重情绪不安，建议活动区域以熟悉环境为主。",
                "detail_child": f"今日{self._name}运势不稳。活动时需要格外注意安全，建议以室内活动为主。提醒家长：1) 容易出现食欲不振，建议增加营养摄入；2) 睡眠可能不安稳，建议保持安静的睡眠环境；3) 情绪起伏较大，需要更多关注和开导。",
                "detail_youth": f"{self._name}今日运势波动。学习方面需要更多耐心，建议将困难课题留到状态好时再战。体能起伏较大，运动量宜适中。群体活动参与度可能下降，建议以个人学习为主。注意：1) 避免过度劳累；2) 多休息多饮水；3) 与人相处以和为贵。",
                "detail_adult": "运势波动较大，诸事需谨慎。财运：不宜大额支出，避免冲动消费。外出：行程易变，需待机而动。人际：人际关系需要维护，避免产生分歧。感情：情绪起伏大，注意沟通方式。家庭：家庭关系略显紧张，宜互相体谅。",
                "detail_elderly": "今日运势波动较大。健康：身体易有不适，需特别关注心脑血管、消化系统。建议及时就医检查。财运：理财需谨慎，防范意外损失。外出：行程多变，不宜远行，建议改期。人际：避免参与琐事纷争，谨防外人相扰。家居：居所需加强防范，谨防意外事故，保持警惕。",
                "advice_toddler": "宜：规律作息、清淡饮食\n忌：环境剧变、长途奔波",
                "advice_child": "宜：室内活动、早睡、规律饮食\n忌：剧烈运动、情绪激动",
                "advice_youth": "宜：独立学习、充足休息\n忌：过度劳累、人际冲突",
                "advice_adult": "稳妥行事，避免冒险",
                "advice_elderly": "宜：居家休养、保持平静\n忌：奔波劳累、激动争执"
            },
            "平": {
                "level": "平",
                "detail_toddler": f"今日{self._name}运势平稳。注意事项：1) 适合保持日常作息，按时吃睡；2) 可以进行常规的亲子活动，以温和的强度为宜；3) 饮食建议按既定安排进行，不宜贸然更改；4) 适合进行日常的观察和认知训练；5) 体温、情绪等各项指标平稳，适合总结生长发育情况。",
                "detail_child": f"今日{self._name}运势平稳。各项活动均可正常开展，适合保持日常生活节奏。提醒家长：1) 适合进行常规教育活动；2) 户外活动适可而止；3) 社交活动中以温和态度为主。",
                "detail_youth": f"{self._name}今日运势平稳。课业学习循序渐进，适合复习和巩固知识。体能表现中规中矩，体育活动量以平时标准为宜。社交活动宜随大流，不必特立独行。注意：1) 保持正常作息；2) 适度运动；3) 按时完成功课。",
                "detail_adult": "运势平稳，无突出吉凶。财运：财务平稳，按既定计划行事。外出：一般平顺，按需出行。人际：社交如常，保持礼节。感情：感情稳定，适合默契相处。家庭：家庭和睦，各安其位。",
                "detail_elderly": "今日运势平稳。健康：身体状况平稳，适合进行日常保健。建议依照往常作息，保持规律运动。财运：财务平稳，依循既定计划行事。外出：短途无碍，长途需慎重。人际：与亲朋好友相处如常，可进行日常交往。家居：居家平安，适合进行日常起居活动。",
                "advice_toddler": "宜：常规作息、日常活动\n忌：过度刺激、突变环境",
                "advice_child": "宜：常规活动、正常作息\n忌：过度劳累",
                "advice_youth": "宜：复习功课、常规运动\n忌：标新立异",
                "advice_adult": "保持平常心，按部就班",
                "advice_elderly": "宜：规律作息、平和处世\n忌：贪图安逸、过度担忧"
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
        
        if years < 3:
            detail = fortune["detail_toddler"]
            advice = fortune["advice_toddler"]
        elif years < 7:
            detail = fortune["detail_child"]
            advice = fortune["advice_child"]
        elif years < 18:
            detail = fortune["detail_youth"]
            advice = fortune["advice_youth"]
        elif years >= 50:  
            detail = fortune["detail_elderly"]
            advice = fortune["advice_elderly"]
        else:
            detail = fortune["detail_adult"]
            advice = fortune["advice_adult"]
            
        return {
            "state": relation,
            "attributes": {
                "运势等级": fortune["level"],
                "运势详解": detail,
                "行动建议": advice,
                "日元": birth_lunar.day8Char,
                "今日天干地支": today_lunar.day8Char
            }
        }

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
                    birth_lunar_month, birth_lunar_day, birth_is_leap = birth_lunar.lunarMonth, birth_lunar.lunarDay, birth_lunar.isLunarLeapMonth
                    today_lunar = cnlunar.Lunar(today, godType='8char')
                    today_year = today.year
                    this_year_birthday = next_year_birthday = None
                    found_birthday = False

                    for year in [today_year - 1, today_year, today_year + 1]:
                        if found_birthday:
                            break
                        for month in range(1, 13):
                            if found_birthday:
                                break
                            next_month = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
                            days_in_month = (next_month - datetime(year, month, 1)).days
                            for day in range(1, days_in_month + 1):
                                test_date = datetime(year, month, day)
                                try:
                                    lunar_test = cnlunar.Lunar(test_date, godType='8char')
                                    if (lunar_test.lunarMonth == birth_lunar_month and 
                                        lunar_test.lunarDay == birth_lunar_day and 
                                        lunar_test.isLunarLeapMonth == birth_is_leap):
                                        test_date_only = test_date.date()
                                        today_date = today.date()
                                        
                                        if test_date_only < today_date:
                                            this_year_birthday = test_date if year == today_year else None
                                        else:
                                            if year == today_year:
                                                this_year_birthday = test_date
                                                found_birthday = True
                                            elif year == today_year + 1:
                                                next_year_birthday = test_date
                                                found_birthday = True
                                        break
                                except:
                                    continue

                    next_birthday = this_year_birthday if this_year_birthday and this_year_birthday.date() >= today.date() else next_year_birthday
                    
                    if next_birthday:
                        days_until = (next_birthday.date() - today.date()).days
                        next_lunar = cnlunar.Lunar(next_birthday, godType='8char')
                        self._state = "今天是生日" if days_until == 0 else f"农历生日还有{days_until}天"
                        
                        if days_until == 0 and self._notification_service and (self._last_notification_date is None or self._last_notification_date != today.date()):
                            await self.hass.services.async_call("notify", self._notification_service.replace("notify.", ""), 
                                                            {"title": "中国老黄历 · Home Assistant", 
                                                            "message": self._notification_message})
                            self._last_notification_date = today.date()
                        
                        self._attributes.update({
                            "下个生日": f"阳历：{next_birthday.strftime('%Y-%m-%d')}"
                        })
                    else:
                        self._state = "无法计算下一个生日日期"

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

            elif self._type == "喜用神":
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
                    "星座", "喜用神", "今日运势", "生存天数", "周岁"
                ]:
                    sensor = BirthdaySensor(hass, birthday_device, person, sensor_type, entry_id)
                    entities.append(sensor)
    
    return entities
