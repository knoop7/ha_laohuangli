from typing import Any, Dict, Optional
import voluptuous as vol
import re
from datetime import datetime
from homeassistant.core import callback
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector
from homeassistant.helpers import entity_registry
from homeassistant.data_entry_flow import FlowResult
from .const import (
    DOMAIN,
    DATA_FORMAT,
    EVENT_DATE_FORMAT,
    MAX_BIRTHDAYS,
    MAX_EVENTS,
    CONF_BIRTHDAY_ENABLED,
    CONF_EVENT_ENABLED,
    CONF_GUANYIN_ENABLED,
    CONF_NOTIFICATION_ENABLED,
    CONF_NOTIFICATION_SERVICE, 
    CONF_NOTIFICATION_MESSAGE,
)

def validate_date(date_str: str, is_event: bool = False) -> str:
    try:
        if is_event:
            datetime.strptime(date_str, EVENT_DATE_FORMAT)
        else:
            datetime.strptime(date_str, DATA_FORMAT)
        return date_str
    except ValueError:
        raise vol.Invalid("invalid_date_format" if not is_event else "invalid_event_date_format")

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    
    def __init__(self):
        self.data = {}
        self.current_person = 0

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            selected_options = user_input.get("setup_options", [])
            self.data[CONF_BIRTHDAY_ENABLED] = "birthday" in selected_options
            self.data[CONF_EVENT_ENABLED] = "event" in selected_options
            self.data[CONF_GUANYIN_ENABLED] = "guanyin" in selected_options

            if self.data[CONF_BIRTHDAY_ENABLED]:
                return await self.async_step_birthday()
            elif self.data[CONF_EVENT_ENABLED]:
                return await self.async_step_event()
            return await self.async_step_name()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("setup_options", default=[]): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value="birthday", label="生日提醒"),
                            selector.SelectOptionDict(value="event", label="事件管理"),
                            selector.SelectOptionDict(value="guanyin", label="观音灵签"),
                        ],
                        mode="list",
                        multiple=True
                    )
                )
            })
        )
        
    async def async_step_birthday(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors = {}
        
        if user_input is not None:
            for i in range(1, self.current_person + 1):
                if (f"person{i}_name" in self.data and 
                    self.data[f"person{i}_name"] == user_input["name"]):
                    errors["name"] = "name_already_exists"
                    return self.async_show_form(
                        step_id="birthday",
                        data_schema=vol.Schema({
                            vol.Required("name"): str,
                            vol.Required("birthday"): str,
                        }),
                        errors=errors
                    )
            
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

    async def async_step_event(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors = {}
        event_count = sum(1 for key in self.data if key.startswith("event") and key.endswith("_name"))

        if event_count >= MAX_EVENTS:
            return await self.async_step_guanyin()

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

    async def async_step_name(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        if user_input is not None:
            self.data[CONF_NAME] = user_input[CONF_NAME]
            if not self.data.get(CONF_EVENT_ENABLED):
                self.data[CONF_EVENT_ENABLED] = False
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

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry
        self.data = dict(config_entry.data)
        self.person_name = None
        self.event_name = None
        self.selected_area = None
        self._edit_event_data = None  


    @callback
    def _save_config(self, new_data: dict) -> None:
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data=new_data
        )
        self.data = dict(new_data)

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        if user_input is not None:
            self.selected_area = user_input["area"]
            return await self.async_step_actions()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("area"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value="birthday", label="生日管理"),
                            selector.SelectOptionDict(value="event", label="事件管理"),
                        ],
                        mode="dropdown"
                    )
                )
            })
        )

    async def async_step_actions(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        current_action = None
        
        person_list = self._get_person_list() if self.selected_area == "birthday" else {}
        event_list = self._get_event_list() if self.selected_area == "event" else {}
        has_existing_data = bool(person_list if self.selected_area == "birthday" else event_list)

        action_options = [selector.SelectOptionDict(value="add", label="添加")]
        if has_existing_data:
            action_options.extend([
                selector.SelectOptionDict(value="edit", label="编辑"),
                selector.SelectOptionDict(value="delete", label="删除")
            ])

        if user_input is not None:
            current_action = user_input.get("action")
            
            if current_action == "add":
                if self.selected_area == "birthday":
                    return await self.async_step_add_birthday()
                else:
                    return await self.async_step_add_event()
            
            elif current_action in ["edit", "delete"]:
                self.current_action = current_action  
                if self.selected_area == "birthday":
                    return await self.async_step_select_person()
                else:
                    return await self.async_step_select_event()

        schema = {
            vol.Required("action", default="add"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=action_options,
                    mode="list"
                )
            )
        }

        return self.async_show_form(
            step_id="actions",
            data_schema=vol.Schema(schema)
        )

    async def async_step_select_person(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        if user_input is not None:
            self.person_name = user_input["person_index"]
            if self.current_action == "edit":
                return await self.async_step_edit_birthday()
            return await self.async_step_delete_birthday()

        person_list = self._get_person_list()
        
        return self.async_show_form(
            step_id="select_person",
            data_schema=vol.Schema({
                vol.Required("person_index", description="options.step.actions.data.person_index"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=name, label=name)
                            for name in person_list.keys()
                        ],
                        mode="dropdown"
                    )
                )
            })
        )

    async def async_step_select_event(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        if user_input is not None:
            self.event_name = user_input["event_index"]
            if self.current_action == "edit":
                return await self.async_step_edit_event()
            return await self.async_step_delete_event()

        event_list = self._get_event_list()
        
        return self.async_show_form(
            step_id="select_event",
            data_schema=vol.Schema({
                vol.Required("event_index", description="options.step.actions.data.event_index"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=name, label=name)
                            for name in event_list.keys()
                        ],
                        mode="dropdown"
                    )
                )
            })
        )

    def _get_person_list(self):
        return {
            self.data[key]: self.data[key]
            for key in sorted(self.data.keys())
            if key.endswith("_name") and key.startswith("person")
        }

    def _get_event_list(self):
        return {
            self.data[key]: self.data[key]
            for key in sorted(self.data.keys())
            if key.endswith("_name") and key.startswith("event")
        }

    async def async_step_add_birthday(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors = {}
        person_count = sum(1 for key in self.data if key.startswith("person") and key.endswith("_name"))

        if person_count >= MAX_BIRTHDAYS:
            return self.async_abort(reason="max_persons_reached")

        if user_input is not None:
            for idx in range(1, MAX_BIRTHDAYS + 1):
                if (f"person{idx}_name" in self.data and 
                    self.data[f"person{idx}_name"] == user_input["name"]):
                    errors["name"] = "name_already_exists"
                    return self.async_show_form(
                        step_id="add_birthday",
                        data_schema=vol.Schema({
                            vol.Required("name"): str,
                            vol.Required("birthday"): str,
                            vol.Optional(CONF_NOTIFICATION_ENABLED, default=False): bool,
                        }),
                        errors=errors
                    )
            
            try:
                validate_date(user_input["birthday"])
                
                new_data = dict(self.data)
                person_count += 1
                new_data[f"person{person_count}_name"] = user_input["name"]
                new_data[f"person{person_count}_birthday"] = user_input["birthday"]
                new_data[CONF_BIRTHDAY_ENABLED] = True
                self._save_config(new_data)
                
                self._edit_person_data = {
                    "name": user_input["name"],
                    "birthday": user_input["birthday"],
                    "notification_enabled": user_input.get(CONF_NOTIFICATION_ENABLED, False),
                    "current_idx": person_count,
                    "old_name": user_input["name"]
                }
                
                if user_input.get(CONF_NOTIFICATION_ENABLED):
                    self.person_name = user_input["name"]
                    return await self.async_step_birthday_notification_edit()
                
                return self.async_abort(reason="person_added")
                
            except vol.Invalid:
                errors["birthday"] = "invalid_date_format"

        return self.async_show_form(
            step_id="add_birthday",
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Required("birthday"): str,
                vol.Optional(CONF_NOTIFICATION_ENABLED, default=False): bool,
            }),
            errors=errors
        )

    async def async_step_add_event(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors = {}
        event_count = sum(1 for key in self.data if key.startswith("event") and key.endswith("_name"))

        if event_count >= MAX_EVENTS:
            return self.async_abort(reason="max_events_reached")

        if user_input is not None:
            try:
                validate_date(user_input["date"], is_event=True)
                
                new_data = dict(self.data)
                event_count += 1
                new_data[f"event{event_count}_name"] = user_input["name"]
                new_data[f"event{event_count}_date"] = user_input["date"]
                new_data[f"event{event_count}_desc"] = user_input.get("description", "")
                new_data[CONF_EVENT_ENABLED] = True
                self._save_config(new_data)
                
                self._edit_event_data = {
                    "name": user_input["name"],
                    "date": user_input["date"],
                    "description": user_input.get("description", ""),
                    "notification_enabled": user_input.get(CONF_NOTIFICATION_ENABLED, False),
                    "current_idx": event_count
                }
                
                if user_input.get(CONF_NOTIFICATION_ENABLED):
                    self.event_name = user_input["name"]
                    return await self.async_step_event_notification_edit()
                
                return self.async_abort(reason="event_added")
                
            except vol.Invalid:
                errors["date"] = "invalid_event_date_format"

        return self.async_show_form(
            step_id="add_event",
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Required("date"): str,
                vol.Optional("description", default=""): str,
                vol.Optional(CONF_NOTIFICATION_ENABLED, default=False): bool,
            }),
            errors=errors
        )

    async def async_step_edit_birthday(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors = {}
        current_idx = None

        for idx in range(1, MAX_BIRTHDAYS + 1):
            if (f"person{idx}_name" in self.data and 
                self.data[f"person{idx}_name"] == self.person_name):
                current_idx = idx
                break

        if user_input is not None:
            try:
                validate_date(user_input["birthday"])
                self._edit_person_data = {
                    "name": user_input["name"],
                    "birthday": user_input["birthday"],
                    "notification_enabled": user_input.get(CONF_NOTIFICATION_ENABLED, False),
                    "current_idx": current_idx,
                    "old_name": self.person_name
                }
                
                if user_input.get(CONF_NOTIFICATION_ENABLED):
                    self.person_name = user_input["name"]  
                    return await self.async_step_birthday_notification_edit()
                
                new_data = dict(self.data)
                new_data[f"person{current_idx}_name"] = user_input["name"]
                new_data[f"person{current_idx}_birthday"] = user_input["birthday"]
                if f"person{current_idx}_notification_service" in new_data:
                    new_data.pop(f"person{current_idx}_notification_service")
                if f"person{current_idx}_notification_message" in new_data:
                    new_data.pop(f"person{current_idx}_notification_message")
                
                self._edit_person_data = None
                self._save_config(new_data)
                return self.async_abort(
                    reason="person_updated",
                    description_placeholders={"name": self.person_name}
                )
                
            except vol.Invalid:
                errors["birthday"] = "invalid_date_format"

        current_birthday = ""
        current_notification = False
        if current_idx:
            current_birthday = self.data[f"person{current_idx}_birthday"]
            current_notification = bool(self.data.get(f"person{current_idx}_notification_service"))

        return self.async_show_form(
            step_id="edit_birthday",
            data_schema=vol.Schema({
                vol.Required("name", default=self.person_name): str,
                vol.Required("birthday", default=current_birthday): str,
                vol.Optional(CONF_NOTIFICATION_ENABLED, default=current_notification): bool,
            }),
            errors=errors
        )

    async def async_step_birthday_notification_edit(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        notify_services = []
        services = self.hass.services.async_services().get("notify", {})
        for service in services:
            notify_services.append(
                selector.SelectOptionDict(
                    value=service, 
                    label=service
                )
            )
        
        if not user_input:
            current_idx = self._edit_person_data["current_idx"]
            current_service = self.data.get(f"person{current_idx}_notification_service", "")
            current_message = self.data.get(f"person{current_idx}_notification_message", 
                                        f"今天是{self._edit_person_data['name']}的生日，祝您生日快乐！🎉")
                    
            return self.async_show_form(
                step_id="birthday_notification_edit",
                data_schema=vol.Schema({
                    vol.Required(CONF_NOTIFICATION_SERVICE, default=current_service if current_service else notify_services[0]["value"] if notify_services else ""): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=notify_services,
                            mode="dropdown"
                        )
                    ),
                    vol.Required(CONF_NOTIFICATION_MESSAGE, default=current_message): str,
                })
            )

        try:
            new_data = dict(self.data)
            current_idx = self._edit_person_data["current_idx"]
            
            new_data[f"person{current_idx}_name"] = self._edit_person_data["name"]
            new_data[f"person{current_idx}_birthday"] = self._edit_person_data["birthday"]
            
            new_data[f"person{current_idx}_notification_service"] = user_input[CONF_NOTIFICATION_SERVICE]
            new_data[f"person{current_idx}_notification_message"] = user_input[CONF_NOTIFICATION_MESSAGE]
            
            self._edit_person_data = None
            self._save_config(new_data)
            
            return self.async_abort(
                reason="person_updated",
                description_placeholders={"name": self.person_name}
            )
        except Exception as e:
            return self.async_show_form(
                step_id="birthday_notification_edit",
                data_schema=vol.Schema({
                    vol.Required(CONF_NOTIFICATION_SERVICE): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=notify_services,
                            mode="dropdown"
                        )
                    ),
                    vol.Required(CONF_NOTIFICATION_MESSAGE): str,
                }),
                errors={"base": "save_error"}
            )

    async def async_step_delete_birthday(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        if user_input is not None and user_input.get("confirm"):
            new_data = dict(self.data)
            deleted_name = self.person_name
            
            for idx in range(1, MAX_BIRTHDAYS + 1):
                if (f"person{idx}_name" in new_data and 
                    new_data[f"person{idx}_name"] == self.person_name):
                    registry = entity_registry.async_get(self.hass)
                    entity_id = f"sensor.birthday_{self.person_name.lower()}"
                    if entity_entry := registry.async_get(entity_id):
                        registry.async_remove(entity_entry.entity_id)
                        
                    new_data.pop(f"person{idx}_name")
                    new_data.pop(f"person{idx}_birthday")
                    if f"person{idx}_notification_service" in new_data:
                        new_data.pop(f"person{idx}_notification_service")
                    if f"person{idx}_notification_message" in new_data:
                        new_data.pop(f"person{idx}_notification_message")
                    break
            
            temp_data = {
                CONF_BIRTHDAY_ENABLED: True,
                CONF_EVENT_ENABLED: self.data.get(CONF_EVENT_ENABLED, False),
                CONF_NAME: self.data[CONF_NAME]
            }
            
            new_idx = 1
            has_persons = False
            for i in range(1, MAX_BIRTHDAYS + 1):
                if f"person{i}_name" in new_data:
                    has_persons = True
                    temp_data[f"person{new_idx}_name"] = new_data[f"person{i}_name"]
                    temp_data[f"person{new_idx}_birthday"] = new_data[f"person{i}_birthday"]
                    if f"person{i}_notification_service" in new_data:
                        temp_data[f"person{new_idx}_notification_service"] = new_data[f"person{i}_notification_service"]
                    if f"person{i}_notification_message" in new_data:
                        temp_data[f"person{new_idx}_notification_message"] = new_data[f"person{i}_notification_message"]
                    new_idx += 1
            
            if not has_persons:
                temp_data[CONF_BIRTHDAY_ENABLED] = False
            
            for key in new_data:
                if key.startswith("event"):
                    temp_data[key] = new_data[key]

            self._save_config(temp_data)
            return self.async_abort(
                reason="person_deleted",
                description_placeholders={"name": deleted_name}
            )

        return self.async_show_form(
            step_id="delete_birthday",
            data_schema=vol.Schema({
                vol.Required("confirm", default=False): bool,
            })
        )


    async def async_step_add_event(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors = {}
        event_count = sum(1 for key in self.data if key.startswith("event") and key.endswith("_name"))

        if event_count >= MAX_EVENTS:
            return self.async_abort(reason="max_events_reached")

        if user_input is not None:
            try:
                validate_date(user_input["date"], is_event=True)
                
                new_data = dict(self.data)
                event_count += 1
                new_data[f"event{event_count}_name"] = user_input["name"]
                new_data[f"event{event_count}_date"] = user_input["date"]
                new_data[f"event{event_count}_desc"] = user_input.get("description", "")
                new_data[f"event{event_count}_auto_remove"] = user_input.get("auto_remove", False)
                new_data[f"event{event_count}_full_countdown"] = user_input.get("full_countdown", False)
                new_data[CONF_EVENT_ENABLED] = True
                self._save_config(new_data)

                self._edit_event_data = {
                    "name": user_input["name"],
                    "date": user_input["date"],
                    "description": user_input.get("description", ""),
                    "auto_remove": user_input.get("auto_remove", False),
                    "full_countdown": user_input.get("full_countdown", False),
                    "notification_enabled": user_input.get(CONF_NOTIFICATION_ENABLED, False),
                    "current_idx": event_count
                }
                
                if user_input.get("full_countdown"):
                    self.event_name = user_input["name"]
                    return await self.async_step_edit_event_time()
                elif user_input.get(CONF_NOTIFICATION_ENABLED):
                    self.event_name = user_input["name"]
                    return await self.async_step_event_notification_edit()
                
                return self.async_abort(reason="event_added")
                
            except vol.Invalid:
                errors["date"] = "invalid_event_date_format"

        return self.async_show_form(
            step_id="add_event",
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Required("date"): str,
                vol.Optional("description", default=""): str,
                vol.Optional("auto_remove", default=False): bool,
                vol.Optional("full_countdown", default=False): bool,
                vol.Optional(CONF_NOTIFICATION_ENABLED, default=False): bool,
            }),
            errors=errors
        )

    async def async_step_edit_event(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors = {}
        
        current_idx = None
        for idx in range(1, MAX_EVENTS + 1):
            if (f"event{idx}_name" in self.data and 
                self.data[f"event{idx}_name"] == self.event_name):
                current_idx = idx
                break
                
        if current_idx is None:
            return self.async_abort(reason="event_not_found")
            
        current_date = self.data[f"event{current_idx}_date"].split()[0] if " " in self.data[f"event{current_idx}_date"] else self.data[f"event{current_idx}_date"]
        current_desc = self.data.get(f"event{current_idx}_desc", "")
        current_auto_remove = self.data.get(f"event{current_idx}_auto_remove", False)
        current_full_countdown = self.data.get(f"event{current_idx}_full_countdown", False)
        current_notification = bool(self.data.get(f"event{current_idx}_notification_service"))

        if user_input is not None:
            try:
                validate_date(user_input["date"], is_event=True)
                
                for idx in range(1, MAX_EVENTS + 1):
                    if (f"event{idx}_name" in self.data and 
                        self.data[f"event{idx}_name"] == user_input["name"] and
                        idx != current_idx):
                        errors["name"] = "duplicate_event_name"
                        break
                        
                if not errors:
                    self._edit_event_data = {
                        "name": user_input["name"],
                        "date": user_input["date"],
                        "description": user_input.get("description", ""),
                        "auto_remove": user_input.get("auto_remove", False),
                        "full_countdown": user_input.get("full_countdown", False),
                        "notification_enabled": user_input.get(CONF_NOTIFICATION_ENABLED, False),
                        "current_idx": current_idx
                    }
                    
                    if user_input.get("full_countdown"):
                        return await self.async_step_edit_event_time()
                    elif user_input.get(CONF_NOTIFICATION_ENABLED):
                        return await self.async_step_event_notification_edit()
                    
                    new_data = dict(self.data)
                    new_data[f"event{current_idx}_name"] = user_input["name"]
                    new_data[f"event{current_idx}_date"] = user_input["date"]
                    new_data[f"event{current_idx}_desc"] = user_input.get("description", "")
                    new_data[f"event{current_idx}_auto_remove"] = user_input.get("auto_remove", False)
                    new_data[f"event{current_idx}_full_countdown"] = False
                    new_data.pop(f"event{current_idx}_notification_service", None)
                    new_data.pop(f"event{current_idx}_notification_message", None)
                    
                    self._edit_event_data = None
                    self._save_config(new_data)
                    return self.async_abort(
                        reason="event_updated",
                        description_placeholders={"name": self.event_name}
                    )
                    
            except vol.Invalid:
                errors["date"] = "invalid_event_date_format"

        return self.async_show_form(
            step_id="edit_event",
            data_schema=vol.Schema({
                vol.Required("name", default=self.event_name): str,
                vol.Required("date", default=current_date): str,
                vol.Optional("description", default=current_desc): str,
                vol.Optional("auto_remove", default=current_auto_remove): bool,
                vol.Optional("full_countdown", default=current_full_countdown): bool,
                vol.Optional(CONF_NOTIFICATION_ENABLED, default=current_notification): bool,
            }),
            errors=errors
        )

    async def async_step_edit_event_time(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors = {}

        if user_input is not None:
            time_str = user_input["time"]
            if re.match(r"^([0-1][0-9]|2[0-3])/[0-5][0-9]$", time_str):
                if self._edit_event_data is None:
                    return self.async_abort(reason="event_not_found")
                    
                self._edit_event_data["time"] = time_str
                
                if self._edit_event_data.get("notification_enabled"):
                    return await self.async_step_event_notification_edit()
                
                new_data = dict(self.data)
                current_idx = self._edit_event_data["current_idx"]
                new_data[f"event{current_idx}_name"] = self._edit_event_data["name"]
                new_data[f"event{current_idx}_date"] = f"{self._edit_event_data['date']} {time_str}"
                new_data[f"event{current_idx}_desc"] = self._edit_event_data.get("description", "")
                new_data[f"event{current_idx}_auto_remove"] = self._edit_event_data.get("auto_remove", False)
                new_data[f"event{current_idx}_full_countdown"] = True
                new_data.pop(f"event{current_idx}_notification_service", None)
                new_data.pop(f"event{current_idx}_notification_message", None)
                
                self._edit_event_data = None
                self._save_config(new_data)
                
                return self.async_abort(
                    reason="event_updated",
                    description_placeholders={"name": self.event_name}
                )
            else:
                errors["time"] = "invalid_time_format"

        return self.async_show_form(
            step_id="edit_event_time",
            data_schema=vol.Schema({
                vol.Required("time", default="12/00"): str
            }),
            errors=errors,
            description_placeholders={"name": self.event_name}
        )

    async def async_step_event_notification_edit(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        notify_services = []
        services = self.hass.services.async_services().get("notify", {})
        for service in services:
            notify_services.append(
                selector.SelectOptionDict(
                    value=service,
                    label=service
                )
            )

        def get_template_message(event_name: str) -> str:
            event_name_lower = event_name.lower()
            
            keyword_patterns = {
                "纪念": ["纪念日", "纪念", "周年", "周年纪念", "纪念活动", "庆典", "庆祝", "节日", "节庆", 
                        "开业纪念", "创业纪念", "入职纪念", "相识纪念", "毕业纪念"],
                "投资": ["投资", "股票", "基金", "期货", "债券", "理财通", "余额宝", "定投", "信托", 
                        "股市", "炒股", "数字货币", "加密货币", "黄金", "贵金属", "期权", "港股", "美股"],
                "理财": ["理财", "存款", "理财产品", "存单", "储蓄", "取款", "利息", "收益", "分红", 
                        "工资", "薪资", "收入", "支付", "转账", "年终奖", "提成", "报销"],
                "工作": ["工作日", "工作", "上班", "补班", "加班", "晨会", "例会", "年会", "述职", 
                        "汇报", "面试", "复工", "入职", "转正", "升职", "离职", "调岗", "述职", 
                        "考核", "评估", "签到", "打卡", "早会", "周会", "月会"],
                "休假": ["休假", "假期", "放假", "调休", "请假", "年假", "事假", "病假", "产假", 
                        "陪产假", "婚假", "丧假", "探亲假", "寒假", "暑假", "春节", "国庆", "中秋",
                        "休息", "放松", "小长假", "大长假", "调整放假"],
                "结婚": ["结婚日", "结婚", "婚礼", "同房", "订婚", "求婚", "恋爱纪念", "领证", "结婚周年",
                        "金婚", "银婚", "钻石婚", "蜜月", "婚宴", "婚礼策划", "婚纱照", "婚前", "婚后",
                        "约会", "纪念日", "恋爱", "热恋", "相亲"],
                "旅行": ["旅行", "旅游", "出游", "度假", "旅程", "行程", "出差", "商务", "机票", "火车",
                        "高铁", "航班", "酒店", "民宿", "入住", "退房", "签证", "护照", "通行证", 
                        "观光", "跟团", "自由行", "自驾游", "露营", "徒步", "登山", "毕业旅行"],
                "还款": ["还款日", "还款", "还贷", "还债", "还信用卡", "房贷", "车贷", "按揭", "月供",
                        "分期", "信用卡账单", "贷款", "欠款", "借款", "网贷", "信用卡", "欠费", 
                        "缴费", "账单", "扣款", "代扣", "自动还款"],
                "学习": ["学习", "考试", "课程", "上课", "补课", "培训", "讲座", "研修", "进修", "考研",
                        "考证", "考级", "学位", "毕业", "论文", "答辩", "开学", "复习", "测验", 
                        "作业", "考核", "期中", "期末", "笔试", "面试", "实习", "实训"],
                "运动": ["运动", "健身", "锻炼", "跑步", "游泳", "瑜伽", "健康", "运动会", "马拉松", 
                        "球赛", "比赛", "训练", "篮球", "足球", "羽毛球", "乒乓球", "网球", "高尔夫",
                        "减肥", "塑形", "体测", "体检", "打卡运动"],
                "医疗": ["医疗", "就医", "看病", "挂号", "体检", "复查", "复诊", "手术", "治疗", "换药",
                        "拆线", "门诊", "住院", "出院", "预约", "取药", "配药", "打针", "输液", 
                        "检查", "化验", "疫苗", "接种", "保健", "康复", "心理咨询"],
                "维护": ["维护", "保养", "维修", "检修", "年检", "换油", "轮胎", "保险", "车检", "年审",
                        "换季保养", "清洗", "维保", "检查", "安检", "消防检查", "设备维护", "系统维护",
                        "例行检查", "故障维修", "定期保养", "装修", "翻新", "整修", "改造"]
            }

            message_templates = {
                "纪念": "今天是「{name}」时间到了，让我们共同铭记这个特殊的日子。🎉",
                "投资": "您关注的「{name}」时间到了，请及时查看并作出相应决策。📊",
                "理财": "您的「{name}」时间到了，请及时查看账户情况。💰",
                "工作": "今天是「{name}」时间到了，请注意安排好您的工作计划。📝",
                "休假": "您的「{name}」已到，祝您假期愉快！🌴",
                "结婚": "今天是「{name}」，愿您的爱情甜蜜永恒！💑",
                "旅行": "您的「{name}」时间到了，祝您旅途愉快！✈️",
                "还款": "您设置的「{name}」时间到了，请及时处理。💳",
                "学习": "您的「{name}」时间到了，保持学习热情！📚",
                "运动": "您的「{name}」时间到了，坚持就是胜利！💪",
                "医疗": "您的「{name}」时间到了，请注意按时就医。🏥",
                "维护": "您的「{name}」时间到了，请及时检查和处理。🔧"
            }


            for category, keywords in keyword_patterns.items():
                for keyword in keywords:
                    if keyword in event_name_lower:
                        return message_templates[category].format(name=event_name)

            return f"您设置的事件 「 {event_name} 」 提醒时间到了！"

        if not user_input:
            if not self._edit_event_data:
                return self.async_abort(reason="event_not_found")

            current_idx = self._edit_event_data["current_idx"]
            current_service = self.data.get(f"event{current_idx}_notification_service", "")
            current_message = self.data.get(
                f"event{current_idx}_notification_message",
                get_template_message(self._edit_event_data["name"])
            )

            return self.async_show_form(
                step_id="event_notification_edit",
                data_schema=vol.Schema({
                    vol.Required(CONF_NOTIFICATION_SERVICE, default=current_service): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=notify_services,
                            mode="dropdown"
                        )
                    ),
                    vol.Optional(CONF_NOTIFICATION_MESSAGE, default=current_message): str,
                })
            )

        try:
            new_data = dict(self.data)
            current_idx = self._edit_event_data["current_idx"]
            new_data[f"event{current_idx}_name"] = self._edit_event_data["name"]
            
            if "time" in self._edit_event_data:
                new_data[f"event{current_idx}_date"] = f"{self._edit_event_data['date']} {self._edit_event_data['time']}"
                new_data[f"event{current_idx}_full_countdown"] = True
            else:
                new_data[f"event{current_idx}_date"] = self._edit_event_data["date"]
                new_data[f"event{current_idx}_full_countdown"] = False
                
            new_data[f"event{current_idx}_desc"] = self._edit_event_data.get("description", "")
            new_data[f"event{current_idx}_auto_remove"] = self._edit_event_data.get("auto_remove", False)
            new_data[f"event{current_idx}_notification_service"] = user_input[CONF_NOTIFICATION_SERVICE]
            new_data[f"event{current_idx}_notification_message"] = user_input[CONF_NOTIFICATION_MESSAGE]
            
            self._edit_event_data = None
            self._save_config(new_data)
            
            return self.async_abort(
                reason="event_updated",
                description_placeholders={"name": self.event_name}
            )
        
        except Exception as e:
            _LOGGER.error("更新事件通知配置失败: %s", e)
            return self.async_show_form(
                step_id="event_notification_edit",
                data_schema=vol.Schema({
                    vol.Required(CONF_NOTIFICATION_SERVICE): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=notify_services,
                            mode="dropdown"
                        )
                    ),
                    vol.Required(CONF_NOTIFICATION_MESSAGE): str,
                }),
                errors={"base": "save_error"}
            )

    async def async_step_delete_event(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        if user_input is not None and user_input.get("confirm"):
            new_data = dict(self.data)
            deleted_name = self.event_name
            deleted_idx = None
            
            for idx in range(1, MAX_EVENTS + 1):
                if (f"event{idx}_name" in new_data and 
                    new_data[f"event{idx}_name"] == self.event_name):
                    registry = entity_registry.async_get(self.hass)
                    entity_id = f"sensor.event_{self.event_name.lower()}"
                    if entity_entry := registry.async_get(entity_id):
                        registry.async_remove(entity_entry.entity_id)
                    deleted_idx = idx
                    break
            
            if deleted_idx:
                new_data.pop(f"event{deleted_idx}_name")
                new_data.pop(f"event{deleted_idx}_date")
                if f"event{deleted_idx}_desc" in new_data:
                    new_data.pop(f"event{deleted_idx}_desc")
                if f"event{deleted_idx}_auto_remove" in new_data:
                    new_data.pop(f"event{deleted_idx}_auto_remove")
                if f"event{deleted_idx}_full_countdown" in new_data:
                    new_data.pop(f"event{deleted_idx}_full_countdown")
                if f"event{deleted_idx}_notification_service" in new_data:
                    new_data.pop(f"event{deleted_idx}_notification_service")
                if f"event{deleted_idx}_notification_message" in new_data:
                    new_data.pop(f"event{deleted_idx}_notification_message")

                has_events = False
                
                temp_data = {
                    CONF_BIRTHDAY_ENABLED: new_data.get(CONF_BIRTHDAY_ENABLED, False),
                    CONF_EVENT_ENABLED: True,  
                    CONF_NAME: new_data[CONF_NAME]
                }
                
                for key in new_data:
                    if key.startswith("person"):
                        temp_data[key] = new_data[key]
                
                new_idx = 1
                for idx in range(1, MAX_EVENTS + 1):
                    if f"event{idx}_name" in new_data and idx != deleted_idx:
                        has_events = True
                        temp_data[f"event{new_idx}_name"] = new_data[f"event{idx}_name"]
                        temp_data[f"event{new_idx}_date"] = new_data[f"event{idx}_date"]
                        if f"event{idx}_desc" in new_data:
                            temp_data[f"event{new_idx}_desc"] = new_data[f"event{idx}_desc"]
                        if f"event{idx}_auto_remove" in new_data:
                            temp_data[f"event{new_idx}_auto_remove"] = new_data[f"event{idx}_auto_remove"]
                        if f"event{idx}_full_countdown" in new_data:
                            temp_data[f"event{new_idx}_full_countdown"] = new_data[f"event{idx}_full_countdown"]
                        if f"event{idx}_notification_service" in new_data:
                            temp_data[f"event{new_idx}_notification_service"] = new_data[f"event{idx}_notification_service"]
                        if f"event{idx}_notification_message" in new_data:
                            temp_data[f"event{new_idx}_notification_message"] = new_data[f"event{idx}_notification_message"]
                        new_idx += 1

                if not has_events:
                    temp_data[CONF_EVENT_ENABLED] = False

                self._save_config(temp_data)
                return self.async_abort(
                    reason="event_deleted",
                    description_placeholders={"name": deleted_name}
                )

        return self.async_show_form(
            step_id="delete_event",
            data_schema=vol.Schema({
                vol.Required("confirm", default=False): bool,
            })
        )
        