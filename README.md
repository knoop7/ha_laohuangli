<div align="center">
  


## 中国老黄历 (Chinese Almanac) for Home Assistant

<br>

<img width="960" alt="截屏2024-09-24 14 06 27" src="https://github.com/user-attachments/assets/2414840b-c860-4d49-b788-b25fbb51b0e5">

</div>
<br>


**为您的智能家居注入传统中国历法的智慧与魅力**
<br>

![版本](https://img.shields.io/badge/version-2024.11.20-blue.svg)
![Home Assistant版本](https://img.shields.io/badge/Hoe%20Assistant-2024.8.0+-yellow.svg)
![维护状态](https://img.shields.io/badge/维护-活跃-green.svg)
![许可](https://img.shields.io/badge/许可-MIT-brightgreen.svg)
![Python版本](https://img.shields.io/badge/Python-3.9+-blue.svg)
![代码扫描](https://img.shields.io/badge/代码扫描-通过-success)

<br>

## ✨ 主要功能

- 📅 实时显示农历日期、阳历对应信息
- 🌱 精准预测二十四节气，并关联天气变化
- 🍀 每日吉凶、宜忌指引，提供生活参考
- ⏰ 实时更新时辰吉凶，指导日常活动安排
- 🐲 展示生肖、星座等个人属性，结合每日运势分析
- 🐉 观音灵签功能，解签并提供每日详细运势解读
- 🎯 支持自定义事件管理，记录重要日子，如生日、纪念日，并提供吉凶预警
- 🎂 基于生日生成八字命盘，结合生肖与星座的运势参考
- 🎉 智能提醒中国传统节日、重要日子
- 📡 支持自定义更新频率，灵活配置更新间隔
  
## 🛠 安装步骤

### 快速安装：
1. Hacs存储库添加https://github.com/knoop7/ha_laohuangli 安装
2. 重启您的Home Assistant系统
3. 在集成页面中搜索"中国老黄历"或者"tgtg"，添加该集成

### 复杂安装：
1. 将 `发行版压缩包` 解压文件夹后，复制到您的Home Assistant配置目录下的 `custom_components` 文件夹
2. 重启您的Home Assistant系统
3. 在集成页面中搜索"中国老黄历"或者"tgtg"，添加该集成

## 📊 可用传感器

- **基础信息**：日期、农历、星期、今日节日
- **传统历法**：八字、节气、季节、时辰凶吉等信息
- **个人属性**：生肖、冲煞、星座、星次
- **传统文化**：彭祖百忌、十二神、廿八宿、三合六合
- **风水择日**：纳音、九宫飞星、吉神方位、胎神定位
- **吉凶指引**：今日吉神、凶煞、宜忌等级、日常活动建议
- **健康养生**：时辰经络、时辰刻度
- **事件提醒**：自定义事件管理，如生日、纪念日等
- **生日管理**：家人生日、八字记录与提醒
- **观音灵签**：每日灵签抽取与解签，提供每日运势参考

## 🖥 使用示例

安装并配置后，您可以在Home Assistant的仪表板中灵活运用这些传感器。以下是一个简单的卡片配置示例：

```yaml
type: vertical-stack
cards:
  - type: entities
    entities:
      - entity: sensor.lao_huang_li
      - entity: sensor.lao_huang_li_ba_zi
      - entity: sensor.lao_huang_ji_shen
      - entity: sensor.lao_huang_li_ji_shen_fang_wei
      - entity: sensor.lao_huang_li_nong_li
      - entity: sensor.lao_huang_li_xing_qi
      - entity: sensor.lao_huang_li_jin_ri_tai_shen
      - entity: sensor.lao_huang_li_na_yin
  - type: entities
    entities:
      - entity: sensor.lao_huang_li_nian_ba_su
      - entity: sensor.lao_huang_li_ji
      - entity: sensor.lao_huang_li_peng_zu_bai_ji
      - entity: sensor.lao_huang_li_shi_er_shen
      - entity: sensor.lao_huang_li_xing_ci
      - entity: sensor.lao_huang_li_xing_qi
      - entity: sensor.lao_huang_li_jin_ri_xiong_sha
      - entity: sensor.lao_huang_li_yi
      - entity: sensor.lao_huang_li_jin_ri_liu_he
      - entity: sensor.lao_huang_li_jin_ri_jie_qi
```


<br>
<br>

您的打赏对于我来说是前进的动力和维护的核心！

<img src="https://github.com/user-attachments/assets/444a1a4a-251b-4a6c-8070-7ba4cca642f4" alt="description" width="300" />


> **特别声明**：本插件独家授权Home Assistant家庭助手公众号，未经允许禁止转发到其他平台。如有违规使用，将停止更新及修复问题。


