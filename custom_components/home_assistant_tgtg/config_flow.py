from typing import Any, Dict, Optional
import voluptuous as vol
from datetime import datetime
from homeassistant.core import callback
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector
from homeassistant.data_entry_flow import FlowResult
from .const import (
    DOMAIN,
    DATA_FORMAT,
    EVENT_DATE_FORMAT,
    MAX_BIRTHDAYS,
    MAX_EVENTS,
    CONF_BIRTHDAY_ENABLED,
    CONF_EVENT_ENABLED,
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

            
            if self.data[CONF_BIRTHDAY_ENABLED]:
                return await self.async_step_birthday()
            elif self.data[CONF_EVENT_ENABLED]:
                return await self.async_step_event()
            return await self.async_step_name()

        from homeassistant.helpers import selector
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("setup_options", default=[]): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value="birthday", label="生日提醒"),
                            selector.SelectOptionDict(value="event", label="事件管理")
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
                return self.async_abort(reason="person_added")
            except vol.Invalid:
                errors["birthday"] = "invalid_date_format"

        return self.async_show_form(
            step_id="add_birthday",
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Required("birthday"): str,
            }),
            errors=errors
            )

    async def async_step_edit_birthday(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors = {}

        if user_input is not None:
            try:
                validate_date(user_input["birthday"])
                new_data = dict(self.data)
                old_name = self.person_name
                for idx in range(1, MAX_BIRTHDAYS + 1):
                    if (f"person{idx}_name" in new_data and 
                        new_data[f"person{idx}_name"] == self.person_name):
                        new_data[f"person{idx}_name"] = user_input["name"]
                        new_data[f"person{idx}_birthday"] = user_input["birthday"]
                        break
                
                self._save_config(new_data)
                return self.async_abort(
                    reason="person_updated",
                    description_placeholders={"name": old_name}
                )
            except vol.Invalid:
                errors["birthday"] = "invalid_date_format"

        current_birthday = ""
        for idx in range(1, MAX_BIRTHDAYS + 1):
            if (f"person{idx}_name" in self.data and 
                self.data[f"person{idx}_name"] == self.person_name):
                current_birthday = self.data[f"person{idx}_birthday"]
                break

        return self.async_show_form(
            step_id="edit_birthday",
            data_schema=vol.Schema({
                vol.Required("name", default=self.person_name): str,
                vol.Required("birthday", default=current_birthday): str,
            }),
            errors=errors
        )

    async def async_step_delete_birthday(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        if user_input is not None and user_input.get("confirm"):
            new_data = dict(self.data)
            deleted_name = self.person_name
            for idx in range(1, MAX_BIRTHDAYS + 1):
                if (f"person{idx}_name" in new_data and 
                    new_data[f"person{idx}_name"] == self.person_name):
                    new_data.pop(f"person{idx}_name")
                    new_data.pop(f"person{idx}_birthday")
                    break
            
            temp_data = {
                CONF_BIRTHDAY_ENABLED: True,
                CONF_EVENT_ENABLED: self.data.get(CONF_EVENT_ENABLED, False),
                CONF_NAME: self.data[CONF_NAME]
            }
            
            new_idx = 1
            for i in range(1, MAX_BIRTHDAYS + 1):
                if f"person{i}_name" in new_data:
                    temp_data[f"person{new_idx}_name"] = new_data[f"person{i}_name"]
                    temp_data[f"person{new_idx}_birthday"] = new_data[f"person{i}_birthday"]
                    new_idx += 1
            
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
                new_data[CONF_EVENT_ENABLED] = True
                self._save_config(new_data)
                return self.async_abort(reason="event_added")
            except vol.Invalid:
                errors["date"] = "invalid_event_date_format"

        return self.async_show_form(
            step_id="add_event",
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Required("date"): str,
                vol.Optional("description", default=""): str,
            }),
            errors=errors
        )

    async def async_step_edit_event(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors = {}

        if user_input is not None:
            try:
                validate_date(user_input["date"], is_event=True)
                new_data = dict(self.data)
                old_name = self.event_name
                for idx in range(1, MAX_EVENTS + 1):
                    if (f"event{idx}_name" in new_data and 
                        new_data[f"event{idx}_name"] == self.event_name):
                        new_data[f"event{idx}_name"] = user_input["name"]
                        new_data[f"event{idx}_date"] = user_input["date"]
                        new_data[f"event{idx}_desc"] = user_input.get("description", "")
                        break
                
                self._save_config(new_data)
                return self.async_abort(
                    reason="event_updated",
                    description_placeholders={"name": old_name}
                )
            except vol.Invalid:
                errors["date"] = "invalid_event_date_format"

        current_date = ""
        current_desc = ""
        for idx in range(1, MAX_EVENTS + 1):
            if (f"event{idx}_name" in self.data and 
                self.data[f"event{idx}_name"] == self.event_name):
                current_date = self.data[f"event{idx}_date"]
                current_desc = self.data.get(f"event{idx}_desc", "")
                break

        return self.async_show_form(
            step_id="edit_event",
            data_schema=vol.Schema({
                vol.Required("name", default=self.event_name): str,
                vol.Required("date", default=current_date): str,
                vol.Optional("description", default=current_desc): str,
            }),
            errors=errors
        )

    async def async_step_delete_event(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        if user_input is not None and user_input.get("confirm"):
            new_data = dict(self.data)
            deleted_name = self.event_name
            for idx in range(1, MAX_EVENTS + 1):
                if (f"event{idx}_name" in new_data and 
                    new_data[f"event{idx}_name"] == self.event_name):
                    new_data.pop(f"event{idx}_name")
                    new_data.pop(f"event{idx}_date")
                    if f"event{idx}_desc" in new_data:
                        new_data.pop(f"event{idx}_desc")
                    break
            
            temp_data = {
                CONF_BIRTHDAY_ENABLED: self.data.get(CONF_BIRTHDAY_ENABLED, False),
                CONF_EVENT_ENABLED: True,
                CONF_NAME: self.data[CONF_NAME]
            }
            
            for key in new_data:
                if key.startswith("person"):
                    temp_data[key] = new_data[key]
                    
            new_idx = 1
            for i in range(1, MAX_EVENTS + 1):
                if f"event{i}_name" in new_data:
                    temp_data[f"event{new_idx}_name"] = new_data[f"event{i}_name"]
                    temp_data[f"event{new_idx}_date"] = new_data[f"event{i}_date"]
                    if f"event{i}_desc" in new_data:
                        temp_data[f"event{new_idx}_desc"] = new_data[f"event{i}_desc"]
                    new_idx += 1
            
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