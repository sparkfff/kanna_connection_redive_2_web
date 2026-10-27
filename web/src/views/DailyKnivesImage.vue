<template>
  <main v-if="data" data-status-board class="daily-board">
    <section class="distribution-card">
      <header><b>{{ data.label }}分布</b><span>{{ data.date }}</span></header>
      <KnifeDistribution :rows="rows" />
      <p v-if="!data.roster_known" class="roster-note">未获取完整公会名单，仅显示有战报的成员。</p>
    </section>
  </main>
  <div v-else class="no-payload">此页面由机器人生成出刀统计图片，不通过网址读取群数据。</div>
</template>

<script setup lang="ts">
import KnifeDistribution from '@/components/KnifeDistribution.vue'
interface DailyImageData {
  label: string
  date: string
  roster_known: boolean
  groups: Array<{ count: number; members: Array<{ id: string; name: string }> }>
}
const data = (window as Window & { __KANNA_STATUS__?: DailyImageData }).__KANNA_STATUS__
const rows = data?.groups.map(group => ({ dao_num: group.count, names: group.members.map(member => member.name) })) || []
</script>

<style scoped>
.daily-board { width: 512px; box-sizing: border-box; padding: 8px; background: #fff0d6; font-family: 'Microsoft YaHei', 'PingFang SC', 'Noto Sans CJK SC', sans-serif; }
.distribution-card { background: #fff; padding: 20px; border-radius: 12px; }
header { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 12px; font-size: 14px; color: #a8184b; }
header span { font-size: 11px; color: #a1a6b7; }
.roster-note { color: #a17b3c; font-size: 11px; line-height: 1.6; margin: 10px 0 0; }
.no-payload { padding: 32px; }
</style>
