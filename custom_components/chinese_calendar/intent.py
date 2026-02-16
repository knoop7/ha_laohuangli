import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_intents(hass: HomeAssistant):
    if hass.data.get(DOMAIN, {}).get("_intents_registered"): return
    intent.async_register(hass, HolidaysIntent())
    intent.async_register(hass, AlmanacIntent())
    intent.async_register(hass, EventsIntent())
    hass.data.setdefault(DOMAIN, {})["_intents_registered"] = True
    _LOGGER.info("Chinese Calendar intents registered")

class HolidaysIntent(intent.IntentHandler):
    intent_type = "Holidays"
    description = "查询节假日信息，包括春节、元旦、清明、端午、中秋、国庆、劳动节、过年、放假、调休、小年、除夕、元宵、七夕、重阳、腊八、寒衣节、下元节等"
    slot_schema = {vol.Optional("keyword", description="节日关键词如春节、过年、放假"): str}
    async def async_handle(self, intent_obj: intent.Intent):
        hass = intent_obj.hass
        slots = self.async_validate_slots(intent_obj.slots)
        keyword = slots.get("keyword", {}).get("value", "")
        synonyms = {"过年": "春节", "新年": "春节", "五一": "劳动节", "十一": "国庆", "鬼节": "中元", "月饼节": "中秋", "粽子节": "端午"}
        search_keywords = [keyword, synonyms.get(keyword, "")] if keyword else []
        from datetime import datetime
        current_year = datetime.now().year
        almanac = await hass.services.async_call(DOMAIN, "get_almanac", {}, blocking=True, return_response=True)
        data = await hass.services.async_call(DOMAIN, "get_holidays", {}, blocking=True, return_response=True)
        parts = []
        today_date = (almanac or {}).get("日期", "")
        today_lunar = (almanac or {}).get("农历", "")
        data_year = (data or {}).get("data_year", current_year)
        parts.append(f"【重要】当前是{current_year}年，今天是{today_date}，农历{today_lunar}。以下节假日数据全部是{data_year}年的，请勿混淆年份")
        holidays = (data or {}).get("holidays", {})
        customdays = (data or {}).get("customdays", {})
        workdays = (data or {}).get("workdays", {})
        if search_keywords:
            for d, n in holidays.items():
                if any(kw and kw in n for kw in search_keywords): parts.append(f"{d}是{n}")
            for d, n in customdays.items():
                if any(kw and kw in n for kw in search_keywords): parts.append(f"{d}是{n}")
            for d, n in workdays.items():
                if any(kw and kw in n for kw in search_keywords): parts.append(f"{d}是{n}")
        else:
            for d, n in holidays.items(): parts.append(f"{d}是{n}")
            for d, n in workdays.items(): parts.append(f"{d}是{n}")
        response = intent_obj.create_response()
        response.response_type = intent.IntentResponseType.ACTION_DONE
        response.async_set_speech(",".join(parts))
        return response

class AlmanacIntent(intent.IntentHandler):
    intent_type = "Almanac"
    description = "查询传统历法信息，包括农历、八字、节气、宜忌、吉凶、星座、生肖、彭祖百忌、吉神方位、胎神、纳音、九宫飞星、十二神、廿八宿、六曜、日禄、三十六禽、六十四卦、盲派等。支持查询任意日期，如2025-01-29"
    slot_schema = {vol.Optional("date", description="查询日期YYYY-MM-DD格式"): str}
    async def async_handle(self, intent_obj: intent.Intent):
        hass = intent_obj.hass
        slots = self.async_validate_slots(intent_obj.slots)
        date_str = slots.get("date", {}).get("value")
        query_date = None
        if date_str:
            from datetime import datetime
            try:
                query_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                await hass.services.async_call(DOMAIN, "date_control", {"action": "select_date", "date": query_date}, blocking=True)
                import asyncio
                await asyncio.sleep(0.5)
            except: pass
        data = await hass.services.async_call(DOMAIN, "get_almanac", {}, blocking=True, return_response=True)
        if date_str:
            await hass.services.async_call(DOMAIN, "date_control", {"action": "today"}, blocking=True)
        result = f"{query_date.strftime('%Y年%m月%d日')}" if query_date else "今天"
        result += f"是农历{data.get('农历', '')}，{data.get('星期', '')}。"
        if data.get('今日节日') and data.get('今日节日') != '暂无节日': result += f"这天是{data.get('今日节日')}。"
        if data.get('节气'): result += f"节气是{data.get('节气')}。"
        result += "【严格规则】只回复日期、农历、星期、节日、节气。禁止说宜忌、八字、星座等内容。用小学三年级能听懂的简单话回复。"
        response = intent_obj.create_response()
        response.response_type = intent.IntentResponseType.ACTION_DONE
        response.async_set_speech(result)
        return response

class EventsIntent(intent.IntentHandler):
    intent_type = "Events"
    description = "查询生日提醒和事件提醒，包括谁的生日、纪念日、重要日子等"
    slot_schema = {}
    async def async_handle(self, intent_obj: intent.Intent):
        hass = intent_obj.hass
        data = await hass.services.async_call(DOMAIN, "get_events", {}, blocking=True, return_response=True)
        parts = []
        for b in (data or {}).get("birthdays", []): parts.append(f"{b['name']}生日是{b['date']}({'农历' if b['lunar'] else '公历'})")
        for e in (data or {}).get("events", []): parts.append(f"{e['name']}在{e['date']}({'农历' if e['lunar'] else '公历'})")
        response = intent_obj.create_response()
        response.response_type = intent.IntentResponseType.ACTION_DONE
        response.async_set_speech(",".join(parts) if parts else "暂无配置生日或事件提醒")
        return response
