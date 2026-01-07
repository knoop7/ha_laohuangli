DOMAIN = "chinese_calendar"
PLATFORMS = ["sensor"] 
CONF_BIRTHDAY_ENABLED = "birthday_enabled"
CONF_EVENT_ENABLED = "event_enabled"

CONF_BIRTHDAY_PERSONS = "birthday_persons"

CONF_NOTIFICATION_ENABLED = "notification_enabled"
CONF_NOTIFICATION_SERVICE = "notification_service"
CONF_NOTIFICATION_MESSAGE = "notification_message"

CONF_AI_ENABLED = "ai_enabled"
CONF_AI_API_URL = "ai_api_url"
CONF_AI_API_KEY = "ai_api_key"
CONF_AI_MODEL = "ai_model"

DEFAULT_AI_API_URL = "https://api.chatanywhere.tech"
AI_MODELS = [
    {"value": "deepseek-r1", "label": "deepseek-r1"},
    {"value": "deepseek-v3.1", "label": "deepseek-v3.1"},
    {"value": "gpt-4o-mini", "label": "gpt-4o-mini"},
    {"value": "gpt-3.5-turbo", "label": "gpt-3.5-turbo"},
    {"value": "gpt-4.1-mini", "label": "gpt-4.1-mini"},
    {"value": "gpt-4.1-nano", "label": "gpt-4.1-nano"},
    {"value": "gpt-5-mini", "label": "gpt-5-mini"},
    {"value": "gpt-5-nano", "label": "gpt-5-nano"},
    {"value": "gpt-4o", "label": "gpt-4o"},
    {"value": "gpt-5", "label": "gpt-5"},
    {"value": "gpt-4.1", "label": "gpt-4.1"}
]


SERVICE_DATE_CONTROL = "date_control"
ATTR_ACTION = "action"
ATTR_DATE = "date"

ACTIONS = ["next_day", "previous_day", "today", "query_date"]

MAIN_SENSORS = ['日期', '农历', '八字']
DATA_FORMAT = "%Y/%m/%d/%H"
EVENT_DATE_FORMAT = "%Y/%m/%d"
MAX_BIRTHDAYS = 5
MAX_EVENTS = 30

TRANSLATIONS = {
    "zh-Hans": {
        "日期": "日期",
        "农历": "农历",
        "星期": "星期",
        "今日节日": "今日节日",
        "周数": "周数",
        "八字": "八字",
        "节气": "节气",
        "季节": "季节",
        "时辰凶吉": "时辰凶吉",
        "生肖冲煞": "生肖冲煞",
        "星座": "星座",
        "星次": "星次",
        "彭祖百忌": "彭祖百忌",
        "十二神": "十二神",
        "廿八宿": "廿八宿",
        "今日三合": "今日三合",
        "今日六合": "今日六合",
        "纳音": "纳音",
        "九宫飞星": "九宫飞星",
        "吉神方位": "吉神方位",
        "今日胎神": "今日胎神",
        "今日吉神": "今日吉神",
        "今日凶煞": "今日凶煞",
        "宜忌等第": "宜忌等第",
        "宜": "宜",
        "忌": "忌",
        "时辰经络": "时辰经络",
        "时辰": "时辰",
        "六曜": "六曜",
        "日禄": "日禄",
        "三十六禽": "三十六禽",
        "六十四卦": "六十四卦",
        "盲派": "盲派"
    },
    "zh-Hant": {
        "日期": "日期",
        "农历": "農曆",
        "星期": "星期",
        "今日节日": "今日節日",
        "周数": "週數",
        "八字": "八字",
        "节气": "節氣",
        "季节": "季節",
        "时辰凶吉": "時辰凶吉",
        "生肖冲煞": "生肖沖煞",
        "星座": "星座",
        "星次": "星次",
        "彭祖百忌": "彭祖百忌",
        "十二神": "十二神",
        "廿八宿": "廿八宿",
        "今日三合": "今日三合",
        "今日六合": "今日六合",
        "纳音": "納音",
        "九宫飞星": "九宮飛星",
        "吉神方位": "吉神方位",
        "今日胎神": "今日胎神",
        "今日吉神": "今日吉神",
        "今日凶煞": "今日凶煞",
        "宜忌等第": "宜忌等第",
        "宜": "宜",
        "忌": "忌",
        "时辰经络": "時辰經絡",
        "时辰": "時辰",
        "六曜": "六曜",
        "日禄": "日祿",
        "三十六禽": "三十六禽",
        "六十四卦": "六十四卦",
        "盲派": "盲派"
    }
}
