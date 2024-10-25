from datetime import timedelta

DOMAIN = "tgtg"
PLATFORMS = ["sensor", "button", "image"] 
MIN_TIME_BETWEEN_UPDATES = timedelta(hours=1)
MIN_TIME_BETWEEN_TWOHOUR_UPDATES = timedelta(minutes=10)
CONF_BIRTHDAY_ENABLED = "birthday_enabled"
CONF_EVENT_ENABLED = "event_enabled"
CONF_BIRTHDAY_PERSONS = "birthday_persons"


MAIN_SENSORS = ['日期', '农历', '八字']
DATA_FORMAT = "%Y/%m/%d/%H"
EVENT_DATE_FORMAT = "%Y/%m/%d"
MAX_BIRTHDAYS = 3
MAX_EVENTS = 10
