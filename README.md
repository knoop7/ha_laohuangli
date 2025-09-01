<div align="center">

<img width="960" alt="img" src="https://github.com/user-attachments/assets/2414840b-c860-4d49-b788-b25fbb51b0e5">


## Chinese Almanac for Home Assistant
### Infuse your smart home with the wisdom and charm of traditional Chinese calendar culture


<br>

<br>



</div>




<br>
<img src="https://img.shields.io/badge/version-2025.08.30-blue.svg" alt="Version">
<img src="https://img.shields.io/badge/Home%20Assistant-2024.4.0+-yellow.svg" alt="Home Assistant">
<img src="https://img.shields.io/badge/Maintenance-Active-green.svg" alt="Maintenance">
<img src="https://img.shields.io/badge/License-MIT-brightgreen.svg" alt="License">
<img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
<img src="https://img.shields.io/badge/Code%20Scan-Passed-success" alt="Code Scan">
<br>

## ✨ Key Features
- 📅 Real-time display of lunar calendar date and its Gregorian counterpart  
- 🌱 Accurate 24-solar-term forecasts linked to weather changes  
- 🍀 Daily auspicious/inauspicious guidance, taboos, and lunar-phase astronomy  
- ⏰ Live updating of traditional two-hour periods to guide daily scheduling  
- 🐲 Show personal attributes like Chinese zodiac and Western horoscope, paired with daily fortune insights  
- 🎯 Custom event management to log birthdays, anniversaries, etc., with luck warnings  
- 🎂 Generate a BaZi chart from birth data and merge zodiac & horoscope forecasts  
- 🎉 Smart alerts for traditional Chinese festivals and key dates  
- 📡 Adjustable refresh frequency for flexible update intervals  

<br>

## 🛠 Installation
### Quick Install
1. Add the HACS repository <code>https://github.com/knoop7/ha_laohuangli</code> and install  
2. Or click → <a href="http://homeassistant.local:8123/hacs/repository?owner=knoop7&repository=ha_laohuangli">Quick Link</a>  
3. Restart your Home Assistant instance  
4. In the Integrations page search for <strong>Chinese Almanac</strong> or <strong>chinese</strong> and add the integration  

### Manual Install
1. Download the release ZIP, extract, and copy the folder into <code>custom_components</code> in your Home Assistant config directory  
2. Restart your Home Assistant instance  
3. In the Integrations page search for <strong>Chinese Almanac</strong> or <strong>chinese</strong> and add the integration  

<br>

## 📊 Available Sensors
- <strong>Basic Info</strong>: date, lunar date, weekday, today’s festivals, week number  
- <strong>Traditional Calendar</strong>: BaZi, solar terms, seasons, two-hour periods, period luck  
- <strong>Personal Attributes</strong>: zodiac clashes, constellation, lunar mansion, Rokuyō, daily fortune direction  
- <strong>Cultural Lore</strong>: Pengzu taboos, twelve deities, 28 lunar mansions, today’s trines & hexes, three-life physiognomy  
- <strong>Feng Shui & Elements</strong>: Nayin element, 64 hexagrams, flying stars, auspicious directions, daily fetal spirit  
- <strong>Luck Guidance</strong>: today’s auspicious spirits, ominous spirits, luck level, suitable & unsuitable activities  
- <strong>Health & Wellness</strong>: meridian flow by hour, hour scale  
- <strong>Event Reminders</strong>: custom events such as birthdays and anniversaries  
- <strong>Birthday Manager</strong>: family birthdays, BaZi records & reminders, AI predictions  
- <del><strong>Guanyin Oracle Lots</strong>: removed; roll back to v10.31 to restore</del>  

<br>

## 🖥 Usage Examples
After installation and configuration, you can freely use these sensors in your Home Assistant dashboards.  
The Chinese Almanac card presents rich traditional calendar data in a clear, intuitive layout:<br>
<img width="556" alt="img" src="https://github.com/user-attachments/assets/dc0556d4-24f3-4f4d-a1cc-3560ee8bf917">

<h4>Large digits show the current date</h4>
Tap the left/right arrows to move to the previous/next day; tap the date itself to open a date-picker for quick jumps.<br>
Displays the current lunar date and BaZi info. Enable/disable individual modules, drag to reorder, lock/unlock layout, and reset to default with one click.

<h4>Info Module Area</h4>
Six-grid layout; each module groups related data:
<ul>
<li><strong>Rhythm & Lunar</strong>: week number, season, solar term, constellation, moon phase</li>
<li><strong>Divination</strong>: Nayin, lunar mansion, flying star, 28 mansions, twelve deities</li>
<li><strong>Hour & Fortune</strong>: daily fortune direction, two-hour period, meridian, 64 hexagrams, luck</li>
<li><strong>Kongming Bird Signs</strong>: Rokuyō, trines, hexes, bird signs, zodiac clashes</li>
<li><strong>Taboos & Directions</strong>: fetal spirit, Pengzu taboos, auspicious directions</li>
<li><strong>Spirits & Luck</strong>: auspicious spirits, ominous spirits, luck level</li>
</ul>

<h4>Sample card configuration</h4>
<pre><code>type: custom:almanac-card
title: Chinese Almanac
prefix: chinese_almanac_</code></pre>
