"""Format queries using the same carryover reconstruction as attack typing."""

from ..util.carryover import remaining_carries
from ..util.knife_policy import game_day


def format_remaining_carries(records, timestamp, player_id=None, name=None):
    day = game_day(timestamp)
    players = {}
    for record in records or []:
        if game_day(record.time) == day and (player_id is None or record.pcrid == player_id):
            players.setdefault(record.pcrid, []).append(record)
    title = f"今日剩余补偿（{day}，05:00换日）"
    if not players:
        return title + '\n' + (f"{name or player_id}：" if player_id is not None else '') + '今日暂无已记录战报。'
    lines = []
    for _, attacks in sorted(players.items()):
        attacks.sort(key=lambda record: (record.time, record.id or 0))
        player_name = attacks[-1].name
        remaining = remaining_carries(attacks)
        if remaining is None:
            lines.append(f"{player_name}：记录不足或存在冲突，无法确认")
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
        if detail or player_id is not None:
            lines.append(f"{player_name}：{detail or '暂无剩余补偿'}")
    return title + '\n' + ('\n'.join(lines) if lines else '当前未发现剩余补偿。') + '\n按本群今日已记录战报推算。'
