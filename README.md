# 🛢️ China Oil Price for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

按地区抓取中国今日油价，接入 Home Assistant。92#/95#/98#/0# 四个**数值型**油价传感器 + 一个「下次调价 / 涨跌方向」提示传感器。

> 数据来源：[qiyoujiage.com](http://www.qiyoujiage.com/)（汽油价格网）
> v2 重构：修复「下次调价/涨跌」长期显示 unknown、改为协调器单点抓取、价格数值化、补齐 unique_id 与地区校验。

---

## ✨ 功能

- 每个地区集成生成 **5 个实体**：`92#` `95#` `98#` `0#` 油价 + `调价提示`
- 油价为 `float`（带 `元/升` 单位、`state_class=measurement`），可直接用于**统计图 / 阈值自动化**
- 「调价提示」state 为完整中文句子，并把**下次调价时间 / 涨跌方向 / 各标号涨跌金额**拆成独立属性
- 一轮更新只抓取一次页面（4 个价格 + 1 提示共享缓存）
- 抓取/解析失败时实体进入 `unavailable`，不会偷偷显示旧值
- 添加集成时**试抓校验地区代码**，填错当场报错；重复地区自动拦截

## 📦 安装

### 方式一：HACS（推荐）

1. HACS → **Integrations** → 右上角 **⋮** → **Custom repositories**
2. Add，填本仓库地址：`https://github.com/zhoujunn/oil-price-hacs`，类别选 **Integration**
3. 搜索 **China Oil Price** → Install → 重启 Home Assistant

### 方式二：手动

1. 下载本仓库，把 `custom_components/oil_price` 文件夹整体拷贝到 HA 配置目录下的 `custom_components/`（没有就新建）
2. 重启 Home Assistant

## ⚙️ 配置

设置 → **设备与服务** → **添加集成** → 搜索 **China Oil Price**：

| 字段 | 说明 | 示例 |
| --- | --- | --- |
| 名称 | 显示名 | `南京油价` |
| 地区代码 | 页面 slug | `jiangsu` |
| 刷新间隔（小时） | 可选，默认 8 | `6` |

**常用地区代码**：

`beijing` `shanghai` `tianjin` `chongqing` `fujian` `shenzhen` `gansu` `guangdong` `guangxi` `guizhou` `hainan` `hebei` `henan` `hubei` `hunan` `jilin` `jiangsu` `jiangxi` `liaoning` `zhejiang` `neimenggu` `anhui` `ningxia` `qinghai` `shandong` `shanxi`（山西） `shanxi-3`（陕西） `sichuan` `xizang` `heilongjiang` `xinjiang` `yunnan`

> 不确定地区代码？打开 `http://www.qiyoujiage.com/`，点对应地区，浏览器地址栏里 `/xxxx.shtml` 的 `xxxx` 就是代码。

## 📊 实体与属性

价格实体（如 `sensor.南京油价_92`）：

| 属性 | 含义 |
| --- | --- |
| `state` | 数值油价，如 `8.58`（单位 `元/升`） |
| `update_time` | 最近一次成功抓取时间（UTC） |
| `region` | 地区代码 |

「调价提示」实体（如 `sensor.南京油价_调价提示`）：

| 属性 | 含义 | 示例 |
| --- | --- | --- |
| `state` | 完整中文提示句 | `下次油价10月15日24时调整 油价搁浅调整，维持目前价格不变。` |
| `next_adjust` | 下次调价时间 | `10月15日24时` |
| `direction` | 涨跌方向 | `上调` / `下调` / `搁浅` / `维持` … |
| `changes` | 各标号涨跌金额 | `{"92": "上调0.11元/升"}`（页面未给金额时为 `{}`） |

### 自动化示例：92 号超过 8.6 元/升就通知

```yaml
automation:
  - trigger:
      - platform: numeric_state
        entity_id: sensor.nanjing_youjia_92
        above: 8.6
    action:
      - service: notify.mobile_app
        data:
          message: "江苏 92# 已涨到 {{ states('sensor.nanjing_youjia_92') }} 元/升"
```

### 卡片示例：展示下次调价与方向

```yaml
type: entities
title: 油价
entities:
  - sensor.nanjing_youjia_92
  - sensor.nanjing_youjia_95
  - sensor.nanjing_youjia_98
  - sensor.nanjing_youjia_0
  - type: attribute
    entity: sensor.nanjing_youjia_调价提示
    attribute: next_adjust
    name: 下次调价
  - type: attribute
    entity: sensor.nanjing_youjia_调价提示
    attribute: direction
    name: 涨跌
```

## ❓ 常见问题

- **没有 entity_id / 找不到实体？** 集成安装后需在「设置 → 设备与服务」里**添加一个 China Oil Price 配置条目**（选地区），实体才会生成。
- **「调价提示」为空？** 说明数据源当前页面未放该区块，或网络抓取失败（实体为 `unavailable`），等下一轮刷新或检查 HA 日志。
- **改了地区代码不生效？** 删除旧配置条目重新添加；同一地区只能添加一次。
- **`update_time` 显示时区？** 那是 UTC 时间戳，在 HA「设置 → 系统 → 时区」正确时前端会本地化显示。

## ⚠️ 免责声明

油价仅供参考，实际以加油站售价为准；数据来自第三方站点，页面结构变更可能导致解析失效，请提 issue 或提 PR。

## 📄 License

[MIT](LICENSE)
