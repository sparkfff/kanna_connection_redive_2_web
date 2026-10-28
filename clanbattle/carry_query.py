"""Format queries using the same carryover reconstruction as attack typing."""

from ..util.carryover import remaining_carries
from ..util.knife_policy import game_day


def remaining_carry_members(records, timestamp, player_id=None):
    day = game_day(timestamp)
    players = {}
    for record in records or []:
        if game_day(record.time) == day and (player_id is None or record.pcrid == player_id):
            players.setdefault(record.pcrid, []).append(record)
    members = []
    for pcrid, attacks in sorted(players.items()):
        attacks.sort(key=lambda record: (record.time, record.id or 0))
        player_name = attacks[-1].name
        remaining = remaining_carries(attacks)
        if remaining is None:
            members.append(dict(pcrid=pcrid, name=player_name, detail='记录不足或存在冲突，无法确认', uncertain=True, has_remaining=True))
            continue
        certain, uncertain = [], []
        for seconds, minimum, maximum in remaining:
            label = f'{seconds}s' if seconds else '秒数未知'
            if minimum:
                certain.append(f'{label}×{minimum}')
            if maximum > minimum:
                uncertain.append(f'{label}×0～{maximum - minimum}')
        detail = '、'.join(certain)
        if uncertain:
            detail += ('；另有待确认：' if detail else '待确认：') + '、'.join(uncertain)
        members.append(dict(pcrid=pcrid, name=player_name, detail=detail or '暂无剩余补偿', uncertain=bool(uncertain) or any(seconds == 0 for seconds, _, _ in remaining), has_remaining=bool(detail)))
    return members


def format_remaining_carries(records, timestamp, player_id=None, name=None):
    title = f"今日剩余补偿（{game_day(timestamp)}，05:00换日）"
    members = remaining_carry_members(records, timestamp, player_id)
    if not members:
        return title + '\n' + (f"{name or player_id}：" if player_id is not None else '') + '今日暂无已记录战报。'
    lines = [f"{member['name']}：{member['detail']}" for member in members if member['has_remaining'] or player_id is not None]
    return title + '\n' + ('\n'.join(lines) if lines else '当前未发现剩余补偿。') + '\n按本群今日已记录战报推算。'
