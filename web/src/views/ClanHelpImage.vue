<template>
  <main v-if="data" data-status-board class="help-board">
    <header><span>环奈连结 R · 会战工具</span><h1>自动报刀帮助</h1><p>查询战报、协作出刀与管理会战</p></header>
    <div class="columns">
      <div v-for="(column, index) in columns" :key="index" class="column">
        <section v-for="section in column" :key="section.title">
          <h2>{{ section.title }}</h2>
          <div v-for="item in section.commands" :key="item.command" class="command">
            <b>{{ item.command }}</b><p v-if="item.description">{{ item.description }}</p>
          </div>
        </section>
      </div>
    </div>
    <footer><p v-for="note in data.notes" :key="note">{{ note }}</p></footer>
  </main>
  <div v-else>此页面由机器人生成帮助图片。</div>
</template>

<script setup lang="ts">
interface HelpSection { title: string; commands: { command: string; description: string }[] }
interface HelpData { sections: HelpSection[]; notes: string[] }
const data = (window as Window & { __KANNA_STATUS__?: HelpData }).__KANNA_STATUS__
const sections = data?.sections || []
const columns = [[sections[0], sections[2]].filter(Boolean), [sections[1], sections[3]].filter(Boolean)]
</script>

<style scoped>
.help-board { width: 840px; box-sizing: border-box; padding: 26px; background: #f8efcc; color: #342d25; font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif; }
header { margin-bottom: 20px; }
header span { font-size: 13px; letter-spacing: 2px; color: #92754c; }
h1 { margin: 8px 0; font-size: 30px; }
header p { margin: 0; color: #82745e; font-size: 14px; }
.columns { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start; }
.column { display: grid; gap: 16px; min-width: 0; }
section { padding: 16px; border-radius: 14px; background: #fffdf7; }
h2 { margin: 0 0 10px; font-size: 18px; color: #a94360; padding-bottom: 9px; border-bottom: 2px solid #f3d6db; }
.command { padding: 8px 0; border-bottom: 1px solid #eee7d9; overflow-wrap: anywhere; }
.command:last-child { border: none; padding-bottom: 0; }
.command b { font-size: 15px; line-height: 1.5; }
.command p { margin: 3px 0 0; font-size: 13px; line-height: 1.6; color: #786d5e; }
footer { margin-top: 16px; padding: 12px 15px; background: #f0e3bc; border-radius: 10px; font-size: 13px; line-height: 1.7; color: #796745; }
footer p { margin: 3px 0; }
</style>
