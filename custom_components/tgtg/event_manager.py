import logging
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers import entity_registry as er

from .const import (
    DOMAIN,
    EVENT_DATE_FORMAT,
)

_LOGGER = logging.getLogger(__name__)

class EventDevice:
    def __init__(self, entry_id: str):
        self._entry_id = entry_id

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry_id}_event")},
            name="事件管理",
            model="Event Tracker",
            manufacturer="道教",
        )

class EventSensor(SensorEntity):
    def __init__(self, device, event_name, event_date, event_desc, registry=None, entity_id=None, auto_remove=False, full_countdown=False, notification_service=None, notification_message=None, hass=None):
        self._device = device
        self._name = event_name
        self._entity_id = entity_id
        date_str = f"{event_date} 12/00" if len(event_date) <= 10 else event_date
        self._event_date = datetime.strptime(date_str, f"{EVENT_DATE_FORMAT} %H/%M")
        self._event_desc = event_desc
        self._state = None
        self._available = True
        self._attr_has_entity_name = True
        self._registry = registry
        self._should_remove = False
        self._auto_remove = auto_remove
        self._full_countdown = full_countdown
        self._notification_service = notification_service
        self._notification_message = notification_message
        self._attributes = {}
        self._update_interval = None
        self._next_update = None
        self._unsub_update = None
        self._hass = hass
        self._notification_sent = False
        self._last_update = None

    @property
    def unique_id(self):
        return f"event_{self._device._entry_id}_{self._name}"

    @property
    def entity_id(self):
        return self._entity_id
        
    @entity_id.setter
    def entity_id(self, value):
        self._entity_id = value

    @property
    def name(self):
        return self._name

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_update:
            self._unsub_update()

    @property
    def device_info(self):
        return self._device.device_info

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        if not self._event_date:
            return {
                "描述": self._event_desc,
                "自动删除": "开启" if self._auto_remove else "关闭",
                "完整倒计时": "开启" if self._full_countdown else "关闭",
                "通知服务": self._notification_service if self._notification_service else "关闭"
            }
        attrs = {
            "描述": self._event_desc,
            "日期": self._event_date.strftime(EVENT_DATE_FORMAT),
            "自动删除": "开启" if self._auto_remove else "关闭",
            "完整倒计时": "开启" if self._full_countdown else "关闭",
            "通知服务": self._notification_service if self._notification_service else "关闭"
        }
        attrs.update(self._attributes)
        return attrs

    @property
    def available(self):
        return self._available

    @property
    def icon(self):
        return 'mdi:calendar-clock'

    @property
    def should_remove(self):
        return self._should_remove


    def should_update(self) -> bool:
        now = dt.now().replace(tzinfo=None)
        if not self._next_update or now >= self._next_update:
            return True
        return False
    async def async_added_to_hass(self):
        await self.async_update()
        
        @callback
        async def _scheduled_update(now):
            await self.async_update()

        if self._full_countdown:
            update_interval = timedelta(milliseconds=100)  
        else:
            update_interval = self._calculate_update_interval()

        self._unsub_update = async_track_time_interval(
            self.hass,
            _scheduled_update,
            update_interval
        )

    def _calculate_update_interval(self):
        now = dt.now().replace(tzinfo=None)
        delta = self._event_date - now
        
        if not self._full_countdown:
            return timedelta(hours=1)
            
        if delta.days > 7:
            return timedelta(hours=1)
        elif delta.days > 1:
            return timedelta(minutes=15)
        elif delta.days == 1:
            return timedelta(minutes=5)
        else:
            return timedelta(seconds=1)

    def _format_countdown(self, delta):
        if not self._full_countdown:
            return f"还有{delta.days}天"
                
        total_seconds = int(delta.total_seconds())
        days = total_seconds // (24 * 3600)
        remaining_seconds = total_seconds % (24 * 3600)
        hours = remaining_seconds // 3600
        remaining_seconds %= 3600
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60

        if days > 0:
            return f"还有{days}天"
        
        parts = []
        if hours > 0:
            parts.append(f"{hours}时")
        if minutes > 0:
            parts.append(f"{minutes}分")
        if seconds > 0 or not parts:  
            parts.append(f"{seconds}秒")
        
        return "".join(parts)

    async def async_update(self):
        try:
            now = dt.now().replace(tzinfo=None)
            
            if self._last_update and (now - self._last_update).total_seconds() < 0.8:
                return
                
            self._last_update = now

            if not self._event_date:
                self._available = False
                return

            delta = self._event_date - now
            total_seconds = delta.total_seconds()

            if self._auto_remove and delta.days < -1:
                self._should_remove = True
                if self._registry and self._entity_id:
                    try:
                        await self._registry.async_remove(self._entity_id)
                    except Exception as e:
                        _LOGGER.error("删除实体失败: %s", e)
                self._available = False
                return

            if total_seconds <= -86400:  
                self._state = "已过期"
            elif self._full_countdown:
                if -3600 < total_seconds <= 0:
                    self._state = "已到时间"
                    await self._handle_notification()
                elif total_seconds > 0:
                    self._state = self._format_countdown(delta)
                    self._notification_sent = False
                else:
                    self._state = "已过期"
            else:
                if delta.days == 0:
                    self._state = "今天"
                    await self._handle_notification()
                elif total_seconds <= 0:
                    self._state = "已过期"
                else:
                    self._state = f"还有{delta.days}天"
                    self._notification_sent = False

            self._available = True

        except Exception as e:
            _LOGGER.error("更新事件传感器时出错: %s", e)
            self._available = False

    async def _handle_notification(self):
        if (self._notification_service and 
            self._notification_message and 
            self._hass and 
            not self._notification_sent):
            try:
                service_data = {
                    "title": "中国老黄历 · Home Assistant",
                    "message": self._notification_message
                }
                await self._hass.services.async_call(
                    "notify",
                    self._notification_service,
                    service_data
                )
                self._notification_sent = True
            except Exception as e:
                _LOGGER.error("发送通知失败: %s", e)
                
async def setup_event_sensors(hass: HomeAssistant, entry_id: str, config_data: dict):
    entities = []
    registry = er.async_get(hass)
    
    existing_entries = er.async_entries_for_config_entry(registry, entry_id)
    for entry in existing_entries:
        if entry.unique_id and entry.unique_id.startswith(f"event_{entry_id}_"):
            try:
                if registry.async_get(entry.entity_id):
                    registry.async_remove(entry.entity_id)
                    if state := hass.states.get(entry.entity_id):
                        hass.states.async_remove(entry.entity_id)
            except Exception as e:
                _LOGGER.error(f"删除实体失败 {entry.entity_id}: {str(e)}")

    if not config_data.get("event_enabled", False):
        return entities

    event_device = EventDevice(entry_id)
    event_count = 1
    
    while True:
        name_key = f"event{event_count}_name"
        date_key = f"event{event_count}_date"
        
        if name_key not in config_data or date_key not in config_data:
            break
            
        try:
            name = config_data.get(name_key)
            sensor_id = f"sensor.event_{name.lower()}"
            event_sensor = EventSensor(
                device=event_device,
                event_name=name,
                event_date=config_data.get(date_key),
                event_desc=config_data.get(f"event{event_count}_desc", ""),
                auto_remove=config_data.get(f"event{event_count}_auto_remove", False),
                full_countdown=config_data.get(f"event{event_count}_full_countdown", False),
                notification_service=config_data.get(f"event{event_count}_notification_service"),
                notification_message=config_data.get(f"event{event_count}_notification_message"),
                registry=registry,
                entity_id=sensor_id,
                hass=hass
            )

            if registry and (unique_id := event_sensor.unique_id):
                if existing := registry.async_get_entity_id("sensor", DOMAIN, unique_id):
                    registry.async_update_entity(
                        existing,
                        new_entity_id=sensor_id,
                        new_unique_id=unique_id
                    )
                    
            entities.append(event_sensor)
            
        except Exception as e:
            _LOGGER.error(f"无法创建事件传感器 {config_data.get(name_key, '')}: {str(e)}")
        
        event_count += 1

    return entities