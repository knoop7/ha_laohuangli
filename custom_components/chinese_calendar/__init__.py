import asyncio
import weakref
import time
from typing import Dict, Set, Optional, List
from homeassistant.core import HomeAssistant
from homeassistant.util import yaml
from homeassistant.helpers import entity_registry
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.components.lovelace import DOMAIN
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig, HomeAssistantView
from aiohttp import web
from datetime import datetime
from .services import async_setup_date_service, SERVICE_DATE_CONTROL
from .const import (
    DOMAIN, 
    PLATFORMS, 
    CONF_BIRTHDAY_ENABLED,
    CONF_EVENT_ENABLED,
    MAX_BIRTHDAYS,
    MAX_EVENTS,
)

class TaskManager:
    def __init__(self):
        self._tasks: Set[asyncio.Task] = weakref.WeakSet()
        self._lock = asyncio.Lock()
        self._closing = False

    async def create_task(self, coro) -> asyncio.Task:
        if self._closing: return
        async with self._lock:
            task = asyncio.create_task(coro)
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            return task

    async def cancel_all(self):
        self._closing = True
        async with self._lock:
            remaining = list(self._tasks)
            for task in remaining:
                if not task.done():
                    task.cancel()
            if remaining:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*remaining, return_exceptions=True),
                        timeout=10.0
                    )
                except asyncio.TimeoutError:
                    pass
                finally:
                    self._tasks.clear()
                    
class RegistryManager:
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self._registry = entity_registry.async_get(hass)
        self._cleanup_lock = asyncio.Lock()
        self._entities: Dict[str, str] = {}

    def _get_entity_parts(self, unique_id: str) -> tuple:  
        if not unique_id: return None, None, None
        parts = unique_id.split('_')
        if len(parts) < 4: return None, None, None
        return parts[0], parts[2], parts[3]

    def _get_entity_by_base_id(self, registry_entities: Dict, base_name: str, type_name: str) -> List:
        matching = []
        for entity in registry_entities.values():
            if not entity.unique_id: continue
            prefix, name, type = self._get_entity_parts(entity.unique_id)
            if prefix == "birthday" and name == base_name and type == type_name:
                matching.append(entity)
        return matching

    async def cleanup_orphaned_entities(self, config_entry: ConfigEntry) -> None:
        async with self._cleanup_lock:
            try:
                all_entities = entity_registry.async_entries_for_config_entry(self._registry, config_entry.entry_id)
                all_registry = self._registry.entities
                valid_entities = await self._get_valid_entities(config_entry)
                preserved_entities = {}
                
                for entity in all_entities:
                    if entity.disabled_by is None:
                        preserved_entities[entity.unique_id] = entity.entity_id

                for entity in all_entities:
                    if "月相" in entity.unique_id: continue
                    if ("birthday_" in entity.unique_id or "event_" in entity.unique_id):
                        base_name = ""
                        if "_" in entity.unique_id:
                            prefix, name, type = self._get_entity_parts(entity.unique_id)
                            if name: base_name = name
                            
                        found = False
                        for i in range(1, MAX_BIRTHDAYS + 1):
                            if config_entry.data.get(f"person{i}_name", "").lower() == base_name:
                                found = True
                                if entity.unique_id in preserved_entities:
                                    self._entities[entity.unique_id] = preserved_entities[entity.unique_id]
                                break
                        
                        if not found:
                            prefix, name, type = self._get_entity_parts(entity.unique_id)
                            if name and type:
                                matching_entities = self._get_entity_by_base_id(all_registry, name, type)
                                active_entities = [e for e in matching_entities if e != entity and e.disabled_by is None]
                                
                                if not active_entities:
                                    if any(matching.unique_id in preserved_entities for matching in matching_entities):
                                        continue
                                    await self._remove_entity(entity.entity_id, entity.unique_id)
            except Exception as e:
                raise RuntimeError(f"清理失败: {str(e)}") from e

    async def _remove_entity(self, entity_id: str, entity_unique_id: str) -> None:
        try:
            entity_entry = self._registry.async_get(entity_id)
            if entity_entry: self._registry.async_remove(entity_id)
            entity_state = self.hass.states.get(entity_id)
            if entity_state: self.hass.states.async_remove(entity_id)
            self._entities.pop(entity_unique_id, None)
            if "birthday_" in entity_unique_id:
                parts = entity_unique_id.split('_')
                if len(parts) > 2:
                    name_part = parts[2] 
                    suffix_list = ['ba_zi', 'yang_li_sheng_ri', 'nong_li_sheng_ri', 'sheng_ri_ti_xing_nong', 'sheng_ri_ti_xing_yang', 'xing_zuo', 'xi_yong_shen', 'jin_ri_yun_shi', 'sheng_cun_tian_shu', 'zhou_sui']
                    for suffix in suffix_list:
                        related_id = f"sensor.sheng_ri_guan_li_{name_part}_{suffix}"
                        if self.hass.states.get(related_id): self.hass.states.async_remove(related_id)
                        if entry := self._registry.async_get(related_id): self._registry.async_remove(related_id)
        except Exception: pass

    async def _get_valid_entities(self, config_entry: ConfigEntry) -> Set[str]:
        valid_entities = set()
        if config_entry.data.get(CONF_BIRTHDAY_ENABLED):
            for i in range(1, MAX_BIRTHDAYS + 1):
                name = config_entry.data.get(f"person{i}_name")
                if name: valid_entities.add(f"birthday_{name.lower()}_{i}")
        if config_entry.data.get(CONF_EVENT_ENABLED):
            for i in range(1, MAX_EVENTS + 1):
                name = config_entry.data.get(f"event{i}_name")
                if name: valid_entities.add(f"event_{name.lower()}_{i}")
        return valid_entities

    async def cleanup_all_entities(self, config_entry: ConfigEntry) -> None:
        try:
            registry = self._registry
            states = self.hass.states.async_all()
            
            preserved_states = {}
            entities = entity_registry.async_entries_for_config_entry(registry, config_entry.entry_id)
            for entity in entities:
                if entity.entity_category == "diagnostic":
                    preserved_states[entity.entity_id] = {
                        'unique_id': entity.unique_id,
                        'name': entity.name,
                        'disabled_by': entity.disabled_by,
                        'platform': entity.platform,
                        'entity_category': entity.entity_category
                    }
            
            prefixes = ["sheng_ri_guan_li", "shi_jian_guan_li"]
            for state in states:
                entity_id = state.entity_id
                if any(prefix in entity_id for prefix in prefixes):
                    if "月相" not in entity_id:
                        self.hass.states.async_remove(entity_id)
                        if entry := registry.async_get(entity_id):
                            if entry.entity_category != "diagnostic":
                                registry.async_remove(entity_id)
            
            for entity_id, state in preserved_states.items():
                if state.get('entity_category') == "diagnostic":
                    registry.async_get_or_create(
                        domain="sensor",
                        platform=state['platform'],
                        unique_id=state['unique_id'],
                        suggested_object_id=entity_id.split('.')[1],
                        disabled_by=state['disabled_by'],
                        entity_category=state['entity_category']
                    )
                        
        except Exception:
            raise

class AlmanacCoordinator:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self._sensors = set()  
        self._lock = asyncio.Lock()
        self._cleanup_lock = asyncio.Lock()
        self._update_listeners = {}
        
    async def register_sensor(self, sensor):
        async with self._lock:
            self._sensors.add(sensor)
            
    async def unregister_sensor(self, sensor):
        async with self._lock:
            self._sensors.discard(sensor)
            
    async def cleanup(self):
        async with self._cleanup_lock:
            for sensor in list(self._sensors):
                await sensor.async_will_remove_from_hass()
            self._sensors.clear()

    async def async_close(self):
        try:
            await self.cleanup()
            self._sensors.clear()
            self._update_listeners.clear()
        except Exception:
            pass

async def setup_almanac_card(hass: HomeAssistant) -> bool:
    version = int(time.time())
    card_path = '/almanac_card-local'
    await hass.http.async_register_static_paths([
        StaticPathConfig(card_path, hass.config.path(f'custom_components/{DOMAIN}/www'), False)
    ])
    add_extra_js_url(hass, f"{card_path}/almanac-card.js?ver={version}")
    return True

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data[DOMAIN] = {}
    await setup_almanac_card(hass)
    await async_setup_date_service(hass)
    hass.http.register_view(AlmanacAPIView())
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Optional[AddEntitiesCallback] = None) -> bool:
    try:
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
        
        if "intents_registered" not in hass.data[DOMAIN]:
            from .intent import async_setup_intents
            await async_setup_intents(hass)
            hass.data[DOMAIN]["intents_registered"] = True
            
        if "registry_manager" not in hass.data[DOMAIN]:
            registry_manager = RegistryManager(hass)
            hass.data[DOMAIN]["registry_manager"] = registry_manager
        
        almanac_coordinator = AlmanacCoordinator(hass, entry)
        hass.data[DOMAIN][entry.entry_id] = {
            "almanac": almanac_coordinator,
            "config": dict(entry.data)
        }
        
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        entry.async_on_unload(entry.add_update_listener(update_listener))
        return True
    except Exception as e:
        raise ConfigEntryNotReady from e

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    try:
        if entry_data := hass.data[DOMAIN].get(entry.entry_id):
            old_config = dict(entry_data.get("config", {}))
            new_config = dict(entry.data)

            need_reload = (
                old_config.get(CONF_BIRTHDAY_ENABLED) != new_config.get(CONF_BIRTHDAY_ENABLED) or
                old_config.get(CONF_EVENT_ENABLED) != new_config.get(CONF_EVENT_ENABLED) or
                any(old_config.get(f"person{i}_name") != new_config.get(f"person{i}_name")
                    for i in range(1, MAX_BIRTHDAYS + 1)) or
                any(old_config.get(f"event{i}_name") != new_config.get(f"event{i}_name")
                    for i in range(1, MAX_EVENTS + 1))
            )

            if need_reload:
                if registry_manager := hass.data[DOMAIN].get("registry_manager"):
                    await registry_manager.cleanup_orphaned_entities(entry)

                entry_data["config"] = new_config
                await hass.config_entries.async_reload(entry.entry_id)
    except Exception as e:
        raise RuntimeError(f"更新监听器失败: {str(e)}") from e

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    registry = entity_registry.async_get(hass)
    entities = entity_registry.async_entries_for_config_entry(registry, entry.entry_id)
    for entity in entities:
            if state := hass.states.get(entity.entity_id):
                hass.states.async_remove(entity.entity_id)
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        if "registry_manager" in hass.data[DOMAIN]:
            await hass.data[DOMAIN]["registry_manager"].cleanup_all_entities(entry)
            
        if entry.entry_id in hass.data[DOMAIN]:
            coordinator = hass.data[DOMAIN][entry.entry_id].get("almanac")
            if coordinator:
                await coordinator.async_close()
            hass.data[DOMAIN].pop(entry.entry_id)
        
        if not hass.config_entries.async_entries(DOMAIN):
            if SERVICE_DATE_CONTROL in (hass.services.async_services().get(DOMAIN) or {}):
                hass.services.async_remove(DOMAIN, SERVICE_DATE_CONTROL)
            hass.data.pop(DOMAIN, None)
            
    return unload_ok

async def export_almanac_data(hass: HomeAssistant, entry_id: str = None) -> dict:
    if DOMAIN not in hass.data or "almanac_sensors" not in hass.data[DOMAIN]:
        return {"error": "未找到老黄历数据"}
    sensors = hass.data[DOMAIN]["almanac_sensors"]
    if entry_id:
        if entry_id not in sensors:
            return {"error": "未找到指定配置"}
        sensor_list = sensors[entry_id]
    else:
        all_sensors = []
        for s_list in sensors.values():
            all_sensors.extend(s_list)
        sensor_list = all_sensors
    result = {"timestamp": datetime.now().isoformat(), "data": {}}
    for sensor in sensor_list:
        if sensor._cleanup_called or not sensor._available:
            continue
        key = sensor._type
        value = {"state": sensor._state, "attributes": sensor._attributes if sensor._attributes else {}}
        if key not in result["data"]:
            result["data"][key] = value
    return result

class AlmanacAPIView(HomeAssistantView):
    url = "/api/chinese_calendar/data"
    name = "api:chinese_calendar:data"
    requires_auth = False
    
    async def get(self, request):
        hass = request.app["hass"]
        entry_id = request.query.get("entry_id")
        data = await export_almanac_data(hass, entry_id)
        return web.json_response(data)
