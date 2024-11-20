import logging
import asyncio
import os
import shutil
from datetime import timedelta
from pathlib import Path
from typing import Dict, Set, Optional, List, Tuple, Any
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.components.lovelace import DOMAIN as LOVELACE_DOMAIN
from homeassistant.components.frontend import add_extra_js_url
from .services import async_setup_date_service, SERVICE_DATE_CONTROL
from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_GUANYIN_ENABLED,
    CONF_BIRTHDAY_ENABLED,
    CONF_EVENT_ENABLED,
    MAX_BIRTHDAYS,
    MAX_EVENTS,
)
from .birthday_manager import setup_birthday_sensors
from .event_manager import setup_event_sensors
from .almanac_sensor import setup_almanac_sensors
from .moon import setup_almanac_moon_sensor

_LOGGER = logging.getLogger(__name__)

class RegistryManager:
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self._registry = entity_registry.async_get(hass)
        self._cleanup_lock = asyncio.Lock()
        self._existing_entities: Dict[str, str] = {}
        self._active_entities: Set[str] = set()
        self.config_data = {}
        self._timeout = 30

    async def reset(self):
        try:
            async with asyncio.timeout(self._timeout):
                async with self._cleanup_lock:
                    self._existing_entities.clear()
                    self._active_entities.clear()
                    self.config_data.clear()
        except asyncio.TimeoutError:
            self._existing_entities.clear()
            self._active_entities.clear()
            self.config_data.clear()

    async def cleanup_orphaned_entities(self, config_entry: ConfigEntry) -> None:
        try:
            async with asyncio.timeout(self._timeout):
                async with self._cleanup_lock:
                    self.config_data = dict(config_entry.data)
                    entities = entity_registry.async_entries_for_config_entry(
                        self._registry, config_entry.entry_id
                    )
                    valid_entities = await self._get_valid_entities()
                    
                    for entity in entities:
                        if entity.unique_id:
                            await self._process_entity(entity, valid_entities)

        except asyncio.TimeoutError:
            await self.reset()
            raise ConfigEntryNotReady("注册表清理超时")
        except Exception as e:
            await self.reset()
            raise ConfigEntryNotReady(f"注册表清理失败： {str(e)}")

    async def _get_valid_entities(self) -> Set[str]:
        valid_entities = set()
        
        valid_entities.add("guanyin_sign")
        valid_entities.add("guanyin_image") 

        if self.config_data.get(CONF_BIRTHDAY_ENABLED, False):
            for i in range(1, MAX_BIRTHDAYS + 1):
                name = self.config_data.get(f"person{i}_name")
                if name:
                    valid_entities.add(f"birthday_{name.lower()}")
        
        if self.config_data.get(CONF_EVENT_ENABLED, False):
            for i in range(1, MAX_EVENTS + 1):
                name = self.config_data.get(f"event{i}_name")
                if name:
                    valid_entities.add(f"event_{name.lower()}")
                    
        return valid_entities

    async def _process_entity(self, entity: Any, valid_entities: Set[str]) -> None:

        if entity.unique_id and entity.unique_id.startswith("guanyin_"):
            self._existing_entities[entity.unique_id] = entity.entity_id
            self._active_entities.add(entity.unique_id)
            return
            
        if not any(entity.unique_id.endswith(valid_id) for valid_id in valid_entities):
            self._registry.async_remove(entity.entity_id)
            self._existing_entities.pop(entity.unique_id, None)
        else:
            self._existing_entities[entity.unique_id] = entity.entity_id
            self._active_entities.add(entity.unique_id)

    def register_entity(self, identifier: str) -> None:
        if identifier:
            self._existing_entities[identifier] = True
            self._active_entities.add(identifier)

class GuanyinCoordinator:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry
        self.entry_id = entry.entry_id
        self.image_entity = None
        self.enabled = entry.data.get(CONF_GUANYIN_ENABLED, False)
        
    async def async_update_sign(self):
        if self.enabled and self.image_entity:
            try:
                async with asyncio.timeout(10):
                    await self.image_entity.async_update_sign()
            except asyncio.TimeoutError:
                pass

class AlmanacCoordinator:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry
        self.entry_id = entry.entry_id
        self.nine_flying_stars_entity = None
        self.image_entity = None
        
    async def async_update_flying_stars(self):
        if self.nine_flying_stars_entity:
            try:
                async with asyncio.timeout(10):
                    await self.nine_flying_stars_entity._get_flying_stars()
                    self.nine_flying_stars_entity.async_write_ha_state()
            except asyncio.TimeoutError:
                pass

async def setup_guanyin_files(hass: HomeAssistant) -> bool:
    www_dir = Path(hass.config.path("www")) / "guanyin"
    guanyin_src = Path(__file__).parent / "guanyin"
    backup_dir = None
    
    try:
        async with asyncio.timeout(30):
            if www_dir.exists():
                backup_dir = www_dir.with_suffix('.bak')
                await hass.async_add_executor_job(shutil.copytree, www_dir, backup_dir)
            
            def _copy_files():
                if not os.path.exists(www_dir):
                    shutil.copytree(guanyin_src, www_dir)
                else:
                    for item in os.listdir(guanyin_src):
                        s = os.path.join(guanyin_src, item)
                        d = os.path.join(www_dir, item)
                        if os.path.isfile(s):
                            shutil.copy2(s, d)
                            
            await hass.async_add_executor_job(_copy_files)
            if backup_dir and backup_dir.exists():
                await hass.async_add_executor_job(shutil.rmtree, backup_dir)
            return True
            
    except Exception:
        if backup_dir and backup_dir.exists():
            if www_dir.exists():
                await hass.async_add_executor_job(shutil.rmtree, www_dir)
            await hass.async_add_executor_job(shutil.move, backup_dir, www_dir)
        return False

async def setup_almanac_card(hass: HomeAssistant) -> bool:
    src_file = Path(__file__).parent / "www" / "almanac-card.js"
    dst_file = Path(hass.config.path("www")) / "almanac-card.js"
    backup_file = None
    
    try:
        async with asyncio.timeout(30):
            if dst_file.exists():
                backup_file = dst_file.with_suffix('.bak')
                await hass.async_add_executor_job(shutil.copy2, dst_file, backup_file)
                
            def _copy_file():
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                shutil.copy2(src_file, dst_file)
                
            await hass.async_add_executor_job(_copy_file)
            if backup_file and backup_file.exists():
                await hass.async_add_executor_job(os.remove, backup_file)
            return True
            
    except Exception:
        if backup_file and backup_file.exists():
            if dst_file.exists():
                await hass.async_add_executor_job(os.remove, dst_file)
            await hass.async_add_executor_job(shutil.move, backup_file, dst_file)
        return False

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    try:
        async with asyncio.timeout(30):
            hass.data[DOMAIN] = {}
            await setup_almanac_card(hass)
            js_url = "/local/almanac-card.js"
            
            if LOVELACE_DOMAIN in hass.data and "dashboards" in hass.data[LOVELACE_DOMAIN]:
                await hass.services.async_call("frontend", "set_theme", {"name": "default", "mode": "light"})
                
            add_extra_js_url(hass, js_url)
            await async_setup_date_service(hass)
            return True
            
    except Exception:
        return False

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback = None) -> bool:
    try:
        async with asyncio.timeout(60):
            if DOMAIN not in hass.data:
                hass.data[DOMAIN] = {}
                
            if "registry_manager" not in hass.data[DOMAIN]:
                hass.data[DOMAIN]["registry_manager"] = RegistryManager(hass)
                
            registry_manager = hass.data[DOMAIN]["registry_manager"]
            await registry_manager.reset()
            await registry_manager.cleanup_orphaned_entities(entry)
            
            if async_add_entities:
                entities = await setup_entities(hass, entry, registry_manager)
                if entities:
                    async_add_entities(entities, True)

            coordinators = await setup_coordinators(hass, entry)
            hass.data[DOMAIN][entry.entry_id] = {
                "config": entry.data,
                "entities": {},
                **coordinators,
                "registry_manager": registry_manager
            }

            if entry.data.get(CONF_GUANYIN_ENABLED, False):
                await setup_guanyin_files(hass)
                
            enabled_platforms = get_enabled_platforms(entry)
            await hass.config_entries.async_forward_entry_setups(entry, enabled_platforms)
            entry.async_on_unload(entry.add_update_listener(update_listener))
            return True
            
    except asyncio.TimeoutError:
        raise ConfigEntryNotReady("Setup timed out")
    except Exception as err:
        raise ConfigEntryNotReady from err

async def setup_entities(hass: HomeAssistant, entry: ConfigEntry, registry_manager: RegistryManager) -> List[Any]:
    entities = []
    setup_tasks = [
        (setup_almanac_sensors, True),
        (setup_almanac_moon_sensor, False),
        (setup_birthday_sensors, False),
        (setup_event_sensors, False)
    ]
    
    results = await asyncio.gather(
        *[setup_func(hass, entry.entry_id, entry.data) for setup_func, _ in setup_tasks],
        return_exceptions=True
    )
    
    for result, (_, has_extra_data) in zip(results, setup_tasks):
        if isinstance(result, Exception):
            continue
            
        if has_extra_data and result:
            entities.extend(result[0])
            hass.data[DOMAIN].setdefault("almanac_sensors", {})[entry.entry_id] = result[1]
        elif result:
            entities.extend(result)
            
    for entity in entities:
        if hasattr(entity, 'unique_id'):
            registry_manager.register_entity(entity.unique_id)
            
    return entities

async def setup_coordinators(hass: HomeAssistant, entry: ConfigEntry) -> Dict[str, Any]:
    return {
        "coordinator": GuanyinCoordinator(hass, entry),
        "almanac_coordinator": AlmanacCoordinator(hass, entry)
    }

def get_enabled_platforms(entry: ConfigEntry) -> List[str]:
    return [
        platform for platform in PLATFORMS
        if not platform.startswith('guanyin_') or
        (platform.startswith('guanyin_') and entry.data.get(CONF_GUANYIN_ENABLED, False))
    ]

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    try:
        async with asyncio.timeout(30):
            old_entry = hass.data[DOMAIN][entry.entry_id]
            old_guanyin_enabled = old_entry.get("coordinator").enabled
            new_guanyin_enabled = entry.data.get(CONF_GUANYIN_ENABLED, False)
            
            if new_guanyin_enabled and not old_guanyin_enabled:
                await setup_guanyin_files(hass)
            
            if "registry_manager" in hass.data[DOMAIN]:
                await hass.data[DOMAIN]["registry_manager"].reset()
            
            await hass.config_entries.async_reload(entry.entry_id)
    except asyncio.TimeoutError:
        pass

async def cleanup_frontend_files(hass: HomeAssistant) -> None:
    try:
        async with asyncio.timeout(30):
            www_dir = Path(hass.config.path("www"))
            guanyin_dir = www_dir / "guanyin"
            almanac_card = www_dir / "almanac-card.js"
            
            def _remove_files():
                if os.path.exists(guanyin_dir):
                    shutil.rmtree(guanyin_dir)
                if os.path.exists(almanac_card):
                    os.remove(almanac_card)
            
            await hass.async_add_executor_job(_remove_files)
    except (asyncio.TimeoutError, Exception):
        pass
    
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    try:
        async with asyncio.timeout(30):
            enabled_platforms = get_enabled_platforms(entry)
            unload_ok = await hass.config_entries.async_unload_platforms(entry, enabled_platforms)
            
            if unload_ok:
                registry = entity_registry.async_get(hass)
                entities = entity_registry.async_entries_for_config_entry(registry, entry.entry_id)
                
                for entity in entities:
                    registry.async_remove(entity.entity_id)
                
                hass.data[DOMAIN].pop(entry.entry_id, None)
                
                if not hass.config_entries.async_entries(DOMAIN):
                    if SERVICE_DATE_CONTROL in (hass.services.async_services().get(DOMAIN) or {}):
                        hass.services.async_remove(DOMAIN, SERVICE_DATE_CONTROL)
                    hass.data.pop(DOMAIN, None)
                    await cleanup_frontend_files(hass)
            
            return unload_ok
            
    except asyncio.TimeoutError:
        return False
    except Exception:
        return False
