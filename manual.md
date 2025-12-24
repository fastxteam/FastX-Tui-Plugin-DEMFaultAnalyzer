# DEM故障分析器插件手册

## 概述

DEM故障分析器是基于AUTOSAR CP DEM故障状态分析工具，支持故障状态位解析和分析。

## 功能

### DTC故障解析

- 解析DTC故障码
- 显示故障状态位
- 支持多种DTC格式

### DEM状态分析

- 分析DEM故障状态
- 显示故障历史
- 支持故障筛选

## 配置

### log_level

- 类型: 字符串
- 默认值: "INFO"
- 说明: 插件的日志级别
- 可选值: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"

### max_history_items

- 类型: 整数
- 默认值: 100
- 说明: 最大历史记录数量

### enable_auto_save

- 类型: 布尔值
- 默认值: False
- 说明: 是否自动保存分析结果

## 使用示例

1. 选择"诊断"菜单
2. 选择"DEM故障分析器"
3. 选择相应的分析功能
4. 按照提示输入DTC或选择故障文件
5. 查看分析结果

## 开发说明

该插件基于AUTOSAR CP DEM标准，支持多种DTC格式的解析和分析。

## 版本历史

### v1.0.0
- 初始版本
- 支持基本的DTC故障解析
- 实现DEM状态分析

## 技术支持

- 仓库: https://github.com/fastxteam/FastX-Tui-Plugin-DEMFaultAnalyzer
- 问题反馈: https://github.com/fastxteam/FastX-Tui-Plugin-DEMFaultAnalyzer/issues