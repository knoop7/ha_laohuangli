import asyncio
import os
import shutil
from datetime import timedelta
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
from .almanac_sensor import setup_almanac_sensors
from .moon import setup_almanac_moon_sensor

class TaskManager:
    def __init__(self):
        self._tasks: Set[asyncio.Task] = set()
        self._lock = asyncio.Lock()
    
    async def create_task(self, coro) -> asyncio.Task:
        async with self._lock:
            task = asyncio.create_task(coro)
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            return task
    
    async def cancel_all(self):
        async with self._lock:
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*self._tasks, return_exceptions=True)

class RegistryManager:
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self._registry = entity_registry.async_get(hass)
        self._cleanup_lock = asyncio.Lock()
        self._entities: Dict[str, str] = {}
        self._task_manager = TaskManager()
    
    async def cleanup_orphaned_entities(self, config_entry: ConfigEntry) -> None:
        async with self._cleanup_lock:
            entities_backup = self._entities.copy()
            try:
                await self._do_cleanup(config_entry)
            except Exception:
                self._entities = entities_backup
                raise
    
    async def _do_cleanup(self, config_entry: ConfigEntry) -> None:
        try:
            self._entities.clear()
            entities = entity_registry.async_entries_for_config_entry(
                self._registry, 
                config_entry.entry_id
            )
            valid_entities = await self._get_valid_entities(config_entry)
            
            for entity in entities:
                await self._process_entity(entity, valid_entities)
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
        self.hass = hass
        self.entry = entry
        self.entry_id = entry.entry_id
        self._update_lock = asyncio.Lock()
        self._task_manager = TaskManager()
        self._closing = asyncio.Event()
        self.nine_flying_stars_entity = None
    
    async def async_update_flying_stars(self):
        if self._closing.is_set():
            return
            
        async with self._update_lock:
            if self.nine_flying_stars_entity:
                await asyncio.wait_for(
                    self.nine_flying_stars_entity._get_flying_stars(),
                    timeout=10.0
                )
                self.nine_flying_stars_entity.async_write_ha_state()
    
    async def async_close(self):
        self._closing.set()
        await self._task_manager.cancel_all()

async def setup_almanac_card(hass: HomeAssistant) -> bool:
    try:
        await hass.async_add_executor_job(lambda: shutil.copy2(
            Path(__file__).parent / "www" / "almanac-card.js",
            Path(hass.config.path("www")) / "almanac-card.js"
        ))
        return True
    except Exception:
        return False

def merge_recorder_config(hass: HomeAssistant) -> None:
    config_path = os.path.join(hass.config.config_dir, "configuration.yaml")
    backup_path = os.path.join(hass.config.config_dir, "configuration.yaml.backup")
    try:
        default_recorder = """recorder:
  exclude:
    domains:
      - almanac
    entity_globs:
      - sensor.zhong_guo_lao_huang_li_*
      - sensor.lao_huang_li_*
      - sensor.*_huang_li_*"""

        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as fsrc, open(backup_path, 'w', encoding='utf-8') as fdst:
                content = fsrc.read()
                fdst.write(content)
                
            if 'recorder:' not in content:
                with open(config_path, 'a', encoding='utf-8') as f:
                    if content and not content.endswith('\n'):
                        f.write('\n')
                    if content:
                        f.write('\n')
                    f.write(default_recorder)
                    return
                    
            lines = content.splitlines()
            need_save = False
            recorder_indent = None
            exclude_indent = None
            domains_indent = None
            entity_globs_indent = None
            
            for i, line in enumerate(lines):
                if 'recorder:' in line and line.strip() == 'recorder:':
                    recorder_indent = len(line) - len(line.lstrip())
                    if i + 1 >= len(lines) or not lines[i + 1].strip():
                        lines.insert(i + 1, ' ' * (recorder_indent + 2) + 'exclude:')
                        lines.insert(i + 2, ' ' * (recorder_indent + 4) + 'domains:')
                        lines.insert(i + 3, ' ' * (recorder_indent + 6) + '- almanac')
                        lines.insert(i + 4, ' ' * (recorder_indent + 4) + 'entity_globs:')
                        for pattern in ["sensor.zhong_guo_lao_huang_li_*", "sensor.lao_huang_li_*", "sensor.*_huang_li_*"]:
                            lines.insert(i + 5, ' ' * (recorder_indent + 6) + f'- {pattern}')
                        need_save = True
                        break
                elif 'exclude:' in line and recorder_indent is not None:
                    exclude_indent = len(line) - len(line.lstrip())
                elif 'domains:' in line and exclude_indent is not None:
                    domains_indent = len(line) - len(line.lstrip())
                    if 'almanac' not in content:
                        for j, next_line in enumerate(lines[i+1:], i+1):
                            if len(next_line.strip()) == 0 or len(next_line) - len(next_line.lstrip()) <= domains_indent:
                                lines.insert(j, ' ' * (domains_indent + 2) + '- almanac')
                                need_save = True
                                break
                elif 'entity_globs:' in line and exclude_indent is not None:
                    entity_globs_indent = len(line) - len(line.lstrip())
                    patterns = ["sensor.zhong_guo_lao_huang_li_*", "sensor.lao_huang_li_*", "sensor.*_huang_li_*"]
                    for pattern in patterns:
                        if pattern not in content:
                            for j, next_line in enumerate(lines[i+1:], i+1):
                                if len(next_line.strip()) == 0 or len(next_line) - len(next_line.lstrip()) <= entity_globs_indent:
                                    lines.insert(j, ' ' * (entity_globs_indent + 2) + f'- {pattern}')
                                    need_save = True
                                    break
            
            if need_save:
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
        else:
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(default_recorder)
            
        if os.path.exists(backup_path):
            os.remove(backup_path)
    except Exception as e:
        if os.path.exists(backup_path):
            try:
                with open(backup_path, 'r', encoding='utf-8') as fsrc, open(config_path, 'w', encoding='utf-8') as fdst:
                    fdst.write(fsrc.read())
            except: pass
            try: os.remove(backup_path)
            except: pass
        raise RuntimeError(f"配置文件修改失败: {str(e)}") from e


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data[DOMAIN] = {}
    await hass.async_add_executor_job(merge_recorder_config, hass)
    if await setup_almanac_card(hass):
        add_extra_js_url(hass, "/local/almanac-card.js")
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
