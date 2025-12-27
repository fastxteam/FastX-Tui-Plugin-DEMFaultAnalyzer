#!/usr/bin/env python3
"""
FastX-Tui DEM Fault Analyzer Plugin - 业务逻辑模块
基于AUTOSAR CP和ETAS DEM的DTC故障状态分析工具
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from core.menu_system import MenuSystem, ActionItem, CommandType
from rich.table import Table
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.box import ROUNDED, SQUARE, SIMPLE
from rich.columns import Columns
from rich.rule import Rule


@dataclass
class BitInfo:
    """状态位信息数据类"""
    bit: int
    name: str
    abbr: str
    intro: str
    desc_true: str  # 置位时的描述
    desc_false: str  # 复位时的描述
    detailed_desc: str  # 详细描述
    set_conditions: List[str]  # 置位条件
    clear_conditions: List[str]  # 清除条件
    mask: int  # 位掩码


class DTCStatusConfig:
    """DTC状态配置表"""

    # 统一配置表
    BIT_CONFIGS = [
        BitInfo(
            bit=0,
            name="testFailed",
            abbr="TF",
            intro="请求时刻测试结果为失败",
            desc_true="当前结果为故障状态",
            desc_false="当前结果不为故障状态",
            detailed_desc="""通常来说，ECU内部以循环的方式不断地针对预先定义好的错误路径进行测试。
如果在最近的一次测试中，在某个错误路径中发现了故障，则相应DTC的这一个状态位就要被置1，表征出错。
此时DTC的testFailed位被置1，但是它不一定被ECU存储到non-volatile memory中。
只有当pendingDTC或confirmedDTC被置1时DTC才会被存储。
而pendingDTC或confirmedDTC被置1的条件应该是检测到错误出现的次数或时间满足某个预定义的门限。
当错误消失或者诊断仪执行了清除DTC指令时，testFailed会再次被置为0。""",
            set_conditions=[
                "周期性测试发现故障条件满足时立即置1",
                "故障发生时立即置1"
            ],
            clear_conditions=[
                "下一个周期测试故障条件未满足时立即恢复为0",
                "Dem_ClearDTC函数清除故障信息（USD 0x14服务，或OBD 0x04服务）",
                "Dem_ResetEventStatus函数对该故障状态位进行复位"
            ],
            mask=0x01
        ),
        BitInfo(
            bit=1,
            name="testFailedThisOperationCycle",
            abbr="TFTOC",
            intro="在当前点火循环至少失败1次",
            desc_true="当前操作循环中至少检测到一次故障",
            desc_false="当前操作循环中没有检测到一次故障",
            detailed_desc="""这个bit用于标识某个DTC在当前的operation cycle中是否出现过testFailed置1的情况，即是否出现过错误。
operation cycle的起始点是ECU通过网络管理唤醒到ECU通过网络管理进入睡眠。
对于没有网络管理的ECU，这个起始点就是KL15通断。
通过bit 0我们无法判断某个DTC是否出现过，比如，当前testFailed = 0，说明当前这个DTC没有出错。
如果testFailedThisOperationCycle = 1的话，就说明这个DTC在当前这个operation cycle中出过错，但是当前错误又消失了。""",
            set_conditions=[
                "一旦testFailed出现过置1的情况，立即置1"
            ],
            clear_conditions=[
                "该运行循环结束或新的运行循环开始",
                "Dem_ClearDTC函数清除故障信息（USD 0x14服务，或OBD 0x04服务）"
            ],
            mask=0x02
        ),
        BitInfo(
            bit=2,
            name="pendingDTC",
            abbr="PDTC",
            intro="在当前或者上一个点火循环测试结果不为失败",
            desc_true="当前操作循环或者上一个完成的操作循环期间至少检测到1次故障",
            desc_false="当前操作循环或者上一个完成的操作循环期间没有检测到1次故障",
            detailed_desc="""根据规范的解释，pendingDTC = 1表示某个DTC在当前或者上一个operation cycle中是否出现过。
pendingDTC位其实是位于testFailed和confirmedDTC之间的一个状态。
有的DTC被确认的判定条件比较严苛，需要在多个operation cycle中出现才可以被判定为confirmed的状态，此时就需要借助于pendingDTC位了。
pendingDTC = 1的时候，DTC就要被存储下来了。
如果接下来的两个operation cycle中这个DTC都还存在，那么confirmedDTC就要置1了。
如果当前operation cycle中，故障发生，pendingDTC = 1，但是在下一个operation cycle中，故障没有了，
pendingDTC 仍然为 1，再下一个operation cycle中，故障仍然不存在，那么pendingDTC 就可以置0了。""",
            set_conditions=[
                "故障在当前运行循环或者上一个运行循环出现过testFailed被置位为1",
                "当前循环测试完毕之后更新状态"
            ],
            clear_conditions=[
                "当前运行TestFailedThisOperationCycle未置为1，且TestNotCompletedThisOperationCycle未置为1，同时运行循环结束或者下一个运行循环开始",
                "Dem_ClearDTC函数清除故障信息（USD 0x14服务，或OBD 0x04服务）"
            ],
            mask=0x04
        ),
        BitInfo(
            bit=3,
            name="confirmedDTC",
            abbr="CDTC",
            intro="请求时刻DTC被确认，一般确认是在一个点火周期内发生错误1次",
            desc_true="表示存在历史故障 - 故障已存储到非易失性内存",
            desc_false="表示不存在历史故障",
            detailed_desc="""当confirmedDTC = 1时，则说明某个DTC已经被存储到ECU的non-volatile memory中，
说明这个DTC曾经满足了被confirmed的条件。
但是请注意，confirmedDTC = 1时，并不意味着当前这个DTC仍然出错。
如果confirmedDTC = 1，但testFailed = 0，则说明这个DTC表示的故障目前已经消失了。
将confirmedDTC重新置0的方法只有删除DTC，UDS用0x14服务，OBD用0x04服务。""",
            set_conditions=[
                "故障已经确认，故障数据存储至EEPROM或者FEE",
                "满足确认条件时置1（通常需要多次出现）"
            ],
            clear_conditions=[
                "故障老化",
                "故障替代",
                "Dem_ClearDTC函数（USD 0x14服务，OBD为 0x04服务）清除故障信息"
            ],
            mask=0x08
        ),
        BitInfo(
            bit=4,
            name="testNotCompleteSinceLastClear",
            abbr="TNCSLC",
            intro="自上次清除DTC之后测试结果已完成，即测试结果为PASS或者FAIL",
            desc_true="表示从上次进行清除诊断信息后，DTC检测尚未完成",
            desc_false="自从清理DTC之后已经完成过针对该DTC的测试",
            detailed_desc="""这个bit用于标识，自从上次调用了清理DTC的服务（UDS用0x14服务，OBD用0x04服务）之后，
是否成功地执行了对某个DTC的测试（不管测试结果是什么，只关心是否测了）。
因为很多DTC的测试也是需要满足某些边界条件的，并不是ECU上电就一定会对DTC进行检测。""",
            set_conditions=[
                "自从上次调用Dem_ClearDTC函数清除故障信息后，尚未成功执行对故障进行检测"
            ],
            clear_conditions=[
                "成功执行对故障进行检测后自动清除"
            ],
            mask=0x10
        ),
        BitInfo(
            bit=5,
            name="testFailedSinceLastClear",
            abbr="TFSLC",
            intro="自上次清除DTC后测试结果都不是FAIL",
            desc_true="自从清理DTC之后该DTC出过至少一次错",
            desc_false="自从清理DTC之后该DTC没有出过错",
            detailed_desc="""这个位与bit 1:testFailedThisOperationCycle有些类似。
后者标识某个DTC在当前的operation cycle中是否出现过testFailed置1的情况。
而testFailedSinceLastClear标识的是在上次执行过清理DTC之后某个DTC是否出过错。""",
            set_conditions=[
                "自从上次调用Dem_ClearDTC函数清除故障信息后，testFailed出现过置位为1"
            ],
            clear_conditions=[
                "Dem_ClearDTC函数清除故障信息"
            ],
            mask=0x20
        ),
        BitInfo(
            bit=6,
            name="testNotCompletedThisOperationCycle",
            abbr="TNCTOC",
            intro="在当前点火周期内测试结果已完成，即为PASS或FAIL状态",
            desc_true="在当前operation cycle中还没在完成过针对该DTC的测试",
            desc_false="在当前operation cycle中已经完成过针对该DTC的测试",
            detailed_desc="""这个位与bit 4: testNotCompletedSinceLastClear类似。
后者标识自从上次调用了清理DTC的服务之后，是否成功地执行了对某个DTC的测试。
而testNotCompletedThisOperationCycle则标识在当前operation cycle中是否成功地执行了对某个DTC的测试。""",
            set_conditions=[
                "当前循环还未对该故障进行检测测试"
            ],
            clear_conditions=[
                "当前循环已对该故障进行检测测试后自动清除"
            ],
            mask=0x40
        ),
        BitInfo(
            bit=7,
            name="warningIndicatorRequested",
            abbr="WIR",
            intro="ECU没有得到点亮警示灯请求",
            desc_true="表示该bit关联的特定DTC警告指示灯亮",
            desc_false="ECU不请求激活警告指示",
            detailed_desc="""某些比较严重的DTC会与用户可见的警告指示相关联，
比如仪表上的报警灯，或者是文字，或者是声音。
这个warningIndicatorRequested就用于此类DTC。""",
            set_conditions=[
                "ECU请求激活警告指示（如仪表MIL灯）",
                "严重故障发生时置1"
            ],
            clear_conditions=[
                "ECU不请求激活警告指示",
                "故障消失或降低严重程度后清除"
            ],
            mask=0x80
        )
    ]

    @classmethod
    def get_bit_info(cls, bit: int) -> Optional[BitInfo]:
        """获取指定bit的信息"""
        for config in cls.BIT_CONFIGS:
            if config.bit == bit:
                return config
        return None

    @classmethod
    def get_all_bits(cls) -> List[BitInfo]:
        """获取所有bit信息"""
        return cls.BIT_CONFIGS


class ISO14229DTCSTATUS:
    """DTC状态位解析类"""

    @staticmethod
    def parse_status_code(status_hex: str) -> Dict:
        """解析DTC状态码"""
        # 转换为整数
        status_int = int(status_hex.replace('0x', '').replace('0X', ''), 16)

        # 解析每个位
        bits = {}
        for bit in range(8):
            bits[bit] = (status_int & (1 << bit)) != 0

        return {
            'hex': status_hex,
            'decimal': status_int,
            'binary': bin(status_int)[2:].zfill(8),
            'bits': bits
        }

    @staticmethod
    def format_analysis(status_hex: str) -> str:
        """格式化分析结果 - 合并为一个Panel"""
        result = ISO14229DTCSTATUS.parse_status_code(status_hex)

        # 使用StringIO捕获输出
        from io import StringIO
        output = StringIO()
        console = Console(file=output, width=146)

        # 构建完整的Panel内容
        content_parts = []

        # 1. 状态码信息 - 标题使用特定颜色但不影响宽度
        title_text = Text("[DTC状态码分析]\n")
        title_text.stylize("bold cyan", 0, len("DTC状态码分析"))

        content_parts.append(title_text)

        # 状态码信息
        status_info = Text(f"HEX: {result['hex']} | DEC: {result['decimal']} | BIN: {result['binary']}\n\n")
        content_parts.append(status_info)

        # 2. 方块视图 - 使用原来的版本但确保一行显示
        section_title = Text("[状态位分布]\n")
        section_title.stylize("magenta", 0, len("状态位分布"))

        content_parts.append(section_title)
        content_parts.append(ISO14229DTCSTATUS._render_bit_blocks(result))

        # 3. 表格视图
        table_title = Text("\n[状态位详细信息]\n")
        table_title.stylize("magenta", 0, len("状态位详细信息"))

        content_parts.append(table_title)
        content_parts.append(ISO14229DTCSTATUS._render_bit_table(result))
        content_parts.append(Text("\n"))

        # 4. 置位bit详细解析
        set_bits = [bit for bit, is_set in result['bits'].items() if is_set]
        if set_bits:
            detail_title = Text("[置位状态位详细解析]\n")
            detail_title.stylize("magenta", 0, len("置位状态位详细解析"))

            content_parts.append(detail_title)

            for bit in sorted(set_bits, reverse=True):  # 从高位到低位
                bit_info = DTCStatusConfig.get_bit_info(bit)
                if bit_info:
                    # 使用Rule作为分隔符，只显示Bit编号和名称
                    content_parts.append(Rule(f"Bit {bit} - {bit_info.name} ({bit_info.abbr})", align="left"))

                    detail_content = ISO14229DTCSTATUS._create_bit_detail_content(bit_info, is_set=True)
                    content_parts.append(detail_content)
                    content_parts.append(Text("\n"))
        else:
            content_parts.append(Text("⚠ 所有状态位均为复位状态\n", style="yellow"))

        # 将所有内容组合
        content = Group(*content_parts)

        # 创建单一Panel，Title靠左对齐
        analysis_panel = Panel(
            content,
            title="DEM故障分析器",
            title_align="center",
            subtitle=f"HEX: {result['hex']} | DEC: {result['decimal']} | BIN: {result['binary']}",
            border_style="cyan",
            box=ROUNDED,
            padding=(1, 2)
        )

        console.print(analysis_panel)

        return output.getvalue()

    @staticmethod
    def _render_bit_blocks(result: Dict) -> Columns:
        """渲染方块视图 - 使用原来的版本但确保一行显示"""
        blocks = []

        # 从高位到低位（Bit7到Bit0）
        for bit in reversed(range(8)):
            is_set = result['bits'][bit]
            bit_info = DTCStatusConfig.get_bit_info(bit)

            if bit_info:
                # 构建方块内容 - 使用原来的格式
                block_content = Text(no_wrap=False)
                block_content.append(f"Bit {bit}\n", style="bold cyan")
                block_content.append(f"{bit_info.abbr}\n", style="bold yellow")

                # 状态名称截断处理
                name_lines = bit_info.name
                if len(name_lines) > 11:
                    name_lines = bit_info.name[:10] + "…"
                block_content.append(f"{name_lines}\n", style="italic")

                # 根据状态添加状态指示
                if is_set:
                    status_text = Text(" 1 ", style="bold white on red")
                else:
                    status_text = Text(" 0 ", style="bold white on green")

                block_content.append(status_text)

                # 创建方块 - 调整为适合一行显示
                block = Panel(
                    block_content,
                    # title=f"Bit {bit}",
                    # subtitle=f"{status_text}",
                    border_style="red" if is_set else "green",
                    width=16,
                    height=6,
                    box=SQUARE,
                    padding=(0, 0)
                )
                blocks.append(block)

        # 使用Columns在一行显示所有方块，增加console宽度确保不换行
        return Columns(blocks, padding=1, expand=False)

    @staticmethod
    def _render_bit_table(result: Dict) -> Table:
        """渲染表格视图 - 完整显示，不截断"""
        # 创建表格
        table = Table(
            show_header=True,
            header_style="bold blue",
            box=SIMPLE,
            show_lines=False,
            width=146
        )

        # 定义列
        table.add_column("位", style="cyan", no_wrap=True, justify="center")
        table.add_column("名称", style="green")
        table.add_column("缩写", style="yellow", no_wrap=True, justify="center")
        table.add_column("状态", style="bold", no_wrap=True, justify="center")
        table.add_column("描述", style="white")

        # 从高位到低位显示（Bit 7 到 Bit 0）
        for bit in reversed(range(8)):
            is_set = result['bits'][bit]
            bit_info = DTCStatusConfig.get_bit_info(bit)

            if bit_info:
                # 获取状态图标和颜色
                status_icon = '✓' if is_set else '✗'

                # 使用彩色文本
                if is_set:
                    status_text = f"[red]{status_icon} SET [/red]"
                else:
                    status_text = f"[green]{status_icon} CLR [/green]"

                # 获取状态描述
                status_desc = bit_info.desc_true if is_set else bit_info.desc_false

                # 添加行
                table.add_row(
                    f"Bit {bit}",
                    bit_info.name,
                    bit_info.abbr,
                    status_text,
                    status_desc
                )

        return table

    @staticmethod
    def _create_bit_detail_content(bit_info: BitInfo, is_set: bool) -> Group:
        """创建位详情内容"""

        # 构建内容
        content_parts = []

        # 1. 状态信息（单独一行）
        if is_set:
            status_line = Text("\n状态: ")
            status_line.append("置位", style="bold red")
        else:
            status_line = Text("状态: ")
            status_line.append("复位", style="bold green")

        content_parts.append(status_line)
        content_parts.append(Text("\n"))

        # 2. 简介（单独一行）
        intro_line = Text(f"简介: {bit_info.intro}")
        content_parts.append(intro_line)
        content_parts.append(Text("\n"))

        # 3. 状态描述
        desc_title = Text(f"状态描述: {bit_info.desc_true if is_set else bit_info.desc_false}")
        content_parts.append(desc_title)
        content_parts.append(Text("\n\n"))

        # 4. 详细说明
        detail_title = Text("详细说明: ")
        detail_title.stylize("cyan", 0, 4)
        detail_text = Text(f"{bit_info.detailed_desc}")
        content_parts.append(detail_title)
        content_parts.append(detail_text)
        content_parts.append(Text("\n"))

        # 5. 置位/清除条件
        if is_set:
            cond_title = Text("置位条件: ")
            cond_title.stylize("cyan", 0, 4)
            content_parts.append(cond_title)
            # content_parts.append(Text("\n"))
            for condition in bit_info.set_conditions:
                content_parts.append(Text(f"  • {condition}\n"))
        else:
            cond_title = Text("清除条件: ")
            cond_title.stylize("cyan", 0, 4)
            content_parts.append(cond_title)
            content_parts.append(Text("\n"))
            for condition in bit_info.clear_conditions:
                content_parts.append(Text(f"  • {condition}\n"))

        return Group(*content_parts)


class DEMFaultAnalyzer:
    """DEM故障分析器业务逻辑类"""

    def __init__(self, plugin_instance):
        """初始化业务逻辑"""
        self.plugin = plugin_instance
        self.log_info("DEM故障分析器业务逻辑初始化完成")

    def log_info(self, msg: str, *args, **kwargs):
        """记录信息日志"""
        self.plugin.log_info(msg, *args, **kwargs)

    def log_warning(self, msg: str, *args, **kwargs):
        """记录警告日志"""
        self.plugin.log_warning(msg, *args, **kwargs)

    def register_commands(self, menu_system: MenuSystem):
        """注册插件命令到菜单系统"""
        # 创建插件的子菜单
        self.create_plugin_submenu(menu_system)

    def create_plugin_submenu(self, menu_system: MenuSystem):
        """创建插件自己的多级菜单"""
        # 创建一级菜单
        dem_main_menu = menu_system.create_submenu(
            menu_id="dem_analyzer_main_menu",
            name="DEM故障分析器",
            description="基于AUTOSAR CP和ETAS DEM的DTC故障状态分析工具",
            icon="🔍"
        )

        # 创建二级菜单 - 故障状态分析
        fault_analysis_menu = menu_system.create_submenu(
            menu_id="fault_analysis_menu",
            name="故障状态分析",
            description="DTC状态位解析和分析",
            icon="📊"
        )

        # 注册故障状态分析命令
        menu_system.register_item(ActionItem(
            id="parse_dtc_status",
            name="DTC状态码分析",
            description="输入DTC状态码进行详细分析",
            command_type=CommandType.PYTHON,
            python_func=self.parse_dtc_status
        ))

        # 将命令添加到菜单
        menu_system.add_item_to_menu("fault_analysis_menu", "parse_dtc_status")

        # 构建菜单结构
        dem_main_menu.add_item("fault_analysis_menu")

        # 将一级菜单添加到主菜单
        menu_system.add_item_to_main_menu("dem_analyzer_main_menu")

    def parse_dtc_status(self) -> str:
        """解析DTC状态码"""
        try:
            # 获取用户输入
            status_input = input("请输入DTC状态码（格式：0x6C 或 6C）: ").strip()

            # 验证输入格式
            if not status_input:
                return "[red]❌ 输入不能为空！[/red]"

            # 处理输入格式
            if not status_input.startswith(('0x', '0X')):
                status_input = '0x' + status_input

            # 验证并解析
            status_int = int(status_input, 16)
            if status_int < 0 or status_int > 255:
                return "[red]❌ 无效的DTC状态码！状态码必须是1字节（0x00-0xFF）。[/red]"

            # 调用分析函数
            return ISO14229DTCSTATUS.format_analysis(status_input)

        except ValueError:
            return "[red]❌ 无效的十六进制格式！请输入有效的DTC状态码。[/red]"
        except Exception as e:
            return f"[red]❌ 解析过程中发生错误：{str(e)}[/red]"