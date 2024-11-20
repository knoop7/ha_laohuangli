from datetime import timedelta

DOMAIN = "tgtg"
PLATFORMS = ["sensor", "button", "image"] 
CONF_BIRTHDAY_ENABLED = "birthday_enabled"
CONF_EVENT_ENABLED = "event_enabled"
CONF_GUANYIN_ENABLED = "guanyin_enabled"

CONF_BIRTHDAY_PERSONS = "birthday_persons"

CONF_NOTIFICATION_ENABLED = "notification_enabled"
CONF_NOTIFICATION_SERVICE = "notification_service"
CONF_NOTIFICATION_MESSAGE = "notification_message"


SERVICE_DATE_CONTROL = "date_control"
ATTR_ACTION = "action"
ATTR_DATE = "date"

ACTIONS = ["next_day", "previous_day", "today", "query_date"]

MAIN_SENSORS = ['日期', '农历', '八字']
DATA_FORMAT = "%Y/%m/%d/%H"
EVENT_DATE_FORMAT = "%Y/%m/%d"
MAX_BIRTHDAYS = 5
MAX_EVENTS = 30
