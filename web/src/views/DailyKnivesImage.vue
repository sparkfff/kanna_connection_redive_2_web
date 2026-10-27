<template>
  <main v-if="data" data-status-board class="daily-board">
    <header class="board-heading">
      <div><p>环奈连结 R · 公会战</p><h1>{{ data.label }}<span>{{ data.date }}</span></h1><h2>{{ data.clan_name }}</h2></div>
      <div class="generated">生成于<br />{{ data.generated_at }}</div>
    </header>

    <section class="overview">
      <div class="total"><span>累计出刀</span><strong>{{ data.total }}<small>刀</small></strong><p>完整刀 1 · 尾刀 / 补偿 0.5</p></div>
      <div><span>已满三刀</span><strong class="green">{{ data.complete_count }}<small>人</small></strong><p>{{ data.member_count ? Math.round(data.complete_count / data.member_count * 100) : 0 }}% 已记录成员完成</p></div>
      <div><span>尚未出刀</span><strong class="rose">{{ data.zero_count ?? '—' }}<small v-if="data.zero_count !== null">人</small></strong><p>{{ data.roster_known ? `统计成员 ${data.member_count} 人` : '未获取完整公会名单' }}</p></div>
    </section>

    <section v-if="data.member_count" class="progress-card">
      <div class="progress-title"><span>出刀分布</span><span>共 {{ data.member_count }} 人</span></div>
      <div class="distribution">
        <div v-for="group in data.groups" :key="group.count" :style="{ width: `${group.members.length / data.member_count * 100}%`, background: daoNumColor(group.count) }"></div>
      </div>
      <div class="legend"><span v-for="group in data.groups" :key="group.count"><i :style="{ background: daoNumColor(group.count) }"></i>{{ group.count === 0 ? '未出刀' : `${group.count} 刀` }} · {{ group.members.length }} 人</span></div>
    </section>

    <div v-if="!data.roster_known" class="roster-note">未获取完整公会名单，仅展示有战报的成员，无法列出全部未出刀成员。</div>
    <section v-for="group in data.groups" :key="group.count" class="group-card" :style="{ '--group-color': daoNumColor(group.count) }">
      <div class="group-heading"><span class="count-badge">{{ group.count === 0 ? '未出刀' : `${group.count} 刀` }}</span><span>{{ group.members.length }} 人</span><span v-if="group.count === 3" class="group-hint">已完成</span></div>
      <div class="members"><span v-for="member in group.members" :key="member.id" class="member">{{ member.name }}</span></div>
    </section>
    <section v-if="!data.groups.length" class="empty">暂无出刀记录</section>
    <footer>每日 05:00（UTC+8）换日 · 每位成员最多计 3 刀<br />{{ data.roster_known ? '未出刀成员依据最近获取的公会名单，昨日统计使用同一名单' : '未出刀人数未知，破折号不表示零人' }}</footer>
  </main>
  <div v-else class="no-payload">此页面由机器人生成出刀统计图片，不通过网址读取群数据。</div>
</template>

<script setup lang="ts">
import { daoNumColor } from '@/utils/dao'

interface DailyImageData {
  label: string
  date: string
  clan_name: string
  generated_at: string
  roster_known: boolean
  total: number
  member_count: number
  complete_count: number
  zero_count: number | null
  groups: Array<{ count: number; members: Array<{ id: string; name: string }> }>
}
const data = (window as Window & { __KANNA_STATUS__?: DailyImageData }).__KANNA_STATUS__
</script>

<style scoped>
.daily-board { width: 960px; box-sizing: border-box; padding: 32px; background: #f6f7fc; color: #273448; font-family: 'Microsoft YaHei', 'PingFang SC', 'Noto Sans CJK SC', sans-serif; }
.board-heading { display: flex; justify-content: space-between; gap: 20px; align-items: center; margin-bottom: 26px; }
.board-heading p { color: #9794b5; font-size: 13px; letter-spacing: 2px; margin: 0 0 7px; }
h1 { font-size: 32px; line-height: 1.4; margin: 0; }
h1 span { margin-left: 14px; font-size: 16px; font-weight: 400; color: #9a9eb3; }
h2 { font-size: 16px; font-weight: 400; color: #7c8397; margin: 5px 0 0; overflow-wrap: anywhere; }
.generated { text-align: right; font-size: 12px; color: #9a9eb3; line-height: 1.8; flex-shrink: 0; }
.overview { display: grid; grid-template-columns: 1.1fr 1fr 1fr; border-radius: 18px; padding: 22px 0; margin-bottom: 18px; background: white; border: 1px solid #ececf5; box-shadow: 0 5px 16px #24265706; }
.overview > div { padding: 0 24px; min-width: 0; }
.overview > div + div { border-left: 1px solid #eff0f7; }
.overview span { font-size: 15px; color: #7d839a; }
.overview strong { display: block; font-size: 43px; line-height: 1.6; color: #6963c8; }
.overview small { margin-left: 6px; font-size: 16px; font-weight: 400; color: #9297aa; }
.overview p { margin: 0; color: #a1a6b7; font-size: 12px; }
.overview .green { color: #10b981; }
.overview .rose { color: #ec637b; }
.progress-card { background: white; padding: 18px 22px; border: 1px solid #ececf5; border-radius: 14px; margin-bottom: 22px; }
.progress-title { display: flex; justify-content: space-between; color: #7d839a; font-size: 13px; margin-bottom: 12px; }
.distribution { display: flex; height: 13px; border-radius: 8px; overflow: hidden; gap: 3px; }
.legend { display: flex; flex-wrap: wrap; gap: 10px 16px; margin-top: 12px; font-size: 12px; color: #9297aa; }
.legend i { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 5px; }
.group-card { background: white; border: 1px solid #ececf5; border-left: 4px solid var(--group-color); border-radius: 13px; padding: 17px 20px; margin-top: 13px; }
.group-heading { display: flex; align-items: center; gap: 12px; font-size: 13px; color: #a1a6b7; margin-bottom: 12px; }
.count-badge { font-weight: 700; font-size: 17px; color: var(--group-color); }
.group-hint { margin-left: auto; color: #10b981; font-size: 12px; }
.members { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 9px; }
.member { background: color-mix(in srgb, var(--group-color) 8%, white); border: 1px solid color-mix(in srgb, var(--group-color) 18%, white); border-radius: 8px; font-size: 15px; padding: 8px 11px; line-height: 1.5; overflow-wrap: anywhere; }
.roster-note { color: #ab8747; background: #fff8e8; padding: 12px 16px; border-radius: 10px; margin: 16px 0; font-size: 13px; }
.empty { text-align: center; color: #a1a6b7; padding: 48px; background: white; border-radius: 14px; }
footer { text-align: center; color: #a1a6b7; font-size: 12px; line-height: 1.9; margin-top: 22px; }
.no-payload { padding: 32px; }
</style>
