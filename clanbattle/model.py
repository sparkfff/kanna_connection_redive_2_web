import asyncio
import contextlib
import time
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List

from loguru import logger

from ..basedata import ItemID, NoticeType, stage_dict
from ..client import (
    BaseClient,
    LoadIndexResponse,
    check_client,
)
from ..client.response import (
    BattleInfo,
    ClanBattleLogListResponse,
    ClanBattleTopResponse,
)
from ..database.dal import pcr_sqla
from ..database.models import RecordDao
from ..errorclass import CancelledError
from ..login import run_group
from ..util.task_pool import PoolBase, PrioritizedQueryItemBase
from ..util.tools import anywhere_send
from ..util.auto_boss import clan_boss_info
from ..util.knife_policy import classify_knife, first_day_carry_active, game_day
from .base import find_item, format_bignum, format_precent
from .damage_correction import DamageCorrectionTracker
from .carry_schedule import sync_first_day_carry
from ..util.hp_recovery import log_key, recover_caps

from traceback import format_exc


class ClanBattle:
    def __init__(self, group_id: int) -> None:
        self.rank = 0  # 会战排名
        self.lap_num = 0  # 周目（会战周目，boss可能多一周目）
        self.loop_num = 0  # 循环编号
        self.error_count = 0  # 失败计数
        self.loop_check = 0  # 循环检查(时间戳)
        self.group_id = group_id
        self.client = None  # 登录后由 init() 赋值；先占位，避免未初始化时属性不存在
        self.notice_dao = []
        self.notice_attacks = []
        self.hp_recovery_time = 0
        self.notice_tree = []
        self.notice_fighter = []
        self.notice_subscribe = []
        self.boss = [Boss(), Boss(), Boss(), Boss(), Boss()]
        self.clan_name = ""
        self.period = ""
        self.dao_update_time = 0  # 网页端更新标记
        self.damage_correction = DamageCorrectionTracker()
        self.fighter_update_time = 0  # 网页端战斗人数更新标记
        self.rank_update_time = 0  # 网页端会战排名更新标记

    def set_rank(self, rank) -> bool:
        """更新会战排名，返回排名是否真的变了。

        **只有变了才推进 `rank_update_time`**：网页端仪表盘的 SSE 只在
        `dao_update_time` / `fighter_update_time` / `rank_update_time` 前进时才推送，
        而排名是游戏侧每半小时刷一次、跟本团有没有人出刀无关。以前直接
        `clan_info.rank = ...` 不打戳，于是「没人出刀」时排名变了前端也收不到，
        卡片一直显示旧值、手动刷新页面才变（2026-09-24 用户报的现象）。
        """
        new_rank = int(rank or 0)
        if new_rank == self.rank:
            return False
        self.rank = new_rank
        self.rank_update_time = int(time.time())
        return True

    async def init(self, client: BaseClient, user_id: int, bot_id: int):
        self.loop_num += 1
        self.client = client
        self.bot_id = bot_id
        self.user_id = user_id
        for _ in range(3):
            with contextlib.suppress(Exception):
                home_index = await self.client.home_index()
                self.clan_id = home_index.user_clan.clan_id
                self.coin = await self.get_coin()
                clan_battle_top = await self.get_clanbattle_top()
                break
        else:
            home_index = await self.client.home_index()
            self.clan_id = home_index.user_clan.clan_id
            self.coin = await self.get_coin()
            clan_battle_top = await self.get_clanbattle_top()

        self.clan_battle_id = clan_battle_top.clan_battle_id
        self.clan_name = clan_battle_top.user_clan.clan_name
        self.lap_num = clan_battle_top.lap_num
        self.period = clan_boss_info.lap2stage(self.lap_num)
        self.refresh_latest_time(clan_battle_top)
        self.damage_correction.reset(clan_battle_top)
        await sync_first_day_carry(self.group_id, self)
        await pcr_sqla.reclassify_carry_day(self.group_id, game_day(time.time()))
        self.members: Dict[int, str] = await self.all_member()
        self.dao_update_time = int(time.time())

    async def get_coin(self) -> int:
        load_index: LoadIndexResponse = await self.client.load_index()
        return find_item(load_index.item_list, ItemID.clanbattle_coin.value)

    async def in_clan_battle(self) -> bool:
        """当前是否处于会战期间（供播报类定时任务判断该不该发）。

        load/index 的 clan_battle 里有两个相关字段：
          - now_open：1 表示会战开放中（首选）
          - is_interval：1 表示处于休赛期（参考项目 pcrjjc2-clanbattle 用的就是这个）
        优先看 now_open，它没数据时退回 is_interval；两者都拿不到就按「非会战期间」处理，
        宁可不播报，也不要在休赛期天天误播。
        """
        if self.client is None:
            return False
        try:
            load_index: LoadIndexResponse = await self.client.load_index()
        except Exception as e:
            logger.warning(f"获取会战开放状态失败 group={self.group_id}: {e}")
            return False

        clan_battle = load_index.clan_battle
        if clan_battle is None:
            logger.warning(
                f"load/index 未返回 clan_battle，按非会战期间处理 group={self.group_id}"
            )
            return False

        if clan_battle.now_open is not None:
            is_open = clan_battle.now_open == 1
        elif clan_battle.is_interval is not None:
            is_open = clan_battle.is_interval != 1
        else:
            is_open = False

        logger.info(
            f"会战开放状态 group={self.group_id} now_open={clan_battle.now_open} "
            f"is_interval={clan_battle.is_interval} 会战期间={is_open}"
        )
        return is_open

    async def get_clanbattle_top(self) -> ClanBattleTopResponse:
        try:
            return await self.client.clan_battle_top(self.clan_id, self.coin)
        except Exception:
            self.coin = await self.get_coin()  # 更新coin
            return await self.client.clan_battle_top(self.clan_id, self.coin)

    async def refresh_fighter_num(self, lap_num: int, order: int) -> int:
        boss = self.boss[order - 1]
        try:
            if boss.current_hp:
                reload_detail_info = await self.client.clan_battle_detail_info(
                    self.clan_id, self.clan_battle_id, lap_num, order
                )
                if reload_detail_info.fighter_num != boss.fighter_num:
                    boss.fighter_num = reload_detail_info.fighter_num
                    # 战斗人数变化时同步打网页端标记，让 renew_dashboard 的 SSE 能感知并推送
                    self.fighter_update_time = int(time.time())
                    return reload_detail_info.fighter_num
        except Exception:
            return 0
        return 0  # 0不播报，没改变不报，改变了是0也不报

    async def get_battle_log(self, page: int) -> ClanBattleLogListResponse:
        return await self.client.clan_battle_log(page, self.clan_battle_id)

    async def add_record(self, loop_num: int):
        # The API's sort_type does not prove which page is newest. Scan all
        # pages and compare stored keys, so old failures cannot hide new logs.
        try:
            first = await self.get_battle_log(1)
        except Exception:
            logger.exception(f"Battle log page 1 failed, group={self.group_id}")
            return
        logs = list(first.battle_list or [])
        pages = first.max_page if isinstance(first.max_page, int) and first.max_page > 0 else 1
        for page in range(2, pages + 1):
            if loop_num != self.loop_num:
                raise CancelledError
            try:
                result = await self.get_battle_log(page)
                logs.extend(result.battle_list or [])
            except Exception:
                logger.exception(f"Battle log page {page} failed, group={self.group_id}")
        if not logs:
            return
        unique = []
        seen = set()
        for record in logs:
            identity = (record.battle_log_id, record.target_viewer_id, record.lap_num,
                        record.order_num, record.battle_end_time, record.total_damage)
            if record.battle_log_id is not None and identity in seen:
                continue
            seen.add(identity)
            unique.append(record)
        counts = Counter(log_key(record) for record in unique)
        self.damage_correction.invalidate_keys({key for key, count in counts.items() if count > 1})
        timestamps = [record.battle_end_time for record in unique]
        existing = await pcr_sqla.get_record_keys_between(self.group_id, min(timestamps), max(timestamps))
        pending = []
        for record in sorted(unique, key=lambda r: r.battle_end_time):
            if loop_num != self.loop_num:
                raise CancelledError
            key = log_key(record)
            if key in existing:
                continue
            try:
                item = await self.general_single_record(
                    record, record.battle_end_time, allow_damage_correction=counts[key] == 1,
                )
                pending.append(item)
            except Exception:
                # Do not advance past a failed detail permanently: the next
                # scan checks all keys again rather than just the latest time.
                logger.exception(f"Battle detail failed, group={self.group_id}, log={record.battle_log_id}, key={key}")
        if pending:
            await pcr_sqla.add_record(pending)


    async def general_single_record(
        self, record: BattleInfo, time: int, allow_damage_correction: bool = True
    ) -> RecordDao:
        pcrid = record.target_viewer_id
        time_line = await self.client.time_line_report(
            pcrid, self.clan_battle_id, record.battle_log_id
        )
        policy = await sync_first_day_carry(self.group_id, self)
        key = (pcrid, record.lap_num, record.order_num, time)
        killed = allow_damage_correction and self.damage_correction.is_kill(record)
        flag = classify_knife(time_line.start_remain_time, time_line.battle_time, killed, time, policy)
        temp_dict = {
            "group_id": self.group_id,
            "battle_log_id": time % 10000000,  # 这玩意居然会重复，受不了，直接取时间
            "name": record.user_name,
            "lap": record.lap_num,
            "boss": record.order_num,
            "damage": (
                self.damage_correction.record_damage(record)
                if allow_damage_correction else record.total_damage
            ),
            "time": time,
            "pcrid": pcrid,
            "remain_time": time_line.start_remain_time,
            "battle_time": time_line.battle_time,
            "raw_damage": self.damage_correction.raw_damage(record) if allow_damage_correction else record.total_damage,
            "boss_hp": (self.damage_correction.cap_for(key) or 0) if allow_damage_correction else 0,
            "kill_confirmed": killed,
            "knife_source": "policy" if flag == .5 and time_line.start_remain_time == 90 and first_day_carry_active(policy, time) else "timing",
            "own_units": ','.join(str(unit.unit_id) for unit in record.units if getattr(unit, 'viewer_id', None) == pcrid),
            "flag": flag,
        }
        for i, unit in enumerate(record.units):
            temp_dict[f"unit{i+1}"] = unit.unit_id
            temp_dict[f"unit{i+1}_level"] = unit.unit_level
            temp_dict[f"unit{i+1}_damage"] = unit.damage
            temp_dict[f"unit{i+1}_rarity"] = unit.unit_rarity
            temp_dict[f"unit{i+1}_rank"] = unit.promotion_level
            temp_dict[f"unit{i+1}_unique_equip"] = (
                unit.unique_equip_slot[0].enhancement_level
                if unit.unique_equip_slot
                else 0
            )
        return RecordDao(**temp_dict)

    async def notice_text(self, order: int, lap: int, item: int) -> str:
        # 只认 24 小时内的预约：避免上一期会战的陈旧预约在下一期被翻出来误触发。
        # get / delete 必须传同一个 max_age_hours，否则会出现「记录删了但没通知」。
        if not (
            info := await pcr_sqla.get_notice(
                item, self.group_id, order, lap, max_age_hours=24
            )
        ):
            return ""

        # 清除需通知成员
        await pcr_sqla.delete_notice(
            item, self.group_id, order, lap=lap, max_age_hours=24
        )

        if item == NoticeType.apply.value:
            return ""

        notice_users = " ".join([f"[CQ:at,qq={notice.user_id}]" for notice in info])

        if item == NoticeType.subscribe.value:
            return f"{notice_users}\n你们预约的{order}王出现了"
        if item == NoticeType.tree.value:
            return "以下成员将自动下树：\n" + notice_users

    async def send_notice(self, types: List[int]):
        """把攒下的通知发到群里。

        **预约（subscribe）穿透「主动推送」开关** —— 那个开关管的是「群播报」
        （出刀人数 / 出刀伤害 / 挂树），而预约是用户**点名要的**提醒：他在网页端
        或 QQ 群明确说了「这个王出现时叫我」，关播报不该连带把他的预约一起吞掉。
        其余几类仍受开关控制：关了就不发，并把攒下的清空 —— 否则关推送期间会
        一直往里堆，等重新开启时一次性全倒出来，比不开还吵。

        顺序要紧：`notice_text` 取到待通知的人时**已经把库里的记录删掉了**
        （见 `notice_text`），所以预约必须在这里真的发出去，不能因为开关被丢弃。

        开关按群独立，见 `dal.get_push_enabled`。
        """
        push_enabled = await pcr_sqla.get_push_enabled(self.group_id)

        # 预约不受开关影响，先发
        if NoticeType.subscribe.value in types:
            await anywhere_send(
                "\n".join(self.notice_subscribe), self.group_id, self.bot_id
            )
            self.notice_subscribe.clear()

        if not push_enabled:
            self.notice_fighter.clear()
            self.notice_dao.clear()
            self.notice_tree.clear()
            return

        if NoticeType.fighter.value in types:
            await anywhere_send(
                "\n".join(self.notice_fighter), self.group_id, self.bot_id
            )
            self.notice_fighter.clear()
        if NoticeType.dao.value in types:
            await anywhere_send(
                "\n".join(self.notice_dao[::-1]), self.group_id, self.bot_id
            )
            self.notice_dao.clear()
        if NoticeType.tree.value in types:
            await anywhere_send("\n".join(self.notice_tree), self.group_id, self.bot_id)
            self.notice_tree.clear()

    async def refresh_boss(self, clan_battle_top: ClanBattleTopResponse) -> bool:
        change = False
        # 获取当前血量,当前王数
        for i, boss in enumerate(self.boss):
            current_boss = clan_battle_top.boss_info[i]
            # 通知预约
            if current_boss.current_hp and (
                subscribe_text := await self.notice_text(
                    current_boss.order_num,
                    current_boss.lap_num,
                    NoticeType.subscribe.value,
                )
            ):
                self.notice_subscribe.append(subscribe_text)
                # 查看当前出刀人数
            if fighter_num := await self.refresh_fighter_num(
                current_boss.lap_num, current_boss.order_num
            ):
                self.notice_fighter.append(f"{i+1}王当前有{fighter_num}人出刀")
            if (
                current_boss.current_hp != boss.current_hp
                or current_boss.lap_num != boss.lap_num
            ):
                change = True
                boss.refresh(
                    current_boss.current_hp,
                    current_boss.lap_num,
                    current_boss.order_num,
                    current_boss.max_hp,
                )
        return change

    async def record_change(self, clan_battle_top: ClanBattleTopResponse):
        for history in self.damage_correction.update(clan_battle_top):
            if await pcr_sqla.clear_finished_application(
                self.group_id, history.viewer_id, history.order_num,
                history.lap_num, history.create_time,
            ):
                from . import notice_update_time

                notice_update_time[self.group_id] = int(time.time())
            damage = self.damage_correction.history_damage(history)
            correction = (
                f"（原始伤害{history.damage}）"
                if damage < history.damage else ""
            )
            self.notice_attacks.append((history, damage, correction, 0))
            # 通知挂树，清空申请出刀
            if history.kill:
                if offtree_text := await self.notice_text(
                    history.order_num, 0, NoticeType.tree.value
                ):
                    self.notice_tree.append(offtree_text)
                await self.notice_text(history.order_num, 0, NoticeType.apply.value)

        self.dao_update_time = int(time.time())
        self.refresh_latest_time(clan_battle_top)

    async def build_attack_notices(self):
        pending = []
        for history, damage, correction, attempts in self.notice_attacks:
            suffix = ''
            if history.kill:
                record = await pcr_sqla.get_attack_record(self.group_id, (
                    history.viewer_id, history.lap_num, history.order_num, history.create_time,
                ))
                if record is None and attempts < 2:
                    pending.append((history, damage, correction, attempts + 1))
                    continue
                if record is not None and record.carry_seconds > 0:
                    suffix = f"获得了{record.carry_seconds}s的返还时间。"
            self.notice_dao.append(
                f"{history.name}对{history.lap_num}周目{history.order_num}王造成{damage}点伤害"
                f"{'并击破' if history.kill else ''}{correction}。{suffix}"
            )
        self.notice_attacks = pending

    async def reconcile_damage(self):
        # A detailed report can become visible after top was fetched in the
        # previous iteration. Fix that already-saved row as well as new inserts.
        pending = dict(self.damage_correction.pending_caps)
        kills = set(self.damage_correction.pending_kills)
        if pending or kills:
            raw = {key: self.damage_correction.raw_for_key(key) for key in (*pending, *kills)}
            await pcr_sqla.correct_kill_damage(self.group_id, pending, kills, raw)
            for key, cap in pending.items():
                if self.damage_correction.pending_caps.get(key) == cap:
                    del self.damage_correction.pending_caps[key]
            self.damage_correction.pending_kills.difference_update(kills)

    async def recover_missing_hp(self, top):
        now = time.time()
        if now - self.hp_recovery_time < 120:
            return
        today = await pcr_sqla.get_day_rcords(int(now), self.group_id)
        if not any(r.kill_confirmed and not r.boss_hp for r in today or []):
            return
        self.hp_recovery_time = now
        battle_id = self.clan_battle_id
        try:
            first = await self.get_battle_log(1)
            if not first.battle_list or not first.max_page:
                return
            logs = list(first.battle_list)
            signature = [(r.battle_log_id, log_key(r), r.total_damage) for r in first.battle_list]
            for page in range(2, first.max_page + 1):
                result = await self.get_battle_log(page)
                if result.max_page != first.max_page or not result.battle_list:
                    return
                logs.extend(result.battle_list)
            check = await self.get_battle_log(1)
            if (self.clan_battle_id != battle_id or check.max_page != first.max_page
                    or signature != [(r.battle_log_id, log_key(r), r.total_damage) for r in check.battle_list or []]):
                return
            times = [r.battle_end_time for r in logs]
            records = await pcr_sqla.get_recovery_records(self.group_id, min(times), max(times))
            # Validate the configured phase's HP against the live game response.
            # Cross-phase history without a matching live maximum is skipped.
            live = {b.order_num: b.max_hp for b in top.boss_info or []}
            maximums = {}
            for r in records:
                maximum = clan_boss_info.get_boss_max(r.lap, r.boss)
                if maximum > 0 and maximum == live.get(r.boss):
                    maximums[r.lap, r.boss] = int(maximum)
            caps, raw = recover_caps(records, logs, maximums)
            if caps:
                await pcr_sqla.correct_kill_damage(self.group_id, caps, set(caps), raw)
        except Exception as e:
            logger.warning(f"会战血量恢复暂未完成 group={self.group_id}: {e}")

    async def all_member(self):
        clan = await self.client.clan_info(self.clan_id)
        return {player.viewer_id: player.name for player in clan.clan.members}

    def refresh_latest_time(self, clan_battle_top: ClanBattleTopResponse) -> int:
        self.latest_time = (
            clan_battle_top.damage_history[0].create_time
            if clan_battle_top.damage_history
            else 0
        )

    def general_boss(self) -> str:
        return (
            "当前进度："
            + f"{self.period}面{stage_dict[self.period]}阶段\n"
            + "\n".join([boss.boss_info() for boss in self.boss])
        )


class Boss:
    def __init__(self) -> None:
        self.stage = 0
        self.order = 0
        self.max_hp = 0
        self.lap_num = 0
        self.stage_num = 0
        self.current_hp = 0
        self.fighter_num = 0

    def refresh(self, current_hp, lap_num, order, max_hp):
        self.current_hp = current_hp
        self.lap_num = lap_num
        self.order = order
        self.max_hp = max_hp
        self.stage = clan_boss_info.lap2stage(lap_num)
        self.stage_num = stage_dict[self.stage]

    def boss_info(self):
        msg = f"{self.lap_num}周目{self.order}王: "
        if self.current_hp:
            msg += f"HP: {format_bignum(self.current_hp)}/{format_bignum(self.max_hp)} {format_precent(self.current_hp/self.max_hp)}"
            if self.fighter_num:
                msg += f" 当前有{self.fighter_num}人挑战"
        else:
            msg += "无法挑战"
        return msg


@dataclass
class ClanbattleItem:
    clan_info: ClanBattle
    loop_num: int


class PrioritizedQueryItem(PrioritizedQueryItemBase):
    data: ClanbattleItem


class ClanBattlePool(PoolBase):
    async def do_single(self, item: PrioritizedQueryItem):
        clan_info: ClanBattle = item.data.clan_info
        loop_num: int = item.data.loop_num
        async with ClanbattleHandle(clan_info, loop_num):
            if loop_num != clan_info.loop_num:
                raise CancelledError

            clan_info.loop_check = time.time()

            # 初始化
            clan_battle_top = await clan_info.get_clanbattle_top()
            if clan_battle_top.clan_battle_id and clan_battle_top.clan_battle_id != clan_info.clan_battle_id:
                clan_info.clan_battle_id = clan_battle_top.clan_battle_id
                clan_info.damage_correction.reset(clan_battle_top)
                clan_info.period = clan_boss_info.lap2stage(clan_battle_top.lap_num) if clan_battle_top.lap_num else ""
            await sync_first_day_carry(clan_info.group_id, clan_info)
            clan_info.lap_num = clan_battle_top.lap_num
            # 用 set_rank 而不是直接赋值：排名变了要打推送标记，网页端卡片才会自己更新
            clan_info.set_rank(clan_battle_top.period_rank)

            # 换面提醒
            if clan_battle_top.lap_num:  # 有时候网络不好这个就直接是none了
                if clan_info.period < (
                    temp := clan_boss_info.lap2stage(clan_battle_top.lap_num)
                ):
                    await anywhere_send(
                        f"会战阶段从{clan_info.period}面到了{temp}面，请注意轴的切换喵",
                        clan_info.group_id,
                        clan_info.bot_id,
                    )
                    clan_info.period = temp

                    # 刷新状态，提醒预约
            await clan_info.refresh_boss(clan_battle_top)
            await clan_info.send_notice(
                [NoticeType.subscribe.value, NoticeType.fighter.value]
            )

            # Damage histories can change even when a snapshot's HP does not.
            await clan_info.record_change(clan_battle_top)
            await clan_info.add_record(loop_num)
            await clan_info.reconcile_damage()
            await clan_info.recover_missing_hp(clan_battle_top)
            await clan_info.build_attack_notices()
            await clan_info.send_notice(
                [NoticeType.dao.value, NoticeType.tree.value]
            )
            clan_info.error_count = 0
        asyncio.create_task(
            self.add_task(
                PrioritizedQueryItem(data=ClanbattleItem(clan_info, loop_num)),
                int(time.time() - clan_info.loop_check),
                True,
                f"会战群{str(clan_info.group_id)}",
            )
        )


class ClanbattleHandle:
    def __init__(self, clan_info: ClanBattle, loop_num: int) -> None:
        self.clan_info = clan_info
        self.loop_num = loop_num

    async def __aenter__(self):
        run_group[self.clan_info.group_id] = self.clan_info.bot_id
        self.clan_info.loop_check = time.time()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            return

        self.clan_info.loop_check = 0
        if self.clan_info.group_id in run_group:
            del run_group[self.clan_info.group_id]

        if self.loop_num != self.clan_info.loop_num:
            self.clan_info.dao_update_time = int(time.time())
            await anywhere_send(
                f"#编号HN000{self.loop_num}监控已关闭",
                self.clan_info.group_id,
                self.clan_info.bot_id,
            )
            return

        if not await check_client(self.clan_info.client):
            self.clan_info.dao_update_time = int(time.time())
            await anywhere_send(
                "当前账号被顶号，出刀监控已退出",
                self.clan_info.group_id,
                self.clan_info.bot_id,
            )
            return

        if self.clan_info.error_count > 3:
            self.clan_info.error_count = 0
            self.clan_info.dao_update_time = int(time.time())
            await anywhere_send(
                f"超过最大重试次数，出刀监控已退出,{exc_value}: {traceback}",
                self.clan_info.group_id,
                self.clan_info.bot_id,
            )
            return

        logger.error(
            f"公会战{self.clan_info.user_id}发生错误，{exc_value}: {traceback}"
        )
        print(format_exc())
        self.clan_info.loop_check = time.time()
        self.clan_info.error_count += 1
        run_group[self.clan_info.group_id] = self.clan_info.bot_id
        return True
