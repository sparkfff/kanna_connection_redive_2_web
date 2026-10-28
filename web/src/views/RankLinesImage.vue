<template>
  <main v-if="data" data-status-board class="rank-board">
    <header>
      <b>会战档线</b>
      <el-tag v-if="data.clan_battle_id" size="small" type="info" effect="plain">编号 {{ data.clan_battle_id }}</el-tag>
      <el-tag v-if="updatedText" size="small" :type="data.stale ? 'warning' : data.cached ? 'info' : 'success'" effect="plain">
        {{ data.stale ? '缓存' : '数据' }} {{ updatedText }}
      </el-tag>
    </header>
    <RankLineTable :lines="data.lines" :my="data.my" :details="false" omit-empty />
  </main>
  <div v-else class="no-payload">此页面由机器人生成分数线图片，不通过网址读取群数据。</div>
</template>

<script setup lang="ts">
import RankLineTable from '@/components/RankLineTable.vue'
import type { RankLinesImageData } from '@/types/rankLinesImage'

const data = (window as Window & { __KANNA_STATUS__?: RankLinesImageData }).__KANNA_STATUS__
const updatedText = data?.updated_at
  ? new Intl.DateTimeFormat('zh-CN', { timeZone: 'Asia/Shanghai', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false })
      .format(new Date(data.updated_at * 1000)).replace('/', '-')
  : ''
</script>

<style scoped>
.rank-board {
  width: 700px;
  box-sizing: border-box;
  padding: 16px 12px 12px;
  border-radius: 12px;
  background: var(--kanna-card-bg);
  color: var(--kanna-text);
  font-family: 'Microsoft YaHei', 'PingFang SC', 'Noto Sans CJK SC', sans-serif;
}
header { display: flex; align-items: center; gap: 7px; margin-bottom: 8px; }
header b { color: var(--kanna-heading); font-size: 15px; }
.rank-board :deep(.el-table) { font-size: 13px; }
.rank-board :deep(.rank-score) { font-size: 14px; white-space: nowrap; }
.rank-board :deep(.el-table .cell) { line-height: 23px; padding: 0 7px; }
.rank-board :deep(.el-table td.el-table__cell) { padding: 4px 0; }
.rank-board :deep(.el-table th.el-table__cell) { color: var(--kanna-text-secondary); }
.no-payload { padding: 32px; }
</style>
