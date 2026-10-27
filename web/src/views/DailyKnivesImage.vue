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
.daily-board { width: 512px; box-sizing: border-box; padding: 8px; background: var(--kanna-page-bg); color: var(--kanna-text); font-family: 'Microsoft YaHei', 'PingFang SC', 'Noto Sans CJK SC', sans-serif; }
.distribution-card { background: var(--kanna-card-bg); padding: 16px; border-radius: 12px; }
header { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 12px; font-size: 18px; color: var(--kanna-heading); }
header span { font-size: 13px; color: var(--kanna-text-secondary); }
.daily-board :deep(.el-table) { font-size: 14px; }
.daily-board :deep(.el-table th.el-table__cell) { color: var(--kanna-text-secondary); }
.daily-board :deep(.dao-num-badge) { font-size: 15px; line-height: 22px; padding: 3px 6px; }
.daily-board :deep(.dist-player-tag) { font-size: 15px; line-height: 22px; padding: 2px 6px; font-weight: 500; }
.roster-note { color: var(--kanna-text-secondary); font-size: 13px; line-height: 1.6; margin: 10px 0 0; }
.no-payload { padding: 32px; }
</style>
