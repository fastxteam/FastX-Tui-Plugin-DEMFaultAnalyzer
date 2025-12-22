# DEM故障分析器

基于AUTOSAR CP和ETAS DEM的DTC故障状态分析工具，支持故障状态位解析和分析。

## 功能特性

- ✅ **DTC状态位解析**：支持解析8位DTC状态码，可视化显示每个位的状态
- ✅ **状态位跳转规则**：详细说明AUTOSAR CP和ETAS DEM中每个状态位的跳转时机
- ✅ **多级菜单结构**：清晰的二级菜单设计，方便用户操作
- ✅ **Rich可视化界面**：使用Rich库实现美观的表格和面板显示
- ✅ **详细的帮助文档**：提供完整的使用说明和背景信息

## 安装方法

1. 将插件目录复制到FastX-Tui的plugins目录下
2. 启动FastX-Tui，插件会自动加载
3. 在主菜单中找到"DEM故障分析器"即可使用

## 目录结构

```
FastX-Tui-Plugin-DEMFaultAnalyzer/
├── fastx_plugin.py       # 插件入口文件
├── dem_fault_analyzer.py # 业务逻辑文件
├── pyproject.toml        # 项目配置文件
├── README.md             # 项目说明文档
└── LICENSE               # 许可证文件
```

## 使用说明

### 1. DTC状态分析

进入"DTC状态分析"子菜单，可以选择不同的状态码进行解析：

- **解析状态码 0x00**：所有状态位未设置
- **解析状态码 0x01**：testFailed置1
- **解析状态码 0x03**：testFailed和testFailedThisOperationCycle置1
- **解析状态码 0x07**：前三位状态位置1
- **解析状态码 0x0F**：前四位状态位置1
- **解析状态码 0xFF**：所有状态位置1

### 2. 状态位跳转规则

进入"状态位跳转规则"子菜单，可以查看每个状态位的跳转时机：

- **Bit 0 (testFailed)**：当前测试结果
- **Bit 1 (testFailedThisOperationCycle)**：当前循环故障记录
- **Bit 2 (pendingDTC)**：待确认故障
- **Bit 3 (confirmedDTC)**：已确认故障
- **Bit 4 (testNotCompleteSinceLastClear)**：清除后测试状态
- **Bit 5 (testFailedSinceLastClear)**：清除后故障记录
- **Bit 6 (testNotCompletedThisOperationCycle)**：当前循环测试状态
- **Bit 7 (warningIndicatorRequested)**：警告指示请求

### 3. 帮助信息

进入"帮助信息"子菜单，可以查看：

- **概述**：DEM故障分析器的基本介绍
- **DTC格式说明**：DTC状态码的格式和定义
- **AUTOSAR DEM信息**：AUTOSAR DEM的背景知识

## DTC状态位定义

| 位 | 名称 | 描述 |
|----|------|------|
| 0 | testFailed (TF) | 当前结果为故障状态 - 最近一次测试中发现故障 |
| 1 | testFailedThisOperationCycle (TFTOC) | 当前操作循环中至少检测到一次故障 |
| 2 | pendingDTC (PDTC) | 当前或上一个操作循环期间至少检测到1次故障 |
| 3 | confirmedDTC (CDTC) | 表示存在历史故障 - 故障已存储到非易失性内存 |
| 4 | testNotCompleteSinceLastClear (TNCSLC) | 上次清除后DTC检测尚未完成 |
| 5 | testFailedSinceLastClear (TFSLC) | 上次清除后该DTC出过至少一次错 |
| 6 | testNotCompletedThisOperationCycle (TNCTOC) | 当前循环还未完成该DTC测试 |
| 7 | warningIndicatorRequested (WIR) | 该DTC关联的警告指示灯亮 |

## 技术支持

- 项目主页：
- 问题反馈：
- 许可证：MIT License

## 开发说明

### 依赖项

- Python 3.8+
- rich >= 13.0.0

### 开发环境设置

```bash
# 安装开发依赖
pip install -e .[dev]

# 运行测试
pytest

# 代码格式化
black .

# 代码检查
flake8
```

### 插件开发规范

1. 遵循FastX-Tui插件开发规范
2. 使用类型注解
3. 保持代码简洁清晰
4. 提供完整的文档
5. 支持Python 3.8+版本

## 更新日志

### v1.0.0 (2025-12-22)

- 初始版本发布
- 支持DTC状态位解析
- 支持状态位跳转规则查看
- 提供完整的帮助文档

## 许可证

MIT License
