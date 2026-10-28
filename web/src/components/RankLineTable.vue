<template>
        <el-table
          class="rankline-table"
          :data="rows"
          size="small"
          v-loading="loading"
          :row-class-name="rankRowClass"
          style="margin-top: 8px"
        >
          <el-table-column label="档位" width="104" align="center">
            <template #default="{ row }">
              <!-- 用普通 span 而不是 el-tag：el-tag 会把 --el-tag-text-color 定义在自身、
                   且 scoped 的 [data-v] 落点不确定，导致自定义配色被组件默认蓝压掉。
                   自己写标签样式和 .last-rank-name 一样，scoped 稳定生效。 -->
              <span
                class="rank-tag"
                :class="[row.medal ? `medal-${row.medal}` : '', row.isMy ? 'is-my' : '']"
              >
                <!-- 前三名加金银铜奖杯：同一个 Trophy 图标，靠 CSS 上三种颜色 -->
                <el-icon v-if="row.medal" class="rank-tag-trophy"><Trophy /></el-icon>
                <span>{{ row.rank }} 名</span>
              </span>
            </template>
          </el-table-column>
          <el-table-column label="合计分数" min-width="120" align="center">
            <template #default="{ row }">
              <b
                v-if="row.damage !== null"
                class="rank-score"
                :class="[row.medal ? `medal-text-${row.medal}` : '', row.isLast ? 'last-rank-name' : '']"
              >{{ row.damage.toLocaleString() }}</b>
              <span v-else class="text-muted">无</span>
            </template>
          </el-table-column>
          <el-table-column label="守线公会" min-width="130" align="center">
            <template #default="{ row }">
              <span :class="[row.medal ? `medal-text-${row.medal}` : '', row.isLast ? 'last-rank-name' : '', !row.medal && row.isMy ? 'my-clan-name' : '']">{{ row.clan_name || '--' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="会长" width="130" align="center">
            <template #default="{ row }">{{ row.leader_name || '--' }}</template>
          </el-table-column>
          <el-table-column label="人数" width="60" align="center">
            <template #default="{ row }">{{ row.member_num ?? '--' }}</template>
          </el-table-column>
          <el-table-column v-if="details" label="档位奖励" min-width="150" align="center">
            <template #default="{ row }">
              <span v-if="row.reward" class="reward-cell">
                💎{{ row.reward.gem }} · 🪙{{ row.reward.coin }} · 🧩{{ row.reward.shard }}
              </span>
              <span v-else class="text-muted">--</span>
            </template>
          </el-table-column>
          <el-table-column v-if="details" label="我会差距" min-width="160" align="center">
            <template #default="{ row }">
              <template v-if="my && my.rank">
                <span v-if="row.isMy && my.damage !== null" class="gap-ok">
                  当前 {{ my.damage.toLocaleString() }}
                </span>
                <template v-else-if="my.rank <= row.rank">
                  <span v-if="row.damage !== null && my.damage !== null" class="gap-ok">
                    超出 {{ (my.damage - row.damage).toLocaleString() }}
                  </span>
                  <span v-else-if="row.damage === null" class="text-muted">无</span>
                  <el-tag v-else type="success" effect="light" size="small">已达标</el-tag>
                </template>
                <template v-else-if="row.damage !== null && my.damage !== null">
                  <span :class="my.damage >= row.damage ? 'gap-ok' : 'gap-lack'">
                    {{ my.damage >= row.damage ? `超出 ${(my.damage - row.damage).toLocaleString()}` : `还差 ${(row.damage - my.damage).toLocaleString()}` }}
                  </span>
                </template>
                <span v-else class="text-muted">无</span>
              </template>
              <span v-else class="text-muted">--</span>
            </template>
          </el-table-column>
        </el-table>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RankLine } from '@/api'

const props = withDefaults(defineProps<{
  lines: (RankLine | null)[]
  my: RankLine | null
  ranks?: number[]
  loading?: boolean
  details?: boolean
  omitEmpty?: boolean
}>(), { ranks: () => [], loading: false, details: true, omitEmpty: false })

// null 档位补全为占位行，保证表格按请求顺序展示；
// 我会若不在档位列表中，按排名顺序动态插入并高亮
interface RankRow extends RankLine {
  isMy?: boolean
  /** 服务器实际最后一名公会所在档位（后端会自动把它追加进档位列表），用绿色高亮 */
  isLast?: boolean
  /** 前三名：'gold' 1 名 / 'silver' 2 名 / 'bronze' 3 名。
   *  1/2/3 名各用金 / 银 / 铜三色区分，**不加奖杯图标**。 */
  medal?: Medal | null
}
const rows = computed<RankRow[]>(() => {
  const rows: RankRow[] = props.lines.map(
    (line, i) => {
      const row: RankRow =
        line ? { ...line } : {
          rank: props.ranks[i] ?? i + 1,
          damage: null,
          clan_name: null,
          leader_name: null,
          leader_viewer_id: null,
          member_num: null,
          reward: null,
          kind: '',
        }
      row.isLast = row.kind === 'last'
      // kind 为空串/undefined 时为 null —— 普通档位不上榜单色
      row.medal = MEDALS.includes(row.kind as string) ? (row.kind as Medal) : null
      return row
    }
  )
  const my = props.my
  if (my && my.rank) {
    // 排名恰好等于某档位时，直接高亮该行
    const exist = rows.find((r) => r.rank === my.rank)
    if (exist) {
      exist.isMy = true
    } else {
      // 本公会档位奖励 = 我会已达成的最高档位（首个排名 >= 我会排名的档位）
      const achieved = rows.find((r) => r.rank >= my.rank!)
      const myRow: RankRow = { ...my, reward: achieved?.reward ?? null, isMy: true }
      // 表格按档位升序展示：插到第一个比我排名靠后的档位之前
      const idx = rows.findIndex((r) => r.rank > my.rank!)
      if (idx === -1) rows.push(myRow)
      else rows.splice(idx, 0, myRow)
    }
  }
  // 兜底：旧版后端（或旧缓存）没有 kind 字段时，仍按「有数据档位里 rank 最大者」
  // 反推末位，保住绿色高亮。**这条兜底不能删** —— kind 是新加字段，旧缓存里没有，
  // 删掉就会让末位色整片消失（2026-09-25 实际踩过）。
  if (!rows.some((r) => r.isLast)) {
    let lastRank: number | null = null
    for (const r of rows) {
      if (r.damage === null || r.damage === undefined) continue
      if (lastRank === null || r.rank > lastRank) lastRank = r.rank
    }
    const lastRow = lastRank === null ? null : rows.find((r) => r.rank === lastRank)
    if (lastRow) lastRow.isLast = true
  }
  return props.omitEmpty ? rows.filter(row => Boolean(row.clan_name?.trim())) : rows
})

// 前三名的 kind 取值（后端 clanbattle.base._MEDAL_KINDS 同序）
const MEDALS: string[] = ['gold', 'silver', 'bronze']
type Medal = 'gold' | 'silver' | 'bronze'

// 行底色优先级：本会 > 前三名 > 末位。
// 前三名和末位一般不会同时落在同一行（只有服务器只有一两家公会时才会撞上），
// 真撞了也让榜单色赢 —— 名次的意义更强。
// 1/2/3 名各用金 / 银 / 铜三色区分（不加奖杯图标，只靠底色与文字色）。
const rankRowClass = ({ row }: { row: RankRow }) =>
  row.isMy
    ? 'my-clan-row'
    : row.medal
      ? `medal-row-${row.medal}`
      : row.isLast
        ? 'last-rank-row'
        : ''

</script>

<style scoped>
/* 我会所在档线行：粉色高亮 */
:deep(.el-table__body tr.my-clan-row > td.el-table__cell) {
  background: var(--kanna-primary-soft);
}
:deep(.el-table__body tr.my-clan-row:hover > td.el-table__cell) {
  background: var(--kanna-hover-strong);
}
.my-clan-name {
  color: var(--kanna-accent-text);
  font-weight: 600;
}
/* —— 前三名：金 / 银 / 铜三色区分（不加奖杯图标）——
   浅底 + 深字。底色负责「一眼看出名次段」，文字用同色系深色版 ——
   深色版才能保证在浅底上看得清（浅底放浅金会糊成一片）。
   银用偏冷的钢灰而不是纯灰，否则跟普通行的白底分不出来。 */
:deep(.el-table__body tr.medal-row-gold > td.el-table__cell) {
  background: #fffbeb;
}
:deep(.el-table__body tr.medal-row-gold:hover > td.el-table__cell) {
  background: #fef3c7;
}
:deep(.el-table__body tr.medal-row-silver > td.el-table__cell) {
  background: #f4f4f6;
}
:deep(.el-table__body tr.medal-row-silver:hover > td.el-table__cell) {
  background: #e7e7ec;
}
:deep(.el-table__body tr.medal-row-bronze > td.el-table__cell) {
  background: #fdf3ea;
}
:deep(.el-table__body tr.medal-row-bronze:hover > td.el-table__cell) {
  background: #fae3d0;
}
/* 前三名的合计分数与公会名：比标签色再深一档 */
.medal-text-gold {
  color: #92400e;
  font-weight: 600;
}
.medal-text-silver {
  color: #475569;
  font-weight: 600;
}
.medal-text-bronze {
  color: #8a3d10;
  font-weight: 600;
}

/* 名次标签：自己实现（替代 el-tag），基础样式 + 前三名金 / 银 / 铜 */
.rank-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  box-sizing: border-box;
  height: 24px;
  padding: 0 9px;
  border: 1px solid var(--kanna-border-strong);
  border-radius: 4px;
  background: var(--kanna-surface-solid);
  color: var(--kanna-text-faint);
  font-size: 12px;
  line-height: 1;
  white-space: nowrap;
  vertical-align: middle;
}
/* 前三名的奖杯：同一个 Trophy 图标，按名次上金 / 银 / 铜色 */
.rank-tag .rank-tag-trophy {
  font-size: 15px;
  flex: none;
}
.rank-tag.medal-gold .rank-tag-trophy {
  color: #e09600;
}
.rank-tag.medal-silver .rank-tag-trophy {
  color: #7f8a99;
}
.rank-tag.medal-bronze .rank-tag-trophy {
  color: #c06a1e;
}
.rank-tag.is-my {
  color: var(--kanna-accent-text);
  border-color: var(--kanna-border-pink);
  background: var(--kanna-primary-soft);
}
.rank-tag.medal-gold {
  color: #a16207;
  border-color: #e0b048;
  background: #fffaf0;
}
.rank-tag.medal-silver {
  color: #5b6675;
  border-color: #aab3c0;
  background: #f7f8fa;
}
.rank-tag.medal-bronze {
  color: #9a4f1d;
  border-color: #d99a6c;
  background: #fef6ef;
}

/* 最后一名（服务器实际榜单末位档位）：绿色高亮 */
:deep(.el-table__body tr.last-rank-row > td.el-table__cell) {
  background: #ecfdf5;
}
:deep(.el-table__body tr.last-rank-row:hover > td.el-table__cell) {
  background: #d1fae5;
}
.last-rank-name {
  color: var(--kanna-success-strong);
  font-weight: 600;
}
/* 档线表格「合计分数」：默认与守线公会名同色（都跟随正文色），
   我会行保持原有合计分数配色，末位行沿用绿色 */
.rank-score {
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}
.rank-score.my-clan-name {
  color: var(--kanna-heading);
}
.reward-cell {
  font-size: 12px;
  color: #92610a;
  white-space: nowrap;
}
.gap-ok {
  color: var(--kanna-success);
  font-weight: 600;
}
.gap-lack {
  color: #ea580c;
  font-weight: 600;
}

/* 档线表格：前三名 / 末位的浅底行在深色下改成半透明色底。表体在 el-table
   内部必须 :deep 穿透；dark 覆盖要把作用域类写在前缀里 —— 直接写
   `html.dark :deep(...)` 会被编译成 `html.dark[data-v-xxx] ...`，
   而 html 上没有 data-v 属性，规则永远不生效。 */
html.dark .rankline-table :deep(.el-table__body tr.medal-row-gold > td.el-table__cell) {
  background: rgba(245, 158, 11, 0.12);
}
html.dark .rankline-table :deep(.el-table__body tr.medal-row-gold:hover > td.el-table__cell) {
  background: rgba(245, 158, 11, 0.2);
}
html.dark .rankline-table :deep(.el-table__body tr.medal-row-silver > td.el-table__cell) {
  background: rgba(148, 163, 184, 0.12);
}
html.dark .rankline-table :deep(.el-table__body tr.medal-row-silver:hover > td.el-table__cell) {
  background: rgba(148, 163, 184, 0.2);
}
html.dark .rankline-table :deep(.el-table__body tr.medal-row-bronze > td.el-table__cell) {
  background: rgba(217, 119, 6, 0.12);
}
html.dark .rankline-table :deep(.el-table__body tr.medal-row-bronze:hover > td.el-table__cell) {
  background: rgba(217, 119, 6, 0.2);
}
html.dark .rankline-table :deep(.el-table__body tr.last-rank-row > td.el-table__cell) {
  background: rgba(16, 185, 129, 0.12);
}
html.dark .rankline-table :deep(.el-table__body tr.last-rank-row:hover > td.el-table__cell) {
  background: rgba(16, 185, 129, 0.2);
}
/* 前三名的深棕 / 钢灰文字在深色底上看不清，换亮色 */
html.dark .medal-text-gold {
  color: #fcd34d;
}
html.dark .medal-text-silver {
  color: #cbd5e1;
}
html.dark .medal-text-bronze {
  color: #fdba74;
}
/* 名次标签：前三名金 / 银 / 铜徽章换半透明底 + 亮字 */
html.dark .rank-tag.medal-gold {
  color: #fcd34d;
  border-color: rgba(234, 179, 8, 0.45);
  background: rgba(234, 179, 8, 0.15);
}
html.dark .rank-tag.medal-silver {
  color: #e2e8f0;
  border-color: rgba(148, 163, 184, 0.5);
  background: rgba(148, 163, 184, 0.15);
}
html.dark .rank-tag.medal-bronze {
  color: #fdba74;
  border-color: rgba(217, 119, 6, 0.5);
  background: rgba(217, 119, 6, 0.16);
}
html.dark .rank-tag.medal-gold .rank-tag-trophy {
  color: #fbbf24;
}
html.dark .rank-tag.medal-silver .rank-tag-trophy {
  color: #cbd5e1;
}
html.dark .rank-tag.medal-bronze .rank-tag-trophy {
  color: #fdba74;
}
html.dark .reward-cell {
  color: #fcd34d;
}
html.dark .gap-lack {
  color: #fb923c;
}


@media (max-width: 767px) {
  .reward-cell { font-size: 11px; }
  .rank-score { font-size: 12px; }
}
</style>
