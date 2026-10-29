"""Explicit game-day policy for guilds carrying 90-second attacks on day one."""

from datetime import datetime, timedelta, timezone

GAME_TZ = timezone(timedelta(hours=8))


def daily_knife_total(records):
    """Same daily display rule everywhere: 1/.5 per attack, max 3 per player."""
    players = {}
    for record in records or []:
        players[record.pcrid] = players.get(record.pcrid, 0) + (1 if record.flag == 0 else .5)
    return sum(min(count, 3) for count in players.values())


def game_day(timestamp):
    return (datetime.fromtimestamp(timestamp, GAME_TZ) - timedelta(hours=5)).strftime("%Y-%m-%d")


def first_day_window(day):
    start = datetime.strptime(day, "%Y-%m-%d").replace(hour=5, tzinfo=GAME_TZ)
    return int(start.timestamp()), int((start + timedelta(days=1)).timestamp())


def first_day_carry_active(policy, timestamp):
    return bool(policy and policy.get("enabled") and policy.get("date") == game_day(timestamp))


def classify_knife(start_time, battle_time, killed, timestamp, policy=None):
    # Preserve directly identifiable short carryovers, including when they kill.
    if start_time < 90:
        return 0.5
    if killed or battle_time < start_time:
        return 1
    return 0.5 if first_day_carry_active(policy, timestamp) else 0
