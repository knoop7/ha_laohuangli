import asyncio
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.util import dt
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from .const import DOMAIN

SERVICE_DATE_CONTROL = "date_control"
ATTR_ACTION = "action"
ATTR_DATE = "date"
ACTIONS = ["next_day", "previous_day", "today", "select_date"]

DATE_CONTROL_SCHEMA = vol.Schema({
    vol.Required(ATTR_ACTION): vol.In(ACTIONS),
    vol.Optional(ATTR_DATE): vol.Any(cv.date, None),
})

async def async_setup_date_service(hass: HomeAssistant) -> None:
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    if "current_date" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["current_date"] = dt.now()
    if "last_update_time" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["last_update_time"] = None
    
    async def handle_date_control(call: ServiceCall) -> None:
        action = call.data[ATTR_ACTION]
        date = call.data.get(ATTR_DATE)
        
        if "almanac_sensors" not in hass.data[DOMAIN]:
            return
            
        now = datetime.now()
        last_update = hass.data[DOMAIN]["last_update_time"]
        
        if action == "today":
            new_date = dt.now()
            hass.data[DOMAIN]["last_update_time"] = None
        else:
            current_date = hass.data[DOMAIN]["current_date"]
            if action == "next_day":
                new_date = current_date + timedelta(days=1)
            elif action == "previous_day":
                new_date = current_date - timedelta(days=1)
            elif action == "select_date" and date:
                current_time = current_date.time()
                new_date = datetime.combine(date, current_time)
            
            if last_update and (now - last_update).total_seconds() > 60:
                new_date = dt.now()
                hass.data[DOMAIN]["last_update_time"] = None
            else:
                hass.data[DOMAIN]["last_update_time"] = now
        
        if new_date:
            hass.data[DOMAIN]["current_date"] = new_date
            almanac_sensors = hass.data[DOMAIN]["almanac_sensors"]
            
            if isinstance(almanac_sensors, list):
                for sensor in almanac_sensors:
                    await sensor.set_date(new_date)
            elif isinstance(almanac_sensors, dict):
                for entry_id, sensors in almanac_sensors.items():
                    if isinstance(sensors, list):
                        for sensor in sensors:
                            await sensor.set_date(new_date)
                    else:
                        await sensors.set_date(new_date)

    hass.services.async_register(
        DOMAIN,
        SERVICE_DATE_CONTROL,
        handle_date_control,
        schema=DATE_CONTROL_SCHEMA
    )