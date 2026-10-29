"""Warm screenshot browser, isolated request contexts, bounded static cache."""

import asyncio
import hashlib
import json
import time
import weakref
from collections import OrderedDict


class ImageRenderer:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.playwright = None
        self.browser = None
        self.channel = None
        self.idle_handle = None
        self.cache = OrderedDict()
        self.last_used = 0

    async def close(self):
        async with self.lock:
            await self._close()

    async def _close_if_idle(self):
        async with self.lock:
            # A timer task may have queued behind a newer render. Do not close
            # a browser that has just been used while that task was waiting.
            if time.monotonic() - self.last_used >= 300:
                await self._close()

    async def _close(self):
        if self.idle_handle:
            self.idle_handle.cancel()
            self.idle_handle = None
        browser, playwright = self.browser, self.playwright
        self.browser = self.playwright = None
        try:
            if browser:
                await browser.close()
        finally:
            if playwright:
                await playwright.stop()

    async def render(self, url, payload, view, channel='', asset_timeout_ms=2000):
        asset_timeout_ms = max(500, min(int(asset_timeout_ms), 10000))
        key = hashlib.sha256(json.dumps([url, payload, view, channel, asset_timeout_ms], sort_keys=True).encode()).hexdigest()
        async with self.lock:
            cached = self.cache.get(key) if view == 'help' else None
            if cached and time.monotonic() - cached[0] < 300:
                self.cache.move_to_end(key)
                return cached[1]
            if self.idle_handle:
                self.idle_handle.cancel()
                self.idle_handle = None
            try:
                if self.browser and (not self.browser.is_connected() or self.channel != channel):
                    await self._close()
                if not self.browser:
                    from playwright.async_api import async_playwright
                    self.playwright = await async_playwright().start()
                    self.browser = await self.playwright.chromium.launch(headless=True, **({'channel': channel} if channel else {}))
                    self.channel = channel
                context = await self.browser.new_context(
                    viewport={'width': {'daily': 512, 'rank': 700, 'help': 840}.get(view, 960), 'height': 960},
                    device_scale_factor=2 if view in ('daily', 'rank', 'help') else 1.5,
                    locale='zh-CN', color_scheme='dark' if view == 'daily' else 'light',
                )
                try:
                    page = await context.new_page()
                    await page.add_init_script(
                        'window.__KANNA_STATUS__ = ' + json.dumps(payload, ensure_ascii=True) + ';'
                        + "localStorage.setItem('kanna.theme.v1', " + json.dumps('dark' if view == 'daily' else 'light') + ');'
                    )
                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    board = page.locator('[data-status-board]')
                    await board.wait_for(state='visible', timeout=20000)
                    await page.evaluate('timeout => Promise.race([document.fonts.ready, new Promise(resolve => setTimeout(resolve, timeout))])', asset_timeout_ms)
                    await page.evaluate("""async timeout => {
                        await Promise.all(Array.from(document.querySelectorAll('[data-status-board] img')).map(img => {
                            if (img.complete) return Promise.resolve();
                            return new Promise(resolve => {
                                let timer;
                                const done = () => {
                                    clearTimeout(timer);
                                    img.removeEventListener('load', done);
                                    img.removeEventListener('error', done);
                                    resolve();
                                };
                                img.addEventListener('load', done, {once: true});
                                img.addEventListener('error', done, {once: true});
                                timer = setTimeout(() => {
                                    // Use existing avatar/icon error fallbacks
                                    // instead of capturing a forever-loading image.
                                    img.removeAttribute('src');
                                    img.dispatchEvent(new Event('error'));
                                    done();
                                }, timeout);
                            });
                        }));
                    }""", asset_timeout_ms)
                    # Let Vue apply error-fallback DOM updates before capturing.
                    await page.evaluate('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
                    result = await board.screenshot(type='png', animations='disabled', timeout=15000)
                finally:
                    await context.close()
                if view == 'help' and len(result) <= 16 * 1024 * 1024:
                    self.cache[key] = (time.monotonic(), result)
                    while len(self.cache) > 8 or sum(len(entry[1]) for entry in self.cache.values()) > 16 * 1024 * 1024:
                        self.cache.popitem(last=False)
                return result
            except BaseException:
                # Includes cancellation: discard a possibly broken connection.
                await self._close()
                raise
            finally:
                if self.browser:
                    self.last_used = time.monotonic()
                    self.idle_handle = asyncio.get_running_loop().call_later(300, lambda: asyncio.create_task(self._close_if_idle()))


_renderers = weakref.WeakKeyDictionary()


def get_image_renderer():
    loop = asyncio.get_running_loop()
    if loop not in _renderers:
        _renderers[loop] = ImageRenderer()
    return _renderers[loop]
