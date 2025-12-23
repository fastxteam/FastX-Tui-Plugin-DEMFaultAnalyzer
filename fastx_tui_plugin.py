#!/usr/bin/env python3
"""
FastX-Tui DEM Fault Analyzer Plugin - 入口文件
这个文件是插件的入口，包含插件的配置信息和基本结构
业务逻辑请参考 dem_fault_analyzer.py
"""

import os
import toml
from typing import List, Dict
from core.plugin_manager import Plugin, PluginInfo
from core.menu_system import MenuSystem
from dem_fault_analyzer import DEMFaultAnalyzer

class DEMFaultAnalyzerPlugin(Plugin):
    """DEM故障分析器插件
    
    这是FastX-Tui插件的入口类，所有插件必须继承自Plugin类并实现所有抽象方法。
    """
    
    def __init__(self):
        """初始化插件"""
        super().__init__()
        self.business = None
    
    @classmethod
    def get_version(cls) -> str:
        """从pyproject.toml获取当前版本号"""
        try:
            # 获取当前文件所在目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # 构建pyproject.toml的路径
            pyproject_path = os.path.join(current_dir, "pyproject.toml")
            # 读取文件
            with open(pyproject_path, "r", encoding="utf-8") as f:
                data = toml.load(f)
            # 返回版本号
            return data["project"]["version"]
        except Exception as e:
            # 如果读取失败，返回默认版本
            return "1.0.0"
    
    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            name="DEM故障分析器",
            version=self.get_version(),
            author="FastX Team",
            description="基于AUTOSAR CP和ETAS DEM的DTC故障状态分析工具，支持故障状态位解析和分析",
            category="诊断",  # 插件分类
            tags=["DEM", "DTC", "故障分析", "AUTOSAR", "ETAS"],  # 插件标签
            compatibility={"fastx-tui": ">=0.1.13"},  # 兼容性要求
            dependencies=[],  # 依赖项
            repository="https://github.com/fastxteam/FastX-Tui-Plugin-DEMFaultAnalyzer",  # 插件仓库
            homepage="https://github.com/fastxteam/FastX-Tui-Plugin-DEMFaultAnalyzer",  # 插件主页
            license="MIT",  # 许可证
            last_updated="2025-12-23",  # 最后更新时间
            rating=5.0,  # 评分
            downloads=0  # 下载次数
        )
    
    def initialize(self):
        """初始化插件"""
        # 初始化业务逻辑
        self.business = DEMFaultAnalyzer(self)
        self.log_info("DEM故障分析器插件初始化完成")
    
    def cleanup(self):
        """清理插件资源"""
        self.log_info("DEM故障分析器插件清理完成")
        # 清理业务逻辑资源
        self.business = None
    
    def register(self, menu_system: MenuSystem):
        """注册插件命令到菜单系统"""
        # 调用业务逻辑注册命令
        self.business.register_commands(menu_system)