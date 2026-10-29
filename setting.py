from enum import Enum
from pathlib import Path
from .basedata import FilePath


class ClientSetting(Enum):
    """
    有关client的设置
    clanbattle_semaphore：会战查询最大并发量
    jjc_semaphore：会战查询最大并发量
    """

    clanbattle_max = 66
    jjc_max = 33


class TimeAxisLimit(Enum):
    """
    分刀限制
    max_calculate：最大计算量
    max_result：最大获取结果数
    max_query：一个boss显示几个作业
    single_limit：一个阶段中一个boss显示几个作业
    """

    max_calculate = 114514
    max_result = 3
    max_query = 8
    single_limit = 3


class JJCSetting(Enum):
    """
    竞技场设置
    buff_path：缓存储存路径
    query_local：作业网查询方法
    """

    buff_path = Path(__file__).parent.parent / "priconne" / "arena" / "buffer"
    query_local = True


class WebSetting(Enum):
    """
    网页端！！！
    api_host/api_port：后端 FastAPI 监听地址（与 nonebot 同进程启动）
    web_host/web_port：前端访问地址（QQ 机器人回复的登录链接会使用这个）
    api_base：后端接口统一前缀

    注意：web_host 请改为你部署机器的内网 IP（如 192.168.x.x），
    手机/其他设备需通过该地址访问前端；仅本机访问可用 127.0.0.1
    """

    api_host = "0.0.0.0"
    api_port = "12138"
    api_base = "/kanna_dependency"
    web_host = "127.0.0.1"  # ← 改成你自己的内网 IP，例如 192.168.1.100
    web_port = "5173"
    web_base = "/kanna_connection"
    # 机器人所在机器能访问的 WebUI 截图页面；生产部署时改成实际前端地址。
    status_image_url = "http://127.0.0.1:5173/#/status-image"
    # 留空使用 playwright install chromium 安装的浏览器；Windows 可设 msedge。
    status_image_browser_channel = ""
    # 等待头像、Boss图标及字体的最长时间；超时使用现有占位样式。
    status_image_asset_timeout_ms = 2000


class BossData(Enum):
    """
    会战boss数据，主要为网页端服务
    """

    use_online = True
    info_path = FilePath.data.value / "boss_info.json"
