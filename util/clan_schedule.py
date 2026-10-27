"""Resolve CN clan-battle first days by exact battle ID, with a durable cache."""

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import httpx
from loguru import logger

from ..basedata import FilePath
from .knife_policy import first_day_window, game_day


def schedule_dates(entries):
    dates = {}
    for entry in entries:
        try:
            battle_id = int(entry["clanBattleId"])
            start = datetime.fromisoformat(entry["startTime"].replace("Z", "+00:00"))
            if battle_id <= 0 or start.utcoffset() is None:
                continue
            dates[str(battle_id)] = game_day(start.timestamp())
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    return dates


class ClanSchedule:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.Lock()
        self.last_attempt = None
        try:
            dates = json.loads(self.path.read_text(encoding="utf-8"))
            self.dates = {}
            if isinstance(dates, dict):
                for key, day in dates.items():
                    try:
                        first_day_window(day)
                        if int(key) > 0:
                            self.dates[str(key)] = day
                    except (TypeError, ValueError):
                        continue
        except (OSError, ValueError):
            self.dates = {}

    async def first_day(self, battle_id):
        key = str(battle_id)
        with self.lock:
            if key in self.dates:
                return self.dates[key]
            now = time.monotonic()
            if self.last_attempt is not None and now - self.last_attempt < 300:
                return None
            self.last_attempt = now
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get("https://pcr.satroki.tech/api/Quest/GetClanBattleInfos", params={"s": "cn"})
                response.raise_for_status()
                entries = response.json()
            if not isinstance(entries, list):
                raise ValueError("invalid clan battle schedule response")
            dates = schedule_dates(entries)
            with self.lock:
                self.dates.update(dates)
                snapshot = dict(self.dates)
            # Keep the fetched dates even if disk persistence fails.
            temporary = self.path.with_name(self.path.name + "." + uuid4().hex + ".tmp")
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                temporary.write_text(json.dumps(snapshot), encoding="utf-8")
                os.replace(temporary, self.path)
            except OSError as e:
                logger.warning(f"会战日程缓存保存失败：{e}")
            finally:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
            return snapshot.get(key)
        except Exception as e:
            logger.warning(f"自动获取会战日程失败：{e}")
            return None


clan_schedule = ClanSchedule(FilePath.data.value / "clan_battle_schedule_cn.json")
