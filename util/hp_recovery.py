"""Reconstruct kills only inside a verified, complete game-log interval."""


def log_key(log):
    return log.target_viewer_id, log.lap_num, log.order_num, log.battle_end_time


def record_key(record):
    return record.pcrid, record.lap, record.boss, record.time


def recover_caps(records, logs, max_hp):
    """Caller must supply stable, fully fetched pages for the current period.

    Require the preceding lap's confirmed kill in the same fetched interval,
    every target-lap report uniquely stored, and a single final confirmed kill.
    """
    by_key = {}
    for record in records:
        by_key.setdefault(record_key(record), []).append(record)
    fetched = {}
    for log in logs:
        key = log_key(log)
        if key in fetched:
            return {}, {}
        fetched[key] = log
    groups = {}
    for key in fetched:
        groups.setdefault((key[1], key[2]), []).append(key)
    caps, raw = {}, {}
    for (lap, boss), keys in groups.items():
        if any(len(by_key.get(key, [])) != 1 for key in keys):
            continue
        rows = sorted((by_key[key][0] for key in keys), key=lambda r: r.time)
        if len({r.time for r in rows}) != len(rows):
            continue
        kill = rows[-1]
        if not kill.kill_confirmed or kill.boss_hp or any(r.kill_confirmed for r in rows[:-1]):
            continue
        anchor = [by_key[k][0] for k in groups.get((lap - 1, boss), [])
                  if len(by_key.get(k, [])) == 1 and by_key[k][0].kill_confirmed]
        if len(anchor) != 1 or anchor[0].time >= rows[0].time:
            continue
        maximum = max_hp.get((lap, boss), 0)
        # A stored nonkill must agree with the freshly fetched detailed log.
        if not isinstance(maximum, int) or maximum <= 0 or any(
            r.damage != fetched[record_key(r)].total_damage or r.damage < 0 for r in rows[:-1]
        ):
            continue
        remaining = maximum - sum(r.damage for r in rows[:-1])
        key = record_key(kill)
        original = max(kill.raw_damage, kill.damage, fetched[key].total_damage)
        if 0 < remaining <= original:
            caps[key] = remaining
            raw[key] = original
    return caps, raw
