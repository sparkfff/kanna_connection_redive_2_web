<template>
  <main v-if="data" data-status-board class="status-board">
    <header class="board-header">
      <div><p>环奈连结 R · 会战状态</p><h1>{{ data.clan_name }}</h1></div>
      <div class="timestamp">{{ data.generated_at }}<br />监控：{{ data.state }}</div>
    </header>
    <div class="board-columns">
      <div class="board-column">
        <section class="summary">
          <div class="summary-stats">
            <div class="stat pink"><span>今日出刀</span><strong>{{ data.full_count + (data.tail_count + data.carry_count) / 2 }}</strong></div>
            <div class="stat purple"><span>阶段</span><strong>{{ data.stage || '—' }}</strong></div>
            <div class="stat blue"><span>当前排名</span><strong>{{ data.rank || '—' }}</strong></div>
          </div>
          <div class="summary-line">完整刀 <b>{{ data.full_count }}</b><i>·</i>尾刀 <b>{{ data.tail_count }}</b><i>·</i>补偿刀 <b>{{ data.carry_count }}</b></div>
          <div class="summary-line">监控人：{{ data.monitor_name }}</div>
          <div class="carry-roster">
            <span class="carry-label">剩余<br />补偿</span>
            <div v-if="data.remaining_carries?.length" class="carry-members">
              <span v-for="member in data.remaining_carries" :key="member.pcrid" class="carry-member" :class="{ uncertain: member.uncertain }">
                <b>{{ member.name }}</b><span>{{ member.detail }}</span>
              </span>
            </div>
            <span v-else class="carry-empty">暂无已记录的剩余补偿</span>
          </div>
        </section>
        <StatusBossCard v-for="(boss, index) in data.boss.slice(0, 2)" :key="index" :boss="boss" :order="index + 1" :lap-level="bossLapLevel(boss.lap, data.boss)" />
      </div>
      <div class="board-column">
        <StatusBossCard v-for="(boss, index) in data.boss.slice(2)" :key="index" :boss="boss" :order="index + 3" :lap-level="bossLapLevel(boss.lap, data.boss)" />
      </div>
    </div>
    <footer class="board-footer">刀数及剩余补偿按今日战报推算 · 预约/申请/挂树显示近 24 小时记录<br />近期入场人数来自游戏接口，不代表全部未结算成员</footer>
  </main>
  <div v-else class="no-payload">此页面由机器人生成状态图片，不通过网址读取群数据。</div>
</template>

<script setup lang="ts">
import StatusBossCard from '@/components/StatusBossCard.vue'
import type { StatusImageData } from '@/types/statusImage'
import { bossLapLevel } from '@/utils/boss'

// The bot injects the payload before navigation. No public group-id endpoint,
// login bypass, URL credentials, localStorage or cross-page session is needed.
const data = (window as Window & { __KANNA_STATUS__?: StatusImageData }).__KANNA_STATUS__
</script>

<style scoped>
.status-board { width: 960px; padding: 24px; box-sizing: border-box; background: #f8efcc; color: #342d25; font-family: 'Microsoft YaHei', 'PingFang SC', 'Noto Sans CJK SC', sans-serif; }
.board-header { display: flex; justify-content: space-between; align-items: center; gap: 24px; margin-bottom: 20px; }
.board-header p { margin: 0 0 5px; font-size: 13px; letter-spacing: 2px; color: #978456; }
h1 { font-size: 26px; line-height: 1.3; margin: 0; overflow-wrap: anywhere; }
.timestamp { text-align: right; color: #8b7957; line-height: 1.8; font-size: 13px; flex-shrink: 0; }
.board-columns { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; align-items: start; }
.board-column { display: flex; flex-direction: column; gap: 18px; min-width: 0; }
.summary { background: #fffdf2; padding: 16px; border-radius: 14px; border: 1px solid white; box-shadow: 0 5px 0 #dacf9e50; }
.summary-stats { display: grid; grid-template-columns: 1fr .8fr 1fr; gap: 10px; margin-bottom: 12px; }
.stat { padding: 10px 6px; text-align: center; border-radius: 10px; }
.stat span { display: block; font-size: 15px; }
.stat strong { display: block; font-size: 30px; line-height: 1.4; }
.pink { background: #ffd2d7; color: #b84355; }
.purple { background: #e8d5fa; color: #7d44b2; }
.blue { background: #d9edf8; color: #397e9e; }
.summary-line { line-height: 1.9; font-size: 15px; color: #7a6c55; overflow-wrap: anywhere; }
.summary-line i { font-style: normal; padding: 0 12px; }
.carry-roster { display: flex; align-items: center; gap: 10px; margin-top: 10px; padding: 9px; background: #efefec; border-radius: 7px; font-size: 14px; }
.carry-label { flex: none; line-height: 1.5; font-weight: bold; color: #655c50; }
.carry-members { display: flex; flex-wrap: wrap; gap: 6px; min-width: 0; }
.carry-member { display: inline-flex; flex-wrap: wrap; gap: 3px 7px; max-width: 100%; padding: 3px 8px; border-radius: 9px; background: #dedfd9; line-height: 1.5; overflow-wrap: anywhere; }
.carry-member.uncertain { background: #fff0cc; color: #8a601c; }
.carry-empty { flex: 1; text-align: center; color: #8b8173; }
.board-footer { font-size: 12px; line-height: 1.8; color: #978456; margin-top: 20px; text-align: center; }
.no-payload { padding: 32px; }
</style>
