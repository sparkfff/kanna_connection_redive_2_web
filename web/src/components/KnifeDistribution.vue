<template>
  <el-table :data="rows" size="small" stripe style="width: 100%">
    <el-table-column label="刀数" width="100">
      <template #default="{ row }">
        <div class="dao-num-badge" :style="{ background: daoNumColor(row.dao_num) }">
          {{ row.dao_num === 0 ? '未出刀' : row.dao_num + ' 刀' }}
        </div>
      </template>
    </el-table-column>
    <el-table-column label="玩家">
      <template #default="{ row }">
        <span v-for="(name, i) in row.names" :key="i" class="dist-player-tag" :style="tagStyle(row.dao_num)">{{ name }}</span>
        <span v-if="!row.names?.length" class="text-muted text-sm">暂无</span>
      </template>
    </el-table-column>
    <el-table-column label="人数" width="80" align="center">
      <template #default="{ row }"><b>{{ row.names?.length || 0 }}</b></template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import type { ReportItem } from '@/types'
import { daoNumColor } from '@/utils/dao'
defineProps<{ rows: ReportItem[] }>()
function tagStyle(count: number) {
  const color = daoNumColor(count)
  return { background: color + '1a', borderColor: color + '59', color }
}
</script>

<style scoped>
.dao-num-badge { display: inline-block; min-width: 52px; text-align: center; padding: 3px 10px; border-radius: 6px; color: #fff; font-size: 13px; font-weight: 600; line-height: 18px; box-shadow: 0 1px 2px #0f172a26, inset 0 0 0 1px #fff3; }
.dist-player-tag { display: inline-block; max-width: 100%; box-sizing: border-box; margin: 2px 4px 2px 0; padding: 1px 8px; border-radius: 4px; border: 1px solid transparent; font-size: 12px; line-height: 18px; white-space: normal; overflow-wrap: anywhere; }
</style>
