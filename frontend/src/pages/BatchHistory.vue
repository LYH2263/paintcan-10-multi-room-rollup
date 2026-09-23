<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'
const items = ref([])
const open = ref({})
const parse = (s) => { try { return JSON.parse(s) } catch { return null } }
const toggle = (id) => { open.value[id] = !open.value[id] }
onMounted(async () => { items.value = (await getJSON('/api/history')).items })
</script>
<template><div class="page"><h1>估算记录</h1>
<table>
  <tr v-for="h in items" :key="h.id">
    <td>
      <div>#{{ h.id }} · {{ h.kind === 'multi_estimate' ? '多房合并' : '单房' }} · {{ h.created_at }}</div>
      <template v-if="h.kind === 'multi_estimate'">
        <a href="#" @click.prevent="toggle(h.id)">{{ open[h.id] ? '收起' : '查看分房明细' }}</a>
        <table v-if="open[h.id]">
          <tr><th>房间</th><th>尺寸 L×W×H</th><th>净面积 m²</th><th>涂布率</th><th>遍数</th><th>升数 L</th></tr>
          <tr v-for="d in parse(h.result_json).rooms" :key="d.room_id">
            <td>#{{ d.room_id }} {{ d.name }}</td>
            <td>{{ d.length }}×{{ d.width }}×{{ d.height }}</td>
            <td>{{ d.net_m2 }}</td>
            <td>{{ d.coverage }}</td>
            <td>{{ d.coats }}</td>
            <td>{{ d.liters }}</td>
          </tr>
          <tr><td colspan="5" style="text-align:right"><strong>合计</strong></td>
            <td><strong>{{ parse(h.result_json).total_liters }} L</strong></td></tr>
        </table>
      </template>
      <template v-else>
        房间 #{{ h.room_id }} · {{ parse(h.result_json).liters }} L
      </template>
    </td>
  </tr>
</table></div></template>
