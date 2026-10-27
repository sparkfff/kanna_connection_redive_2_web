<template>
  <article class="status-boss" :class="lapLevel">
    <header class="boss-heading">
      <img v-if="boss.id && !failed" :src="bossAvatarUrl(boss.id)" @error="failed = true" alt="" />
      <div v-else class="boss-placeholder">{{ order }}</div>
      <div class="heading-content">
        <div class="title-line">
          <h2>{{ order }} · {{ boss.name || '未知 BOSS' }}</h2>
          <span class="lap" :class="lapLevel">{{ lapLevel === 'high' ? '高周目 · ' : lapLevel === 'low' ? '低周目 · ' : '' }}{{ boss.lap || '—' }} 周目</span>
        </div>
        <div class="hp-track">
          <div class="hp-fill" :style="{ width: `${percent}%` }"></div>
          <span>{{ boss.max_hp ? `${boss.current_hp.toLocaleString()} / ${boss.max_hp.toLocaleString()}` : '暂无血量数据' }}</span>
        </div>
      </div>
    </header>
    <div v-for="section in sections" :key="section.key" class="member-row" :class="section.key">
      <span class="row-label">{{ section.label }}</span>
      <div class="member-list">
        <span v-if="!boss[section.key].length" class="empty">{{ section.empty }}</span>
        <span v-for="(member, index) in boss[section.key]" :key="index" class="member-chip">
          <b>{{ member.name }}</b>
          <span v-if="member.lap">{{ member.lap }} 周目</span>
          <span v-if="member.text">{{ member.text }}</span>
        </span>
      </div>
    </div>
    <footer>近期入场 {{ boss.fighter || 0 }} 人</footer>
  </article>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { StatusBoss } from '@/types/statusImage'
import { bossAvatarUrl } from '@/utils/boss'
import type { LapLevel } from '@/utils/boss'

const props = defineProps<{ boss: StatusBoss; order: number; lapLevel?: LapLevel }>()
const failed = ref(false)
const percent = computed(() => props.boss.max_hp ? Math.max(0, Math.min(100, props.boss.current_hp / props.boss.max_hp * 100)) : 0)
const sections = computed(() => ([
  { key: 'subscribe', label: '预约', empty: '暂无预约' },
  { key: 'apply', label: '申请', empty: '暂无申请' },
  { key: 'tree', label: '挂树', empty: '暂无挂树' }
] as const).filter(section => section.key !== 'tree' || props.boss.tree.length > 0))
</script>

<style scoped>
.status-boss { background: #fffdf2; border: 1px solid #fff; border-radius: 14px; padding: 15px; box-shadow: 0 5px 0 #dacf9e50; }
.status-boss.low { border-top: 4px solid #159a92; padding-top: 12px; }
.status-boss.high { border-top: 4px solid #8554c8; padding-top: 12px; }
.boss-heading { display: flex; align-items: center; gap: 12px; margin-bottom: 13px; }
.boss-heading img, .boss-placeholder { width: 66px; height: 66px; flex-shrink: 0; border-radius: 12px; object-fit: cover; }
.boss-placeholder { display: grid; place-items: center; background: #ecdcb6; color: #866a40; font-size: 32px; font-weight: 800; }
.heading-content { flex: 1; min-width: 0; }
.title-line { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-bottom: 10px; }
h2 { font-size: 21px; line-height: 1.25; font-weight: 700; margin: 0; overflow-wrap: anywhere; }
.lap { white-space: nowrap; background: #e86376; border-radius: 12px; padding: 1px 10px; color: white; font-size: 17px; }
.lap.low { background: #159a92; font-size: 15px; }
.lap.high { background: #8554c8; font-size: 15px; }
.hp-track { height: 25px; background: #e9e5d5; border-radius: 20px; overflow: hidden; position: relative; text-align: center; color: #302619; font-size: 15px; font-weight: 700; }
.hp-fill { height: 100%; background: #f36a6a; }
.hp-track span { position: absolute; inset: 0; line-height: 25px; text-shadow: 0 0 3px #fff; }
.member-row { display: flex; min-height: 62px; border-radius: 8px; margin-top: 8px; overflow: hidden; }
.subscribe { background: #bceafa; }
.apply { background: #fff6bb; }
.tree { background: #ffd2d7; }
.row-label { display: flex; align-items: center; justify-content: center; width: 46px; padding: 10px; flex-shrink: 0; font-size: 19px; font-weight: 700; border-right: 1px solid #ffffff90; }
.member-list { flex: 1; display: flex; flex-wrap: wrap; align-items: center; gap: 6px; padding: 10px; min-width: 0; }
.empty { text-align: center; width: 100%; color: #706957; font-size: 18px; }
.member-chip { display: flex; flex-wrap: wrap; gap: 4px 7px; align-items: baseline; max-width: 100%; padding: 4px 9px; border-radius: 10px; background: #ffffffa6; font-size: 15px; overflow-wrap: anywhere; }
.member-chip b { font-weight: 600; }
.member-chip span { color: #706957; font-size: 13px; }
footer { color: #93866a; font-size: 11px; margin-top: 10px; }
</style>
