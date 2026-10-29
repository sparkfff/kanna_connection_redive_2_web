"""Render the WebUI's group status board without a web account or public API."""

import base64
import re
import time
from urllib.parse import urlsplit

from ..basedata import NoticeType
from ..database.dal import pcr_sqla, pcr_date
from ..setting import WebSetting
from ..webui.status_data import build_boss_status
from .carry_query import remaining_carry_members
from ..util.knife_policy import daily_knife_total



def build_help_payload(text):
    groups = {name: [] for name in ('战报与查询', '出刀协作', '监控与设置', '管理操作')}
    notes = []
    for line in text.splitlines():
        match = re.match(r'^【([^】]+)】\s*(.*)$', line.strip())
        if not match:
            if line.strip():
                notes.append(line.strip().lstrip('* '))
            continue
        command, description = match.groups()
        if command.startswith(('清空', '启用肃正', '修正出刀', 'kpi调整', '删除kpi')):
            group = '管理操作'
        elif command.startswith(('出刀监控', '取消出刀监控', '开启', '关闭', '首日满补')):
            group = '监控与设置'
        elif command.startswith(('预约 +', '取消预约', '上树', '挂树', '下树', '申请', '进1', '取消申请', 'sl')):
            group = '出刀协作'
        else:
            group = '战报与查询'
        groups[group].append(dict(command=command, description=description))
    return dict(sections=[dict(title=title, commands=commands) for title, commands in groups.items() if commands], notes=notes)


async def build_status_payload(bot, group_id, clan_info):
    now = int(time.time())
    names = {}
    try:
        for member in await bot.get_group_member_list(group_id=group_id):
            names[int(member["user_id"])] = member.get("card") or member.get("nickname") or str(member["user_id"])
    except Exception:
        pass
    bosses = build_boss_status(clan_info)
    for boss in bosses:
        boss.update(subscribe=[], apply=[], tree=[])
    for label, kind in (
        ("subscribe", NoticeType.subscribe.value),
        ("apply", NoticeType.apply.value),
        ("tree", NoticeType.tree.value),
    ):
        notices = await pcr_sqla.get_notice(kind, group_id, max_age_hours=24)
        for notice in notices or []:
            if not 1 <= notice.boss <= len(bosses):
                continue
            bosses[notice.boss - 1][label].append({
                "name": names.get(int(notice.user_id), str(notice.user_id)),
                "qq_id": str(notice.user_id),
                "text": notice.text or "",
                "lap": notice.lap or 0,
            })
    records = await pcr_sqla.get_day_rcords(now, group_id)
    records = records or []
    remaining = [member for member in remaining_carry_members(records, now) if member['has_remaining']]
    player_qqs = await pcr_sqla.get_group_player_qqs(group_id, names.keys()) if remaining else {}
    for member in remaining:
        member['qq_id'] = player_qqs.get(member['pcrid'])
    running = bool(clan_info.loop_check)
    return {
        "clan_name": clan_info.clan_name or f"群 {group_id}",
        "stage": clan_info.period,
        "rank": clan_info.rank,
        "state": ("开启（高占用）" if now - clan_info.loop_check > 30 else "开启") if running else "关闭 · 保留最后进度",
        "monitor_name": names.get(int(clan_info.user_id), str(clan_info.user_id)),
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
        "full_count": sum(record.flag == 0 for record in records),
        "daily_count": daily_knife_total(records),
        "tail_count": sum(record.flag == 1 for record in records),
        "carry_count": sum(record.flag == 0.5 for record in records),
        "remaining_carries": remaining,
        "boss": bosses,
    }


def build_daily_payload(stats, clan_name, target_time, label, roster_known):
    groups = {count: [] for count in (3, 2.5, 2, 1.5, 1, 0.5, 0)}
    total = 0
    for player_id, name, count in stats:
        count = min(count, 3)
        groups[count].append({"id": str(player_id), "name": name})
        total += count
    return {
        "clan_name": clan_name,
        "label": label,
        "date": pcr_date(target_time).strftime("%Y-%m-%d"),
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "roster_known": roster_known,
        "total": total,
        "member_count": len(stats),
        "complete_count": len(groups[3]),
        "zero_count": len(groups[0]) if roster_known else None,
        "groups": [{"count": count, "members": members} for count, members in groups.items() if members],
    }


def build_rank_lines_payload(result):
    """Use the same cached ranking response as the dashboard and QQ query."""
    data = result["data"]
    return {
        "clan_battle_id": data["clan_battle_id"],
        "lines": data.get("lines") or [],
        "my": data.get("my"),
        "updated_at": int(result.get("updated_at") or 0),
        "cached": bool(result.get("cached")),
        "stale": bool(result.get("stale")),
    }


async def render_status_image(payload, view="status"):
    from ..util.image_renderer import get_image_renderer

    url = WebSetting.status_image_url.value
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError("WebSetting.status_image_url 必须是已部署 WebUI 的 HTTP(S) 地址")
    if view == "daily":
        # Reuse the configured frontend origin and deployment subpath.
        url = parts._replace(fragment="/daily-knives-image").geturl()
    elif view == "rank":
        url = parts._replace(fragment="/rank-lines-image").geturl()
    elif view == "help":
        url = parts._replace(fragment="/clan-help-image").geturl()
    elif view != "status":
        raise ValueError("未知的截图页面")
    result = await get_image_renderer().render(
        url, payload, view, WebSetting.status_image_browser_channel.value,
        WebSetting.status_image_asset_timeout_ms.value,
    )
    return "[CQ:image,file=base64://" + base64.b64encode(result).decode("ascii") + "]"
