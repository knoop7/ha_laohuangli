import asyncio
import os
import shutil
import logging
import weakref
import time
from pathlib import Path
from typing import Dict, Set, Optional, List
from homeassistant.core import HomeAssistant
from homeassistant.util import yaml
from homeassistant.helpers import entity_registry
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.components.lovelace import DOMAIN as LOVELACE_DOMAIN
from homeassistant.components.frontend import add_extra_js_url
from .services import async_setup_date_service, SERVICE_DATE_CONTROL
from .const import (
    DOMAIN, 
    PLATFORMS, 
    CONF_BIRTHDAY_ENABLED,
    CONF_EVENT_ENABLED,
    MAX_BIRTHDAYS,
    MAX_EVENTS,
)
from .birthday_manager import setup_birthday_sensors
from .event_manager import setup_event_sensors
from .almanac_sensor import AlmanacSensor
from .moon import setup_almanac_moon_sensor

_LOGGER = logging.getLogger(__name__)


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
    
    async def cleanup_orphaned_entities(self, config_entry: ConfigEntry) -> None:
        async with self._cleanup_lock:
            try:
                async with asyncio.timeout(30):
                    self._entities.clear()
                    entities = entity_registry.async_entries_for_config_entry(
                        self._registry, config_entry.entry_id)
                    valid_entities = await self._get_valid_entities(config_entry)
                    
                    for entity in entities:
                        if ("birthday_" in entity.unique_id or "event_" in entity.unique_id):
                            if not any(entity.unique_id.endswith(valid_id) for valid_id in valid_entities):
                                self._registry.async_remove(entity.entity_id)
                            else:
                                self._entities[entity.unique_id] = entity.entity_id
            except Exception as e:
                raise RuntimeError(f"清理失败: {str(e)}") from e

    async def _get_valid_entities(self, config_entry: ConfigEntry) -> Set[str]:
        valid_entities = set()
        
        if config_entry.data.get(CONF_BIRTHDAY_ENABLED):
            for i in range(1, MAX_BIRTHDAYS + 1):
                name = config_entry.data.get(f"person{i}_name")
                if name:
                    valid_entities.add(f"birthday_{name.lower()}")

        if config_entry.data.get(CONF_EVENT_ENABLED):
            for i in range(1, MAX_EVENTS + 1):
                name = config_entry.data.get(f"event{i}_name")
                if name:
                    valid_entities.add(f"event_{name.lower()}")
                    
        return valid_entities

    async def _process_entity(self, entity, valid_entities: Set[str]) -> None:
        try:
            is_birthday = "birthday_" in entity.unique_id
            is_event = "event_" in entity.unique_id
            
            if is_birthday or is_event:
                if not any(entity.unique_id.endswith(valid_id) for valid_id in valid_entities):
                    self._registry.async_remove(entity.entity_id)
                else:
                    self._entities[entity.unique_id] = entity.entity_id
        except Exception as e:
            raise RuntimeError(f"处理实体失败: {str(e)}") from e

    async def cleanup_all_entities(self, config_entry: ConfigEntry) -> None:
        try:
            registry = entity_registry.async_get(self.hass)
            entities = entity_registry.async_entries_for_config_entry(registry, config_entry.entry_id)
            
            for entity in entities:
                if "birthday_" in entity.unique_id or "event_" in entity.unique_id:
                    registry.async_remove(entity.entity_id)
        except Exception as e:
            raise RuntimeError(f"清理所有实体失败: {str(e)}") from e

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
        except Exception as e:
            _LOGGER.error("关闭协调器时出错: %s", str(e))

async def setup_almanac_card(hass: HomeAssistant) -> bool:
    try:
        await hass.async_add_executor_job(lambda: shutil.copy2(
            Path(__file__).parent / "www" / "almanac-card.js",
            Path(hass.config.path("www")) / "almanac-card.js"
        ))
        return True
    except Exception:
        return False

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data[DOMAIN] = {}
    if await setup_almanac_card(hass):
        version = int(time.time())  
        add_extra_js_url(hass, f"/local/almanac-card.js?v={version}")  
    await async_setup_date_service(hass)
    return True
    return False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Optional[AddEntitiesCallback] = None) -> bool:
    try:
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}

        registry_manager = await _setup_registry_manager(hass, entry)
        
        if async_add_entities:
            entities = await _setup_entities(hass, entry)
            for entity in entities:
                if hasattr(entity, 'unique_id'):
                    registry_manager._entities[entity.unique_id] = entity.entity_id
            async_add_entities(entities, True)
        
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

async def _setup_registry_manager(hass: HomeAssistant, entry: ConfigEntry) -> RegistryManager:
    if registry_manager := hass.data[DOMAIN].get("registry_manager"):
        await registry_manager.cleanup_orphaned_entities(entry)
    else:
        registry_manager = RegistryManager(hass)
        hass.data[DOMAIN]["registry_manager"] = registry_manager
    return registry_manager

async def _setup_entities(hass: HomeAssistant, entry: ConfigEntry) -> List:
    entities = []
    
    if almanac_result := await setup_almanac_sensors(hass, entry.entry_id, entry.data):
        entities.extend(almanac_result[0])
        
    setup_functions = [
        setup_almanac_moon_sensor,
        setup_birthday_sensors,
        setup_event_sensors
    ]
    
    async with asyncio.TaskGroup() as tg:
        tasks = [
            tg.create_task(setup_func(hass, entry.entry_id, entry.data))
            for setup_func in setup_functions
        ]
        
    for task in tasks:
        if additional_entities := task.result():
            entities.extend(additional_entities)
            
    return entities

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