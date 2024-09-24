## 中国老黄历 (Chinese Almanac) for Home Assistant

![版本](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Home Assistant版本](https://img.shields.io/badge/Home%20Assistant-2023.6.0+-yellow.svg)
![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)
![维护状态](https://img.shields.io/badge/维护-活跃-green.svg)
![许可](https://img.shields.io/badge/许可-MIT-brightgreen.svg)
![Python版本](https://img.shields.io/badge/Python-3.9+-blue.svg)
![代码扫描](https://img.shields.io/badge/代码扫描-通过-success)

"中国老黄历"是一个为Home Assistant精心打造的自定义组件，旨在为您的智能家居注入传统中国历法的智慧与魅力。本插件提供丰富的中国传统历法信息，让您在现代科技的怀抱中感受古老文化的脉动。
> **特别声明**：本插件独家授权Home Assistant家庭助手公众号，未经允许禁止转发到其他平台。如有违规使用，将停止更新及修复问题。


<img width="960" alt="截屏2024-09-24 14 06 27" src="https://github.com/user-attachments/assets/2414840b-c860-4d49-b788-b25fbb51b0e5">




#### ✨ 主要功能

- 📅 实时显示农历日期信息
- 🌱 精准预报二十四节气
- 🍀 每日吉凶、宜忌指引
- ⏰ 实时更新时辰凶吉信息
- 🐲 展示生肖、星座等个人信息（后续更新）
- 🎉 智能提醒传统节日(后续更新)
- ⚙️ 支持自定义更新频率（已支持）
  
#### 🛠 安装步骤

1. 将 `custom_components/home_assistant_tgtg` 文件夹复制到您的Home Assistant配置目录下的 `custom_components` 文件夹中。
2. 重启您的Home Assistant系统。
3. 在集成页面中搜索"中国老黄历"并添加该集成。

#### 📊 可用传感器

安装成功后，您将获得以下丰富的传感器：

- 基础信息：日期、农历、星期、今日节日
- 传统历法：八字、节气信息、季节、时辰凶吉
- 个人属性：生肖冲煞、星座、星次
- 传统文化：彭祖百忌、十二神、廿八宿、三合六合
- 风水择日：纳音、九宫飞星、吉神方位、胎神
- 吉凶指引：今日吉神、凶煞、宜忌等第、宜、忌
- 健康养生：时辰经络（暂不更新）

#### 🖥 使用示例

安装并配置
后，您可以在Home Assistant的仪表板中灵活运用这些传感器。以下是一个简单的卡片配置示例：

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
