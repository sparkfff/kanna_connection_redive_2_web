from ..client import tw_pcrclient
from ..database.dal import pcr_sqla
from ..util.clan_schedule import clan_schedule


async def sync_first_day_carry(group_id, clan_info=None):
    policy = await pcr_sqla.get_first_day_carry_policy(group_id)
    if not policy["enabled"] or not policy.get("automatic"):
        return policy
    # Do not use CN calendar dates for other servers, or infer a period from
    # the local month / first monitoring date.
    battle_id = getattr(clan_info, "clan_battle_id", 0)
    client = getattr(clan_info, "client", None)
    if not battle_id or client is None or isinstance(client, tw_pcrclient):
        return dict(policy, date="")
    if policy.get("battle_id") == battle_id and policy["date"]:
        return policy
    day = await clan_schedule.first_day(battle_id)
    if not day:
        return dict(policy, date="")
    count = await pcr_sqla.set_first_day_carry_policy(
        group_id, True, day, automatic=True, battle_id=battle_id, resolve_only=True,
    )
    policy = await pcr_sqla.get_first_day_carry_policy(group_id)
    return dict(policy, corrected_count=count)
