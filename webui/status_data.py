"""Boss snapshot shared by the dashboard API and group status image."""

from ..util.auto_boss import clan_boss_info


def build_boss_status(clan_info=None):
    bosses = []
    for index, info in enumerate(clan_boss_info.boss_info[:5]):
        boss = clan_info.boss[index] if clan_info and index < len(clan_info.boss) else None
        bosses.append({
            "name": info.name,
            "id": info.boss_id,
            "current_hp": boss.current_hp if boss else 0,
            "max_hp": boss.max_hp if boss else 0,
            "lap": boss.lap_num if boss else 0,
            "fighter": boss.fighter_num if boss else 0,
        })
    return bosses
