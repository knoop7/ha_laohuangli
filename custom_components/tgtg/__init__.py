import logging
import asyncio
import os
import shutil
from pathlib import Path
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, PLATFORMS, CONF_GUANYIN_ENABLED

_LOGGER = logging.getLogger(__name__)

class GuanyinCoordinator:
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.entry_id = entry.entry_id
        self.image_entity = None
        self.enabled = entry.data.get(CONF_GUANYIN_ENABLED, False)

    async def async_update_sign(self):
        if self.enabled and self.image_entity:
            await self.image_entity.async_update_sign()

class AlmanacCoordinator:
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.entry_id = entry.entry_id
        self.nine_flying_stars_entity = None
        self.image_entity = None

    async def async_update_flying_stars(self):
        if self.nine_flying_stars_entity:
            await self.nine_flying_stars_entity._get_flying_stars()
            self.nine_flying_stars_entity.async_write_ha_state()

async def setup_guanyin_files(hass: HomeAssistant) -> bool:
    www_dir = Path(hass.config.path("www")) / "guanyin"
    guanyin_src = Path(__file__).parent / "guanyin"
    
    try:
        def _copy_files():
            shutil.copytree(guanyin_src, www_dir, dirs_exist_ok=True)
        await hass.async_add_executor_job(_copy_files)
        _LOGGER.debug("观音文件复制成功！福德增加一次！")
        return True
    except Exception as e:
        _LOGGER.error(f"复制观音文件失败！福德减少一次！: {str(e)}")
        return False

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data[DOMAIN] = {}
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    
    guanyin_coordinator = GuanyinCoordinator(hass, entry)
    almanac_coordinator = AlmanacCoordinator(hass, entry)
    
    hass.data[DOMAIN][entry.entry_id] = {
        "config": entry.data,
        "entities": {},
        "coordinator": guanyin_coordinator,
        "almanac_coordinator": almanac_coordinator
    }

    if entry.data.get(CONF_GUANYIN_ENABLED, False):
        await setup_guanyin_files(hass)

    enabled_platforms = []
    for platform in PLATFORMS:
        if platform.startswith('guanyin_'):
            if entry.data.get(CONF_GUANYIN_ENABLED, False):
                enabled_platforms.append(platform)
        else:
            enabled_platforms.append(platform)

    await hass.config_entries.async_forward_entry_setups(entry, enabled_platforms)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    old_entry = hass.data[DOMAIN][entry.entry_id]
    old_guanyin_enabled = old_entry.get("coordinator").enabled
    new_guanyin_enabled = entry.data.get(CONF_GUANYIN_ENABLED, False)
    
    if new_guanyin_enabled and not old_guanyin_enabled:
        await setup_guanyin_files(hass)
    
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    enabled_platforms = []
    for platform in PLATFORMS:
        if platform.startswith('guanyin_'):
            if entry.data.get(CONF_GUANYIN_ENABLED, False):
                enabled_platforms.append(platform)
        else:
            enabled_platforms.append(platform)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, enabled_platforms)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok