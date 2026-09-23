<script setup>
import { computed, onMounted, ref } from 'vue'
import { getJSON, postJSON } from '../api'

const rooms = ref([])
const selected = ref([])
const coats = ref(null)
const coverage = ref(null)
// 分房覆盖：{ [room_id]: { coats, coverage } }，留空回落统一值
const perRoom = ref({})
const out = ref(null)
const err = ref('')
const loading = ref(false)

onMounted(async () => { rooms.value = (await getJSON('/api/rooms')).items })

const orderedSelected = computed(() =>
  rooms.value.filter(r => selected.value.includes(r.id)).map(r => r.id))

function toggle(id) {
  const i = selected.value.indexOf(id)
  if (i >= 0) {
    selected.value.splice(i, 1)
  } else {
    selected.value.push(id)
    perRoom.value[id] = perRoom.value[id] ?? { coats: null, coverage: null }
  }
}

const run = async () => {
  err.value = ''; out.value = null
  if (!orderedSelected.value.length) { err.value = '请至少选择一个房间'; return }
  const room_params = orderedSelected.value
    .map(rid => ({
      room_id: rid,
      coats: perRoom.value[rid]?.coats ?? null,
      coverage: perRoom.value[rid]?.coverage ?? null,
    }))
    .filter(p => p.coats !== null || p.coverage !== null)
  try {
    loading.value = true
    out.value = await postJSON('/api/estimate/multi', {
      room_ids: orderedSelected.value,
      coats: coats.value,
      coverage: coverage.value,
      room_params,
      persist: true,
    })
  } catch (e) {
    let msg = String(e.message || e)
    try { msg = JSON.parse(msg).detail || msg } catch { /* 原样展示 */ }
    err.value = msg
  } finally {
    loading.value = false
  }
}
</script>
<template><div class="page"><h1>估漆工作台（多房合并）</h1>
  <h2>选择房间</h2>
  <table>
    <tr v-for="r in rooms" :key="r.id">
      <td><input type="checkbox" :checked="selected.includes(r.id)" @change="toggle(r.id)" /></td>
      <td>#{{ r.id }} {{ r.name }}</td>
      <td>{{ r.length }}×{{ r.width }}×{{ r.height }} m</td>
      <td v-if="selected.includes(r.id)">
        遍数 <input style="width:5em" type="number" min="1" v-model.number="perRoom[r.id].coats" placeholder="统一" />
        涂布率 <input style="width:6em" type="number" min="0.1" step="0.1" v-model.number="perRoom[r.id].coverage" placeholder="统一" />
      </td>
    </tr>
  </table>
  <h2>统一参数（留空用全局设置）</h2>
  <label>遍数 <input style="width:5em" type="number" min="1" v-model.number="coats" placeholder="默认" /></label>
  <label style="margin-left:1rem">涂布率 m²/L <input style="width:6em" type="number" min="0.1" step="0.1" v-model.number="coverage" placeholder="默认" /></label>
  <div style="margin-top:0.75rem"><button :disabled="loading" @click="run">{{ loading ? '估算中…' : '合并估算' }}</button></div>
  <p v-if="err" style="color:#b03434">{{ err }}</p>
  <div v-if="out">
    <h2>分房明细</h2>
    <table>
      <tr><th>房间</th><th>尺寸 L×W×H</th><th>净面积 m²</th><th>涂布率</th><th>遍数</th><th>升数 L</th></tr>
      <tr v-for="d in out.rooms" :key="d.room_id">
        <td>#{{ d.room_id }} {{ d.name }}</td>
        <td>{{ d.length }}×{{ d.width }}×{{ d.height }}</td>
        <td>{{ d.net_m2 }}</td>
        <td>{{ d.coverage }}</td>
        <td>{{ d.coats }}</td>
        <td>{{ d.liters }}</td>
      </tr>
    </table>
    <p class="hero-num">合计 {{ out.total_liters }} 升 <span v-if="out.run_id" style="font-size:1rem">（记录 #{{ out.run_id }}）</span></p>
  </div>
</div></template>
