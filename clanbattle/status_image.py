"""Render the WebUI's group status board without a web account or public API."""

import asyncio
import base64
import json
import time
from urllib.parse import urlsplit

from ..basedata import NoticeType
from ..database.dal import pcr_sqla
from ..setting import WebSetting
from ..webui.status_data import build_boss_status

# Bound simultaneous browser instances; every request gets an isolated context.
_render_lock = asyncio.Lock()


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
                "text": notice.text or "",
                "lap": notice.lap or 0,
            })
    records = await pcr_sqla.get_day_rcords(now, group_id)
    records = records or []
    running = bool(clan_info.loop_check)
    return {
        "clan_name": clan_info.clan_name or f"群 {group_id}",
        "stage": clan_info.period,
        "rank": clan_info.rank,
        "state": ("开启（高占用）" if now - clan_info.loop_check > 30 else "开启") if running else "关闭 · 保留最后进度",
        "monitor_name": names.get(int(clan_info.user_id), str(clan_info.user_id)),
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
        "full_count": sum(record.flag == 0 for record in records),
        "tail_count": sum(record.flag == 1 for record in records),
        "carry_count": sum(record.flag == 0.5 for record in records),
        "boss": bosses,
    }


async def render_status_image(payload):
    # Lazy import: deployments without Playwright still retain text status.
    from playwright.async_api import async_playwright

    url = WebSetting.status_image_url.value
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError("WebSetting.status_image_url 必须是已部署 WebUI 的 HTTP(S) 地址")
    async with _render_lock:
        async with async_playwright() as playwright:
            options = {"headless": True}
            channel = WebSetting.status_image_browser_channel.value
            if channel:
                options["channel"] = channel
            browser = await playwright.chromium.launch(**options)
            try:
                page = await browser.new_page(
                    viewport={"width": 960, "height": 960},
                    device_scale_factor=1.5, locale="zh-CN", color_scheme="light",
                )
                # No token, account credentials, or data-bearing public URL.
                # Data enters only this browser context, never a server endpoint.
                await page.add_init_script(
                    "window.__KANNA_STATUS__ = " + json.dumps(payload, ensure_ascii=True) + ";"
                )
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                board = page.locator("[data-status-board]")
                await board.wait_for(state="visible", timeout=20000)
                await page.evaluate("document.fonts.ready")
                await page.evaluate("""async () => {
                    await Promise.all(Array.from(document.querySelectorAll('[data-status-board] img')).map(img => {
                        if (img.complete) return Promise.resolve();
                        return new Promise(resolve => {
                            img.addEventListener('load', resolve, {once: true});
                            img.addEventListener('error', resolve, {once: true});
                            setTimeout(resolve, 4000);
                        });
                    }));
                    document.documentElement.classList.remove('dark');
                }""")
                image = await board.screenshot(type="png", animations="disabled", timeout=15000)
                return "[CQ:image,file=base64://" + base64.b64encode(image).decode("ascii") + "]"
            finally:
                await browser.close()
