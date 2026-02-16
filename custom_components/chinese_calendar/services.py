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

  
    async def handle_get_almanac(call: ServiceCall) -> dict:
        data = {}
        sensors = hass.data.get(DOMAIN, {}).get("almanac_sensors", {})
        for ss in sensors.values():
            for s in ss:
                if s.state: data[s._type] = s.state
        return data
    
    async def handle_get_events(call: ServiceCall) -> dict:
        result = {"birthdays": [], "events": []}
        for entry_data in [v for v in hass.data.get(DOMAIN, {}).values() if isinstance(v, dict) and "config" in v]:
            config = entry_data.get("config", {})
            for i in range(1, 6):
                name, bday, lunar = config.get(f"person{i}_name"), config.get(f"person{i}_birthday"), config.get(f"person{i}_is_lunar", False)
                if name and bday: result["birthdays"].append({"name": name, "date": bday, "lunar": lunar})
            for i in range(1, 31):
                name, edate, lunar = config.get(f"event{i}_name"), config.get(f"event{i}_date"), config.get(f"event{i}_is_lunar", False)
                if name and edate: result["events"].append({"name": name, "date": edate, "lunar": lunar})
            break
        return result
    
    hass.services.async_register(DOMAIN, "get_almanac", handle_get_almanac, schema=vol.Schema({}), supports_response=True)
    hass.services.async_register(DOMAIN, "get_events", handle_get_events, schema=vol.Schema({}), supports_response=True)
    
    async def handle_get_holidays(call: ServiceCall) -> dict:
        import yaml, os
        year = call.data.get("year")
        yaml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hworkdays.yaml')
        def load_yaml():
            with open(yaml_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        data = await hass.async_add_executor_job(load_yaml)
        holidays = data.get("holidays", {})
        customdays = data.get("customdays", {})
        workdays = data.get("workdays", {})
        current_year = datetime.now().year
        data_year = int(list(holidays.keys())[0][:4]) if holidays else current_year
        return {"holidays": holidays, "customdays": customdays, "workdays": workdays, "data_year": data_year, "current_year": current_year}
    
    hass.services.async_register(DOMAIN, "get_holidays", handle_get_holidays, schema=vol.Schema({}), supports_response=True)