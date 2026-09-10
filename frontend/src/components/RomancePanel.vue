<script setup lang="ts">
import { computed, ref, reactive, watch, onBeforeUnmount } from 'vue';
import { Sparkles, ArrowRight, WandSparkles } from '@lucide/vue';
import StreamNote from '@/components/StreamNote.vue';
import { readStream } from '@/lib/api';
import { Button } from '@/components/ui/button';
import type { Profile } from '@/lib/demo';
const props = defineProps<{ profile?: Profile }>();
const emit = defineEmits<{ 'edit-profile': [] }>();
const linkedProfile = computed(() => {
  const p = props.profile;
  return p && p.name.trim() && p.interests.length && p.city.trim() && Number.isInteger(p.age) && p.age >= 18 && p.age <= 80 ? p : null;
});
const form = reactive({ birth_date: '', birth_time: '', birth_place: '', relationship_status: '单身', year: new Date().getFullYear(), context: '' });
const unknownTime = ref(false);
const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
const busy = ref(false), error = ref(''), content = ref(''), status = ref(''), stopped = ref(false);
const exampleUsed = ref(false);
let controller: AbortController | undefined;
let revision = 0;
function reset() { revision++; controller?.abort(); busy.value = false; content.value = ''; status.value = ''; stopped.value = false; error.value = ''; }
watch([form, unknownTime], () => { reset(); exampleUsed.value = false; }, { deep: true, flush: 'sync' });
watch(() => props.profile, reset, { deep: true });
onBeforeUnmount(reset);
function preset() {
  unknownTime.value = false;
  Object.assign(form, { birth_date: '2000-06-15', birth_time: '14:30', birth_place: '浙江杭州', relationship_status: '单身', year: 2026, context: '想了解本命与2026年的桃花对应，以及怎样自然地认识新朋友。' });
  exampleUsed.value = true;
}
function stop() { revision++; controller?.abort(); busy.value = false; stopped.value = true; status.value = '已停止'; }
async function calculate() {
  if (busy.value) return;
  if (!form.birth_date || form.birth_date > today || form.birth_date < '1900-01-01' || !form.birth_place.trim() || (!unknownTime.value && !form.birth_time) || !Number.isInteger(form.year) || form.year < 1900 || form.year > 2100) { error.value = '请补全有效的出生资料和关注年份。'; return; }
  reset();
  const id = revision;
  controller = new AbortController(); busy.value = true;
  try {
    await readStream('/api/romance/calculate', { ...form, birth_time: unknownTime.value ? null : form.birth_time, calendar: '公历', time_basis: '北京时间 UTC+8', profile: linkedProfile.value }, controller.signal, (event) => {
      if (id !== revision) return;
      if (event.type === 'delta') content.value += event.text;
      if (event.type === 'stage') status.value = event.label;
      if (event.type === 'done') status.value = '解读完成';
    });
  } catch (e) { if (id === revision) { error.value = e instanceof Error ? e.message : '请稍后重试'; status.value = '生成未完成'; } }
  finally { if (id === revision) busy.value = false; }
}
</script>
<template>
  <section class="romance-panel">
    <form class="romance-form" @submit.prevent="calculate">
      <div class="romance-form-heading"><h2>你的出生资料</h2><Button type="button" variant="ghost" size="sm" @click="preset"><WandSparkles :size="14" />填入示例</Button></div>
      <div class="romance-profile-link">
        <div><strong>{{ linkedProfile ? `已结合 ${linkedProfile.name} 的资料` : '尚未关联个人资料' }}</strong><button type="button" @click="emit('edit-profile')">{{ linkedProfile ? '修改' : '去完善' }}</button></div>
        <p v-if="linkedProfile">{{ linkedProfile.goal }} · {{ linkedProfile.rhythm }}<br />{{ linkedProfile.interests.join('、') }} · {{ linkedProfile.companionship }}</p>
        <p v-else>完善兴趣与关系期待，建议会更贴合你。也可直接解读。</p>
      </div>
      <p v-if="exampleUsed" class="example-note">已填入虚构出生示例，关联的个人偏好保持不变。</p>
      <label>出生日期 <small>公历</small><input v-model="form.birth_date" type="date" min="1900-01-01" :max="today" required /></label>
      <label>出生时间 <small>北京时间</small><input v-model="form.birth_time" type="time" :disabled="unknownTime" :required="!unknownTime" /></label>
      <label class="unknown-time"><input v-model="unknownTime" type="checkbox" />不清楚具体时间</label>
      <label>出生地<input v-model="form.birth_place" maxlength="80" placeholder="例如：浙江杭州" required /></label>
      <div class="romance-row"><label>感情状态<select v-model="form.relationship_status"><option>单身</option><option>正在了解</option><option>已有伴侣</option></select></label><label>关注年份<input v-model.number="form.year" type="number" min="1900" max="2100" required /></label></div>
      <label>想了解什么 <small>选填</small><textarea v-model="form.context" maxlength="1000" rows="3" placeholder="比如：本命桃花与今年有什么对应？" /></label>
      <Button type="submit" :disabled="busy" class="romance-submit"><Sparkles :size="15" />{{ busy ? '正在解读…' : '开始解读' }}<ArrowRight :size="15" /></Button>
      <details class="romance-about"><summary>口径与说明 · 民俗娱乐</summary><p>公历、北京时间，日柱以午夜换日；不校正真太阳时。AI 推算仅供民俗娱乐，可能有误，不影响匹配分。资料会发送至你配置的模型服务，本应用不保存查询。</p><a href="https://www.chinese-classics.org/read/shushu/mingli/san-ming-tong-hui/003" target="_blank" rel="noopener noreferrer">咸池规则出处 ↗</a></details>
    </form>
    <section class="romance-result">
      <div class="romance-result-heading"><h2>今日桃花</h2><span role="status">{{ status }}</span></div>
      <StreamNote v-if="content || busy || error || stopped" :key="revision" :content="content" :running="busy" :stopped="stopped" :error="error" compact @stop="stop" @retry="calculate" />
      <div v-else class="romance-empty"><Sparkles :size="32" :stroke-width="1" /><h3>从你的出生时刻，聊聊缘分</h3><p>今日结论 · 相处建议 · 推算依据</p><Button variant="outline" @click="preset">用示例试试</Button><p v-if="error" role="alert">{{ error }}</p></div>
    </section>
  </section>
</template>
<style scoped>
.romance-panel { display:grid; grid-template-columns:330px minmax(0,1fr); gap:36px; flex:1; min-height:0; width:100%; max-width:1250px; margin:0 auto; }
.romance-form { overflow:auto; min-height:0; padding-right:20px; scrollbar-width:thin; }
.romance-form-heading,.romance-result-heading { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:20px; }
h2 { font-size:17px; font-weight:600; margin:0; }.romance-form label:not(.unknown-time) { display:block; font-size:13px; margin-bottom:18px; } small { font-size:11px; color:#929785; margin-left:6px; }
input:not([type=checkbox]),select,textarea { display:block; width:100%; min-width:0; margin-top:8px; padding:11px 12px; background:#fffefa; border:1px solid var(--border); border-radius:8px; font:inherit; } input:disabled { opacity:.45; } textarea { resize:vertical; max-height:150px; }
.unknown-time { display:flex; align-items:center; gap:8px; font-size:12px; margin:-8px 0 18px; color:#818a76; }.romance-row { display:grid; grid-template-columns:1fr 1fr; gap:14px; }.romance-submit { width:100%; }
.romance-about { font-size:11px; color:#89907f; line-height:1.8; margin:16px 0; } summary { cursor:pointer; } a { color:var(--primary); }.example-note { color:var(--primary); font-size:12px; margin:0 0 16px; }
.romance-result { display:flex; flex-direction:column; overflow:hidden; min-height:0; min-width:0; border-left:1px solid var(--border); padding-left:32px; }.romance-result-heading { flex-shrink:0; min-height:32px; }.romance-result-heading span { font-size:12px; color:#89907f; }
.romance-result :deep(.stream-note) { display:flex; flex-direction:column; flex:1; min-height:0; min-width:0; overflow:hidden; padding:0; margin:0; border:0; background:transparent; }.romance-result :deep(.stream-viewport) { flex:1; min-height:0; max-height:none; overflow:auto; overflow-wrap:anywhere; }.romance-result :deep(.stream-actions) { flex-shrink:0; }.romance-empty { margin:auto; text-align:center; color:#869078; padding:20px; }.romance-empty h3 { font-family:serif; font-size:23px; margin:18px 0 12px; }.romance-empty p { font-size:12px; margin-bottom:24px; }
@media(max-width:900px) { .romance-panel { grid-template-columns:270px minmax(0,1fr); gap:16px; }.romance-result { padding-left:16px; } }
@media(max-width:640px) { .romance-panel { grid-template-columns:1fr; grid-template-rows:minmax(0,42%) minmax(0,1fr); }.romance-form { padding-right:4px; }.romance-result { border-left:0; border-top:1px solid var(--border); padding:12px 0 0; }.romance-result-heading { margin-bottom:8px; } }
/* Make the model's conclusion visibly distinct while it streams. */
.romance-result :deep(.stream-viewport h1) { font-family:serif; font-size:clamp(26px, 3vw, 38px); font-weight:600; line-height:1.4; color:var(--primary); margin:8px 0 18px; }
.romance-result :deep(.stream-viewport blockquote) { border-left:3px solid var(--primary); background:#f4ece5; border-radius:0 10px 10px 0; padding:16px 20px; margin:0 0 20px; color:var(--foreground); }
.romance-result :deep(.stream-viewport blockquote p) { font-size:17px; line-height:1.8; margin:0; color:inherit; }
.romance-result :deep(.stream-viewport h2) { font-size:18px; margin:24px 0 12px; }
.romance-profile-link { border-bottom:1px solid var(--border); padding-bottom:14px; margin-bottom:18px; font-size:12px; }
.romance-profile-link > div { display:flex; align-items:center; justify-content:space-between; gap:12px; }
.romance-profile-link strong { font-weight:500; color:var(--primary); }
.romance-profile-link button { color:#818a76; text-decoration:underline; }
.romance-profile-link p { color:#89907f; line-height:1.8; margin:6px 0 0; }
</style>
