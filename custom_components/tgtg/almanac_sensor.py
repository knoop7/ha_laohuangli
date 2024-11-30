import logging,asyncio,re
from datetime import datetime,timedelta
from functools import lru_cache
from typing import Any,Dict,Optional,List
from collections import defaultdict
import cnlunar
from weakref import WeakValueDictionary
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant,callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo,EntityCategory
from .const import DOMAIN,MAIN_SENSORS
from .services import async_setup_date_service

_LOGGER = logging.getLogger(__name__)

class TextProcessor:
    _FILTERS={'上表章','上册','颁诏','修置产室','举正直','选将','宣政事','冠带','上官','临政','竖柱上梁','修仓库','营建','穿井','伐木','畋猎','招贤','酝酿','乘船渡水','解除','缮城郭','筑堤防','修宫室','安碓硙','纳采','针刺','开渠','平治道涂','裁制','修饰垣墙','塞穴','庆赐','破屋坏垣','鼓铸','启攒','开仓','纳畜','牧养','经络','安抚边境','选将','布政事','覃恩','雪冤','出师'}
    _TEXT_PATTERN=re.compile(r'\[.*?\]|[,;，；]')
    @staticmethod
    def clean_text(text): return ' '.join(w for w in TextProcessor._TEXT_PATTERN.sub(' ',text).split() if w not in TextProcessor._FILTERS).strip()
    @staticmethod
    def format_lucky_gods(data): return ' '.join(data) if isinstance(data,list) else ' '.join(f"{k}:{v}" for k,v in data.items()) if isinstance(data,dict) else str(data)
    @staticmethod
    def format_dict(data): return ' '.join(f"{k}{v}" for k,v in data.items()) if isinstance(data,dict) else str(data)
class TimeHelper:
    SHICHEN=('子时','丑时','寅时','卯时','辰时','巳时','午时','未时','申时','酉时','戌时','亥时')
    MARKS=('初','一','二','三','四','五','六','七')
    TIME_RANGES=('23:00-01:00','01:00-03:00','03:00-05:00','05:00-07:00','07:00-09:00','09:00-11:00','11:00-13:00','13:00-15:00','15:00-17:00','17:00-19:00','19:00-21:00','21:00-23:00')
    @staticmethod
    def get_current_shichen(h,m):i=0 if h==23 else(h+1)//2%12;start_hour=23 if h==23 else(h//2)*2+1;total_mins=(h-start_hour)*60+m;k=total_mins//15;return f"{TimeHelper.SHICHEN[i]}{'初' if k==0 else TimeHelper.MARKS[min(7,k)]}刻"
    @staticmethod
    def get_current_twohour(h):return 11 if h==23 else((h+1)//2)%12
    @staticmethod
    def format_twohour_lucky(l,t): i=TimeHelper.get_current_twohour(t.hour);return{'state':f"{TimeHelper.TIME_RANGES[i]} {l[i]}",'attributes':dict(zip(TimeHelper.TIME_RANGES,l))}
class AlmanacDevice:
    def __init__(self,entry_id,name):
        self._entry_id,self._name=entry_id,name
        self._holiday_cache={}
        self._workday_cache={}
        self._custom_cache={}   
    async def async_setup(self,hass):
        import yaml,os
        
        def load_yaml_file(path):
            with open(path,'r',encoding='utf-8') as f:
                return yaml.safe_load(f)
        yaml_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'tgtg','hworkdays.yaml')
        data=await hass.async_add_executor_job(load_yaml_file,yaml_path)
        self._holiday_cache=data.get('holidays',{})
        self._workday_cache=data.get('workdays',{})
        self._custom_cache=data.get('customdays',{})  
    @property
    def device_info(self): return DeviceInfo(identifiers={(DOMAIN,self._entry_id)},name=self._name,model="Chinese Almanac",manufacturer="道教")   
    def get_holiday(self,date_str,cnlunar_holidays): return next((v for d in(self._holiday_cache,self._workday_cache,self._custom_cache)if date_str in d for v in[d[date_str]]),cnlunar_holidays or"暂无节日")
class UpdateManager:
    def __init__(self):
        self._lock=asyncio.Lock()
        self._last_update={}
        self._pending_tasks=0
        self._max_pending=3
        self._cleanup_task=None
        self._lunar_cleanup_task=None
        self._task_running=False
        
    async def start(self):
        if self._pending_tasks < self._max_pending and not self._task_running:
            self._task_running=True
            self._cleanup_task=asyncio.create_task(self._periodic_cleanup())
            self._lunar_cleanup_task=asyncio.create_task(self._lunar_cleanup())
            self._pending_tasks += 2
            
    async def _periodic_cleanup(self):
        try:
            while self._task_running:
                await asyncio.sleep(3600)
                if not self._task_running:break
                async with self._lock:self._last_update.clear()
        finally:
            self._pending_tasks -= 1
                
    async def _lunar_cleanup(self):
        try:
            while self._task_running:
                await asyncio.sleep(300)
                if not self._task_running:break
                async with AlmanacSensor._cache_lock:AlmanacSensor._shared_lunar_cache.clear()
        finally:
            self._pending_tasks -= 1
                
    async def stop(self):
        self._task_running=False
        if self._cleanup_task:self._cleanup_task.cancel()
        if self._lunar_cleanup_task:self._lunar_cleanup_task.cancel()
            
    async def can_update(self,sensor_type):
        if self._pending_tasks >= self._max_pending:return False
        last=self._last_update.get(sensor_type)
        if not last or(datetime.now()-last)>=timedelta(seconds=5):
            self._last_update[sensor_type]=datetime.now()
            return True
        return False

class AlmanacSensor(SensorEntity):
    _shared_lunar_cache = WeakValueDictionary()
    _cache_lock = asyncio.Lock()
    _twelve_gods_cache = {}  
    _twelve_gods_lock = asyncio.Lock() 


    def __init__(self,device,name,sensor_type,is_main_sensor,hass):  
        super().__init__() 
        self._device,self._type,self._hass,self._is_main_sensor=device,sensor_type,hass,is_main_sensor
        self._state=self._last_state=self._last_update=self._custom_date=self._custom_date_set_time=None
        self._attributes,self._available,self._cleanup_called,self._updating={},True,False,False
        self._attr_has_entity_name=True
        self._update_lock=asyncio.Lock()
        self._text_processor,self._time_helper=TextProcessor(),TimeHelper()

    @classmethod
    async def _get_lunar_data(cls,date):
        now=datetime.now();key=date.strftime('%Y-%m-%d_%H')
        async with cls._cache_lock:
            if key in cls._shared_lunar_cache:return cls._shared_lunar_cache[key]
            try:data=cnlunar.Lunar(date,godType='8char');cls._shared_lunar_cache[key]=data;return data
            except Exception as e:_LOGGER.error(f"计算数据时出错: {e}");return None

    @property
    def name(self): return self._type
    @property 
    def unique_id(self): return f"{self._device._entry_id}_{self._type}"
    @property 
    def device_info(self): return self._device.device_info
    @property 
    def entity_category(self): return None if self._is_main_sensor else EntityCategory.DIAGNOSTIC
    @property 
    def state(self): return self._state
    @property 
    def extra_state_attributes(self): return self._attributes if self._type in['时辰凶吉','时辰','节气','九宫飞星','十二神']else{}
    @property 
    def available(self): return self._available
    @property 
    def icon(self): return'mdi:calendar-text'

    async def _get_current_time(self):
        return dt.as_local(self._custom_date).replace(tzinfo=None) if(self._custom_date and self._custom_date_set_time and(datetime.now()-self._custom_date_set_time).total_seconds()<60)else dt.as_local(dt.now()).replace(tzinfo=None)

    async def async_update(self):
        if self._cleanup_called:return
        try:
            async with self._update_lock:
                self._updating=True
                current_time=await self._get_current_time()
                update_map={'时辰凶吉':self._update_twohour_lucky,'时辰':self._update_double_hour}
                new_state=await(update_map.get(self._type,self._update_general))(current_time)
                if new_state!=self._last_state:self._state=self._last_state=new_state;self._available=True;self._last_update=datetime.now()
        except Exception as e:
            _LOGGER.error(f"更新传感器时出错 {self._type}: {e}")
            self._available=False

        finally:
            self._updating=False


    async def cleanup(self):
        if self._cleanup_called:return
        try:
            self._cleanup_called=True
            async with self._update_lock:
                self._attributes.clear()
                self._state=None
                self._device=self._hass=self._text_processor=self._time_helper=None
                self._available=False
        except Exception as e:
            _LOGGER.error(f"清理时出错: {e}")

    async def _update_double_hour(self,now):
        try: self._state=self._time_helper.get_current_shichen(now.hour,now.minute);self._available=True;return self._state
        except: self._available=False;return None

    async def _update_twohour_lucky(self,now):
        try:
            lunar_data=await self._get_lunar_data(now)
            if lunar_data:
                lucky_data=self._time_helper.format_twohour_lucky(lunar_data.get_twohourLuckyList(),now)
                self._state,self._attributes,self._available=lucky_data['state'],lucky_data['attributes'],True;return self._state
            self._available=False;return None
        except: self._available=False;return None

    async def _process_solar_terms(self,solar_terms_dict,current_month,current_day):
        terms=sorted(solar_terms_dict.items(),key=lambda x:(x[1][0],x[1][1]))
        for i,(term,(month,day)) in enumerate(terms):
            if i==len(terms)-1 and(month<current_month or(month==current_month and day<=current_day)): return term,terms[0][0],f"{terms[0][1][0]}月{terms[0][1][1]}日"
            elif((month<current_month)or(month==current_month and day<=current_day))and((terms[i+1][1][0]>current_month)or(terms[i+1][1][0]==current_month and terms[i+1][1][1]>current_day)): return term,terms[i+1][0],f"{terms[i+1][1][0]}月{terms[i+1][1][1]}日"
            elif i==0 and(month>current_month or(month==current_month and day>current_day)): return terms[-1][0],term,f"{month}月{day}日"
        return"","",""

    async def set_date(self,new_date): 
        self._custom_date,self._custom_date_set_time=new_date,datetime.now()
        await self.async_update();self.async_write_ha_state()

    async def _update_general(self,now):
        try:
            lunar_data=await self._get_lunar_data(now)
            if not lunar_data: 
                self._available=False
                return None
            formatted_date=now.strftime('%Y-%m-%d')
            if self._type == '十二神':
                async with self._twelve_gods_lock:
                    cached = self._twelve_gods_cache.get(formatted_date)  
                    current_time = datetime.now().timestamp()
                    
                    if cached and (current_time - cached[0]) < 86400:
                        self._state = cached[1]
                    else:
                        gods = self._text_processor.clean_text(' '.join(lunar_data.get_today12DayOfficer()))
                        self._twelve_gods_cache[formatted_date] = (current_time, gods)
                        self._state = gods
                        
                        old_dates = [d for d in self._twelve_gods_cache if d != formatted_date]
                        for d in old_dates:
                            self._twelve_gods_cache.pop(d, None)
                            
                    self._available = True
                    return self._state
            lunar_holidays_str=self._text_processor.clean_text(''.join(lunar_data.get_legalHolidays()+lunar_data.get_otherHolidays()+lunar_data.get_otherLunarHolidays()))
            numbers=self._text_processor.clean_text(self._text_processor.format_dict(lunar_data.get_the9FlyStar()))
            nine_palace_attrs={}
            if numbers.isdigit() and len(numbers)==9:
                P=('西北乾','北坎','东北艮','西兑','中宫','东震','西南坤','南离','东南巽')
                PS=('西北','正北','东北','正西','中宫','正东','西南','正南','东南')
                SC={'1':'白','2':'黑','3':'碧','4':'绿','5':'黄','6':'白','7':'赤','8':'白','9':'紫'}
                nine_palace_attrs.update({s:f"{p}{n}{SC[n]}"for s,p,n in zip(PS,P,numbers)if n in SC})
            term,next_term,next_date=await self._process_solar_terms(lunar_data.thisYearSolarTermsDic,now.month,now.day)
            stem,branch=lunar_data.day8Char[0],lunar_data.day8Char[1]
            six_idx=(lunar_data.lunarMonth+lunar_data.lunarDay-1)%6
            BL={'甲':'寅','乙':'卯','丙':'巳','戊':'巳','丁':'午','己':'午','庚':'申','辛':'酉','壬':'亥','癸':'子'}
            SG={'甲':('寅','卯'),'乙':('卯','辰'),'丙':('巳','午'),'戊':('巳','午'),'丁':('午','未'),'己':('午','未'),'庚':('申','酉'),'辛':('酉','戌'),'壬':('亥','子'),'癸':('子','丑')}
            luck_pos=BL.get(stem,'')
            day_fortune=f"{branch}命进禄"if branch==luck_pos else f"{branch}命互禄"if branch in SG.get(stem,())else f"{stem}命进{luck_pos}禄"
            state_map={'日期':formatted_date,'农历':f"{lunar_data.year8Char}({lunar_data.chineseYearZodiac})年 {lunar_data.lunarMonthCn}{lunar_data.lunarDayCn}",'星期':lunar_data.weekDayCn,'周数':f"{now.isocalendar()[1]}周",'今日节日':self._device.get_holiday(formatted_date,lunar_holidays_str),'八字':f"{lunar_data.year8Char} {lunar_data.month8Char} {lunar_data.day8Char} {lunar_data.twohour8Char}",'节气':term,'季节':lunar_data.lunarSeason,'生肖冲煞':lunar_data.chineseZodiacClash,'星座':lunar_data.starZodiac,'星次':lunar_data.todayEastZodiac,'彭祖百忌':self._text_processor.clean_text(''.join(lunar_data.get_pengTaboo(long=4,delimit=' '))),'十二神':self._text_processor.clean_text(' '.join(lunar_data.get_today12DayOfficer())),'廿八宿':self._text_processor.clean_text(''.join(lunar_data.get_the28Stars())),'今日三合':self._text_processor.clean_text(' '.join(lunar_data.zodiacMark3List)),'今日六合':lunar_data.zodiacMark6,'纳音':lunar_data.get_nayin(),'九宫飞星':numbers,'吉神方位':self._text_processor.format_lucky_gods(lunar_data.get_luckyGodsDirection()),'今日胎神':lunar_data.get_fetalGod(),'今日吉神':self._text_processor.clean_text(' '.join(lunar_data.goodGodName)),'今日凶煞':self._text_processor.clean_text(' '.join(lunar_data.badGodName)),'宜忌等第':lunar_data.todayLevelName,'宜':self._text_processor.clean_text(' '.join(lunar_data.goodThing)),'忌': self._text_processor.clean_text(' '.join(lunar_data.badThing)) or "暂无",'时辰经络':self._text_processor.clean_text(self._text_processor.format_dict(lunar_data.meridians)),'六曜':("大安","赤口","先胜","友引","先负","空亡")[six_idx],'日禄':day_fortune}
            self._state=state_map.get(self._type,'')
            if self._type=='九宫飞星'and nine_palace_attrs:self._attributes=nine_palace_attrs
            elif self._type=='节气'and next_term and next_date:self._attributes={"下一节气":f"{next_term} ({next_date})"}
            self._available=True
            return self._state
        except Exception as e:
            _LOGGER.error(f"更新传感器时出错 {self._type}: {e}")
            self._available=False
            return None

async def setup_sensor_updates(hass,sensors,um):
    UK="almanac_unsubs"
    [unsub() for unsub in hass.data.get(DOMAIN,{}).get(UK,[])]
    hass.data.setdefault(DOMAIN,{}).setdefault(UK,[])
    async def process_updates(sensors_to_update,group_type):
        async with um._lock:[await s.async_update() or s.async_write_ha_state() for s in sensors_to_update if not(s._updating or s._cleanup_called)]
    @callback
    def time_change_handler(now):[hass.loop.create_task(process_updates(group_sensors,group_type))for group_type,group_sensors in sensors_groups.items()if group_sensors]
    sensors_groups={'shichen':[s for s in sensors if s._type in['时辰']],'other':[s for s in sensors if s._type not in['日期','时辰']]}
    update_times={'shichen':{'second':[0],'minute':[0,15,30,45]},'other':{'second':[0],'minute':[0],'hour':'*'}}
    [hass.data[DOMAIN][UK].append(async_track_time_change(hass,time_change_handler,**update_schedule))for group_type,update_schedule in update_times.items()if sensors_groups[group_type]]
    
async def setup_almanac_sensors(hass,eid,cd):
    if DOMAIN not in hass.data:hass.data[DOMAIN]={}
    if"almanac_sensors"not in hass.data[DOMAIN]:hass.data[DOMAIN]["almanac_sensors"]={}
    if eid in hass.data[DOMAIN]["almanac_sensors"]:[await s.cleanup()for s in hass.data[DOMAIN]["almanac_sensors"][eid]];hass.data[DOMAIN]["almanac_sensors"][eid]=[]
    d=AlmanacDevice(eid,cd.get("name","中国老黄历"))
    await d.async_setup(hass)
    um=UpdateManager();await um.start()
    SK=['日期','农历','星期','今日节日','周数','八字','节气','季节','时辰凶吉','生肖冲煞','星座','星次','彭祖百忌','十二神','廿八宿','今日三合','今日六合','纳音','九宫飞星','吉神方位','今日胎神','今日吉神','今日凶煞','宜忌等第','宜','忌','时辰经络','时辰','六曜','日禄']
    s=[AlmanacSensor(d,cd.get("name","中国老黄历"),k,k in MAIN_SENSORS,hass)for k in SK]
    await setup_sensor_updates(hass,s,um)  
    hass.data[DOMAIN]["almanac_sensors"][eid]=s;return s,s

async def async_setup_entry(hass:HomeAssistant,entry:ConfigEntry,aae:AddEntitiesCallback)->bool:
    try:
        if entry.entry_id in hass.data.get(DOMAIN,{}).get("almanac_sensors",{}):return True
        e,s=await setup_almanac_sensors(hass,entry.entry_id,dict(entry.data))
        if DOMAIN not in hass.data:hass.data[DOMAIN]={}
        if"almanac_sensors"not in hass.data[DOMAIN]:hass.data[DOMAIN]["almanac_sensors"]={}
        await async_setup_date_service(hass);aae(e)
        hass.data[DOMAIN]["almanac_sensors"][entry.entry_id]=s;return True
    except:return False

async def async_unload_entry(hass:HomeAssistant,entry:ConfigEntry)->bool:
    if DOMAIN not in hass.data:return True
    try:
        if"almanac_unsubs"in hass.data[DOMAIN]:[unsub()for unsub in hass.data[DOMAIN]["almanac_unsubs"]];hass.data[DOMAIN]["almanac_unsubs"]=[]
        if"almanac_sensors"in hass.data[DOMAIN]:[await s.cleanup()for s in hass.data[DOMAIN]["almanac_sensors"].get(entry.entry_id,[])];hass.data[DOMAIN]["almanac_sensors"].pop(entry.entry_id,None)
        if not hass.data[DOMAIN]["almanac_sensors"]:hass.data.pop(DOMAIN,None);return True
    except:return False
