<div align="center">
  


## 中国老黄历 (Chinese Almanac) for Home Assistant

<br>

<img width="960" alt="截屏2024-09-24 14 06 27" src="https://github.com/user-attachments/assets/2414840b-c860-4d49-b788-b25fbb51b0e5">

</div>
<br>


**为您的智能家居注入传统中国历法的智慧与魅力**
<br>

![版本](https://img.shields.io/badge/version-2024.12.01-blue.svg)
![Home Assistant版本](https://img.shields.io/badge/Hoe%20Assistant-2024.8.0+-yellow.svg)
![维护状态](https://img.shields.io/badge/维护-活跃-green.svg)
![许可](https://img.shields.io/badge/许可-MIT-brightgreen.svg)
![Python版本](https://img.shields.io/badge/Python-3.1.3+-blue.svg)
![代码扫描](https://img.shields.io/badge/代码扫描-通过-success)

<br>

## ✨ 主要功能

- 📅 实时显示农历日期、阳历对应信息
- 🌱 精准预测二十四节气，并关联天气变化
- 🍀 每日吉凶、宜忌指引，月相天文
- ⏰ 实时更新时辰，指导日常活动安排
- 🐲 展示生肖、星座等个人属性，结合每日运势分析
- 🎯 支持自定义事件管理，记录重要日子，如生日、纪念日，并提供吉凶预警
- 🎂 基于生日生成八字命盘，结合生肖与星座的运势参考
- 🎉 智能提醒中国传统节日、重要日子
- 📡 支持自定义更新频率，灵活配置更新间隔
  


<br>

## 🛠 安装步骤

### 快速安装：
1. Hacs存储库添加https://github.com/knoop7/ha_laohuangli 安装
2. 重启您的Home Assistant系统
3. 在集成页面中搜索"中国老黄历"或者"tgtg"，添加该集成

### 复杂安装：
1. 将 `发行版压缩包` 解压文件夹后，复制到您的Home Assistant配置目录下的 `custom_components` 文件夹
2. 重启您的Home Assistant系统
3. 在集成页面中搜索"中国老黄历"或者"tgtg"，添加该集成


<br>

## 📊 可用传感器

- **基础信息**：日期、农历、星期、今日节日、周数
- **传统历法**：八字、节气、季节、时辰、时辰凶吉
- **个人属性**：生肖冲煞、星座、星次、六曜、日禄
- **传统文化**：彭祖百忌、十二神、廿八宿、今日三合、今日六合
- **风水五行**：纳音、九宫飞星、吉神方位、今日胎神
- **吉凶指引**：今日吉神、今日凶煞、宜忌等第、宜、忌
- **健康养生**：时辰经络、时辰刻度
- **事件提醒**：自定义事件管理，如生日、纪念日等
- **生日管理**：家人生日、八字记录与提醒
-  ~~**观音灵签**：已删除可更新回退10.31版本~~

<br>

## 🖥 使用示例

安装并配置后，您可以在Home Assistant的仪表板中灵活运用这些传感器
<br>
中国老黄历卡片为您提供丰富的传统历法信息，界面布局清晰直观：

<img width="400" alt="截屏2024-11-25 16 00 11" src="https://github.com/user-attachments/assets/b8b69c30-d08f-4225-a605-9ea2318961e9">

#### 大数字显示当前日期
可点击左右箭头切换前一天/后一天，点击日期可打开日期选择器，方便跳转到指定日期
<br>
显示当前农历日期与八字信息，启用/禁用特定信息模块，通过拖拽调整模块顺序，锁定/解锁布局一键恢复默认设置

#### 信息模块区域
采用六宫格布局，每个模块包含相关联的信息：

- **节律太阴**：显示周数、季节、节气、星座、月相等信息
- **卜筮术数**：包含纳音、星次、飞星、廿八宿、十二神等术数信息
- **日时禄位**：展示日禄、时辰、经络、吉凶等时刻信息
- **孔明生肖**：显示六曜、三合、六合、生肖冲煞等信息
- **胎忌利向**：提供胎神、百忌、方位等趋避信息
- **神煞吉凶**：展示吉神、凶煞、等第等综合信息

#### 以下是卡片配置示例：

```yaml

实体卡片界面UI
删除集成之后不可见！

type: custom:almanac-card
title: 老黄历

注明：若您修改了老黄历的名称
可能模版无法识别您的实体名称

所以可以修改前缀名
type: custom:almanac-card
title: 老黄历
prefix: lao_huang_li_  

```




<br>
<br>


您的打赏对于我来说是前进的动力和维护的核心！

<br>

<img src="https://github.com/user-attachments/assets/444a1a4a-251b-4a6c-8070-7ba4cca642f4" alt="description" width="300" />


> **特别声明**：本插件独家授权Home Assistant家庭助手公众号，未经允许禁止转发到其他平台。如有违规使用，将停止更新及修复问题。


