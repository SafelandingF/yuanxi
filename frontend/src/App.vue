<script setup lang="ts">
import {
  computed,
  defineAsyncComponent,
  onBeforeUnmount,
  onMounted,
  nextTick,
  reactive,
  ref,
  watch,
} from "vue";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronDown,
  Coffee,
  Compass,
  Eye,
  EyeOff,
  Heart,
  KeyRound,
  Leaf,
  Moon,
  RotateCcw,
  Settings2,
  ShieldCheck,
  Sparkles,
  Square,
  Users,
  Utensils,
  WandSparkles,
  X,
} from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import AgentWorkspace from "@/components/AgentWorkspace.vue";
import { sessionRequest, type AgentPart, type AgentSession } from "@/lib/agent";
import Portrait from "@/components/Portrait.vue";
import {
  exampleProfile,
  interestOptions,
  type Candidate,
  type Profile,
  type PlanItem,
} from "@/lib/demo";
import { readStream, type DateResult, type RankedCandidate } from "@/lib/api";
import {
  fetchModelConfig,
  saveModelConfig,
  type ModelConfigStatus,
} from "@/lib/config";
const StreamNote = defineAsyncComponent(
  () => import("@/components/StreamNote.vue"),
);
type Step = "profile" | "matches" | "date";
const mainContent = ref<HTMLElement>();
const step = ref<Step>("profile"),
  toast = ref("");
const configOpen = ref(true),
  configRequired = ref(true),
  configLoading = ref(true),
  configSaving = ref(false),
  configError = ref(""),
  showApiKey = ref(false);
const modelConfig = reactive({
  api_key: "",
  provider: "volcengine-ark",
  base_url: "https://ark.cn-beijing.volces.com/api/v3",
  model: "doubao-seed-2-0-pro-260215",
  has_api_key: false,
});
let toastTimer: ReturnType<typeof setTimeout> | undefined;
function notify(message: string) {
  toast.value = message;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (toast.value = ""), 4500);
}
const mealPreference = ref("都可以"),
  spendingStyle = ref("均衡安排"),
  foodRestrictions = ref<string[]>([]);
const defaultProfile: Profile = {
  name: "",
  age: 23,
  city: "杭州",
  goal: "认真长久",
  rhythm: "规律慢生活",
  interests: [],
  companionship: "每周 2–3 次",
  note: "",
};
function restore(): Profile {
  try {
    const raw = JSON.parse(localStorage.getItem("yuanxi-profile") || "null");
    if (
      raw &&
      typeof raw.name === "string" &&
      typeof raw.age === "number" &&
      typeof raw.city === "string" &&
      typeof raw.note === "string" &&
      Array.isArray(raw.interests) &&
      raw.interests.every((i: unknown) => typeof i === "string") &&
      typeof raw.goal === "string" &&
      typeof raw.rhythm === "string" &&
      typeof raw.companionship === "string"
    )
      return raw;
  } catch {}
  return structuredClone(defaultProfile);
}
const profile = reactive<Profile>(restore()),
  analyzedProfile = ref<Profile>();
const agentSession = ref<AgentSession>();
const more = ref(false),
  error = ref(""),
  busy = ref(false),
  stage = ref(0),
  stageLabel = ref(""),
  trace = ref<string[]>([]),
  dateTools = ref<AgentPart[]>([]);
const emptyCandidate: Candidate = {
  id: 0,
  name: "",
  age: 0,
  city: "",
  occupation: "",
  interests: [],
  color: "sage",
  quote: "",
  rhythm: "",
  companionship: "",
  budget: 120,
  food: "",
  detail: "",
};
const selected = ref<Candidate>(emptyCandidate),
  budget = ref(120),
  startTime = ref("18:00"),
  planReady = ref(false),
  planError = ref(""),
  generatedPlan = ref<PlanItem[]>([]),
  latestResult = ref<DateResult>(),
  planRevision = ref(0),
  feedback = ref(false),
  feedbackExplanation = ref(""),
  finalScore = ref<number>(),
  dateNote = ref("");
const dateTab = ref<"plan" | "note" | "activity">("plan");
const dateDirty = ref(false);
const streaming = ref(false),
  streamTarget = ref<"match" | "date">("match"),
  streamError = ref(""),
  streamStopped = ref(false);
let controller: AbortController | undefined;
let runId = 0;
const steps = [
  { id: "profile" as const, number: "01", label: "了解自己", icon: Heart },
  { id: "matches" as const, number: "02", label: "匹配助手", icon: Users },
  { id: "date" as const, number: "03", label: "安排约会", icon: Compass },
];
const stepIndex = computed(() => steps.findIndex((s) => s.id === step.value));
const ranked = computed<RankedCandidate[]>(
  () => agentSession.value?.candidates || [],
);
const planTotal = computed(() =>
  generatedPlan.value.reduce((sum, item) => sum + item.cost, 0),
);
const planDuration = computed(() => {
  if (!generatedPlan.value.length) return "";
  if (generatedPlan.value.some((item) => !item.duration_minutes))
    return "2 小时 45 分钟";
  const minutes =
    generatedPlan.value.reduce(
      (sum, item) => sum + (item.duration_minutes || 0),
      0,
    ) +
    Math.max(0, generatedPlan.value.length - 1) * 15;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return `${hours ? `${hours} 小时` : ""}${rest ? ` ${rest} 分钟` : ""}`.trim();
});
const selectedScore = computed(
  () =>
    finalScore.value ??
    ranked.value.find((c) => c.id === selected.value.id)?.score ??
    0,
);
watch(
  profile,
  () => {
    try {
      localStorage.setItem("yuanxi-profile", JSON.stringify(profile));
    } catch {}
  },
  { deep: true },
);
watch([budget, startTime, mealPreference, spendingStyle, foodRestrictions], () => {
  if (streamTarget.value === "date") stopStream();
  dateDirty.value = true;
});
function toggleInterest(value: string) {
  if (busy.value) return;
  const index = profile.interests.indexOf(value);
  if (index === -1) profile.interests.push(value);
  else profile.interests.splice(index, 1);
}
function example() {
  Object.assign(profile, structuredClone(exampleProfile));
  error.value = "";
  notify("示例已填入，可以改成你的偏好");
}
function stopStream() {
  runId++;
  controller?.abort();
  controller = undefined;
  if (streaming.value) streamStopped.value = true;
  busy.value = false;
  streaming.value = false;
}
function cancel() {
  stopStream();
  notify("已停止，当前输入与结果已保留");
}
function begin(target: "match" | "date") {
  stopStream();
  controller = new AbortController();
  streamTarget.value = target;
  streaming.value = true;
  streamStopped.value = false;
  streamError.value = "";
  busy.value = true;
  stageLabel.value = "正在连接豆包…";
  stage.value = 0;
  trace.value = [];
  dateTools.value = [];
  return { id: runId, signal: controller.signal };
}
async function analyze() {
  if (busy.value) return;
  if (!profile.name.trim()) {
    error.value = "先告诉我们怎么称呼你。";
    return;
  }
  if (!Number.isFinite(profile.age) || profile.age < 18 || profile.age > 80) {
    error.value = "请填写 18–80 岁之间的年龄。";
    return;
  }
  if (!profile.interests.length) {
    error.value = "至少选择一个你喜欢的日常。";
    return;
  }
  error.value = "";
  busy.value = true;
  try {
    const session = await sessionRequest(
      "/api/agent/sessions",
      JSON.parse(JSON.stringify(profile)),
    );
    updateSession(session);
    selected.value = emptyCandidate;
    planReady.value = false;
    feedback.value = false;
    finalScore.value = undefined;
    step.value = "matches";
    void nextTick(() =>
      mainContent.value?.scrollTo({ top: 0, behavior: "auto" }),
    );
  } catch (e) {
    error.value = e instanceof Error ? e.message : "保存失败，请重试";
  } finally {
    busy.value = false;
  }
}
function updateSession(session: AgentSession) {
  agentSession.value = session;
  analyzedProfile.value = session.profile;
  selected.value =
    session.candidates.find((c) => c.id === session.selected_id) ||
    emptyCandidate;
  try {
    localStorage.setItem("yuanxi-agent-session", session.session_id);
  } catch {}
}

function applyConfigStatus(status: ModelConfigStatus) {
  modelConfig.provider = status.provider;
  modelConfig.base_url = status.base_url;
  modelConfig.model = status.model;
  modelConfig.has_api_key = status.has_api_key;
  modelConfig.api_key = "";
}

async function restorePreviousSession() {
  try {
    const id = localStorage.getItem("yuanxi-agent-session");
    if (!id) return;
    const session = await sessionRequest(
      `/api/agent/sessions/${encodeURIComponent(id)}`,
    );
    updateSession(session);
    step.value = "matches";
  } catch {
    notify("上次对话未能恢复，请确认本地服务已启动，或重新保存资料");
  }
}

async function loadModelConfiguration() {
  configLoading.value = true;
  configError.value = "";
  try {
    const status = await fetchModelConfig();
    applyConfigStatus(status);
    configRequired.value = !status.configured;
    configOpen.value = !status.configured;
    if (status.configured) await restorePreviousSession();
  } catch (e) {
    configRequired.value = true;
    configOpen.value = true;
    configError.value =
      e instanceof Error ? e.message : "无法读取本地模型配置";
  } finally {
    configLoading.value = false;
  }
}

function openModelConfiguration() {
  configError.value = "";
  configOpen.value = true;
}

function closeModelConfiguration() {
  if (!configRequired.value && !configSaving.value) configOpen.value = false;
}

async function submitModelConfiguration() {
  if (configSaving.value) return;
  if (!modelConfig.has_api_key && !modelConfig.api_key.trim()) {
    configError.value = "请填写 API Key";
    return;
  }
  if (!modelConfig.base_url.trim() || !modelConfig.model.trim()) {
    configError.value = "请填写 API 地址和模型名称";
    return;
  }
  configSaving.value = true;
  configError.value = "";
  try {
    const status = await saveModelConfig({
      api_key: modelConfig.api_key,
      provider: modelConfig.provider,
      base_url: modelConfig.base_url,
      model: modelConfig.model,
    });
    applyConfigStatus(status);
    configRequired.value = false;
    configOpen.value = false;
    notify("模型配置已保存到本机");
    if (!agentSession.value) await restorePreviousSession();
  } catch (e) {
    configError.value = e instanceof Error ? e.message : "模型配置保存失败";
  } finally {
    configSaving.value = false;
  }
}

onMounted(async () => {
  await loadModelConfiguration();
});

function navigate(value: Step) {
  if (busy.value && streamTarget.value !== "date") return;
  if (value !== "profile" && !agentSession.value) {
    notify("请先完善并保存个人资料");
    return;
  }
  if (value === "date" && !agentSession.value?.selected_id) {
    notify("请先在对话中选择一位候选");
    return;
  }
  if (value === "date") {
    void choose(selected.value);
    return;
  }
  stopStream();
  step.value = value;
  void nextTick(() =>
    mainContent.value?.scrollTo({ top: 0, behavior: "auto" }),
  );
}
async function choose(candidate: Candidate) {
  stopStream();
  streamTarget.value = "date";
  streamError.value = "";
  streamStopped.value = false;
  dateTab.value = "plan";
  dateNote.value = "";
  generatedPlan.value = [];
  latestResult.value = undefined;
  dateTools.value = [];
  trace.value = [];
  selected.value = candidate;
  budget.value = Math.min(120, candidate.budget);
  planReady.value = false;
  feedback.value = false;
  finalScore.value = undefined;
  planError.value = "";
  step.value = "date";
  void nextTick(() =>
    mainContent.value?.scrollTo({ top: 0, behavior: "auto" }),
  );
  const saved = agentSession.value?.latest_date;
  if (saved?.request.candidate_id === candidate.id) {
    budget.value = saved.request.budget;
    startTime.value = saved.request.start;
    mealPreference.value = saved.request.meal_preference;
    spendingStyle.value = saved.request.spending_style || "均衡安排";
    foodRestrictions.value = saved.request.food_restrictions;
    await nextTick();
    generatedPlan.value = saved.result.plan;
    feedback.value = saved.result.feedback;
    feedbackExplanation.value = saved.result.feedback_explanation;
    finalScore.value = saved.result.final_score;
    dateNote.value = saved.summary;
    latestResult.value = saved.result;
    planReady.value = true;
    planRevision.value++;
  }
  await nextTick();
  dateDirty.value = false;
}
async function generatePlan() {
  if (!agentSession.value || streaming.value) return;
  if (
    !Number.isFinite(budget.value) ||
    budget.value < 30 ||
    budget.value > 500
  ) {
    planError.value = "预算请填写 30–500 元 / 人。";
    return;
  }
  if (
    !/^\d{2}:\d{2}$/.test(startTime.value) ||
    startTime.value < "10:00" ||
    startTime.value > "20:00"
  ) {
    planError.value = "请选择 10:00–20:00 之间的开始时间。";
    return;
  }
  planError.value = "";
  const task = begin("date");
  if (!planReady.value) dateTab.value = "activity";
  let receivedResult = false;
  try {
    await readStream<DateResult>(
      "/api/date/plan",
      {
        session_id: agentSession.value.session_id,
        candidate_id: selected.value.id,
        budget: budget.value,
        start: startTime.value,
        meal_preference: mealPreference.value,
        spending_style: spendingStyle.value,
        food_restrictions: foodRestrictions.value,
        avoid_ids: generatedPlan.value
          .map((item) => item.catalog_id)
          .filter((id): id is string => Boolean(id)),
      },
      task.signal,
      (event) => {
        if (task.id !== runId) return;
        if (event.type === "stage") {
          stage.value = event.index;
          stageLabel.value = event.label;
          trace.value.push(event.label);
        }
        if (event.type === "tool_start") dateTools.value.push(event);
        if (event.type === "tool_end") {
          const tool = dateTools.value.find((p) => p.id === event.id);
          if (tool) Object.assign(tool, event);
        }
        if (event.type === "result") {
          receivedResult = true;
          dateDirty.value = false;
          dateNote.value = "";
          latestResult.value = event;
          generatedPlan.value = event.plan;
          feedback.value = event.feedback;
          feedbackExplanation.value = event.feedback_explanation;
          finalScore.value = event.final_score;
          planReady.value = true;
          planRevision.value++;
          busy.value = false;
        }
        if (event.type === "delta") dateNote.value += event.text;
      },
    );
    if (task.id === runId && receivedResult && latestResult.value && agentSession.value) {
      agentSession.value.latest_date = {
        request: {
          candidate_id: selected.value.id,
          budget: budget.value,
          start: startTime.value,
          meal_preference: mealPreference.value,
          spending_style: spendingStyle.value,
          food_restrictions: [...foodRestrictions.value],
        },
        result: latestResult.value,
        summary: dateNote.value,
      };
    }
  } catch (e) {
    if (task.id === runId && !task.signal.aborted) {
      streamError.value = e instanceof Error ? e.message : "服务连接失败";
      planError.value = streamError.value;
      notify(streamError.value);
    }
  } finally {
    if (task.id === runId) {
      busy.value = false;
      streaming.value = false;
    }
  }
}
function reset() {
  stopStream();
  Object.assign(profile, structuredClone(defaultProfile));
  analyzedProfile.value = undefined;
  agentSession.value = undefined;
  try {
    localStorage.removeItem("yuanxi-agent-session");
  } catch {}
  planReady.value = false;
  feedback.value = false;
  step.value = "profile";
  error.value = "";
  trace.value = [];
  notify("已重新开始");
}
onBeforeUnmount(() => {
  controller?.abort();
  clearTimeout(toastTimer);
});
</script>
<template>
  <div class="app-shell" :class="{ 'chat-mode': step === 'matches' }">
    <aside class="sidebar">
      <a
        class="brand"
        href="#"
        aria-label="缘析，返回个人资料"
        @click.prevent="navigate('profile')"
      >
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 36 36" fill="none">
            <ellipse
              cx="13"
              cy="15"
              rx="7.5"
              ry="10"
              transform="rotate(-28 13 15)"
            />
            <ellipse
              cx="23"
              cy="21"
              rx="7.5"
              ry="10"
              transform="rotate(28 23 21)"
            />
          </svg>
        </span>
        <span class="brand-wordmark"
          ><strong class="brand-name">缘析</strong><small>YUANXI</small></span
        >
      </a>
      <nav aria-label="主要步骤">
        <button
          v-for="(item, index) in steps"
          :key="item.id"
          :class="['nav-item', { active: step === item.id }]"
          :aria-current="step === item.id ? 'step' : undefined"
          :disabled="busy && streamTarget !== 'date'"
          @click="navigate(item.id)"
        >
          <component :is="item.icon" :size="18" :stroke-width="1.6" /><span>{{
            item.label
          }}</span
          ><span class="nav-number">{{
            index < stepIndex ? "✓" : item.number
          }}</span>
        </button>
      </nav>
    </aside>

    <div class="main-shell">
      <header class="topbar">
        <div>
          <strong>{{ steps[stepIndex]?.label }}</strong>
        </div>
        <div>
          <button
            class="text-button model-settings-button"
            :disabled="busy"
            @click="openModelConfiguration"
            aria-label="模型设置"
            title="模型设置"
          >
            <Settings2 :size="14" />
            <span>模型设置</span>
          </button>
          <button
            v-if="step === 'matches'"
            class="text-button"
            @click="navigate('profile')"
          >
            修改资料
          </button>
          <button
            class="text-button"
            :disabled="busy"
            @click="reset"
            aria-label="重新开始"
            title="重新开始"
          >
            <RotateCcw :size="14" />
          </button>
        </div>
      </header>
      <main ref="mainContent" :class="{ 'profile-page': step === 'profile', 'date-page': step === 'date' }">
        <template v-if="step === 'profile'">
          <section class="hero">
            <div class="hero-copy">
              <h1>
                先懂自己，<br />再遇见<span class="accent-word">刚刚好。</span>
              </h1>
              <p>
                从你的日常和期待出发，探索舒服的关系，<br
                  class="desktop-break"
                />也为下一次相遇，多准备一点可能。
              </p>
            </div>
            <div class="connection-art" aria-hidden="true">
              <div class="art-orbit"></div>
              <div class="art-orbit second"></div>
              <div class="art-card first">
                <Leaf :size="27" :stroke-width="1.2" /><span>你的节奏</span
                ><small>be yourself</small>
              </div>
              <div class="art-card second">
                <Heart :size="27" :stroke-width="1.2" /><span>共同的日常</span
                ><small>find your people</small>
              </div>
              <span class="art-star">✳</span><span class="art-dot"></span>
              <div class="art-caption">a connection that feels like you</div>
            </div>
          </section>

          <div class="content-columns">
            <section class="form-panel">
              <div class="panel-title">
                <div>
                  <span class="small-index">01 / ABOUT YOU</span>
                  <h2>聊聊你的日常</h2>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  :disabled="busy"
                  @click="example"
                  ><WandSparkles :size="15" />填入示例</Button
                >
              </div>
              <form @submit.prevent="analyze">
                <fieldset :disabled="busy">
                  <div class="form-grid basics">
                    <label
                      >怎么称呼你<Input
                        v-model="profile.name"
                        maxlength="12"
                        placeholder="一个喜欢的昵称"
                        autocomplete="off"
                    /></label>
                    <label
                      >年龄<Input
                        v-model.number="profile.age"
                        type="number"
                        min="18"
                        max="80"
                    /></label>
                    <label
                      >所在城市<select v-model="profile.city">
                        <option>杭州</option>
                        <option>上海</option>
                        <option>北京</option>
                        <option>沈阳</option>
                        <option>成都</option>
                        <option>广州</option>
                        <option>深圳</option>
                        <option>南京</option>
                        <option>苏州</option>
                        <option>武汉</option>
                        <option>西安</option>
                        <option>重庆</option>
                        <option>长沙</option>
                        <option>厦门</option>
                        <option>青岛</option>
                        <option>天津</option>
                        <option>郑州</option>
                        <option>合肥</option>
                        <option>昆明</option>
                        <option>大连</option>
                      </select></label
                    >
                  </div>
                  <div class="field-group">
                    <div class="field-title">
                      你期待怎样的关系？<span>没有标准答案</span>
                    </div>
                    <div class="choice-row">
                      <button
                        v-for="goal in ['认真长久', '慢慢了解', '先交朋友']"
                        :key="goal"
                        type="button"
                        :class="['choice', { chosen: profile.goal === goal }]"
                        :aria-pressed="profile.goal === goal"
                        @click="profile.goal = goal"
                      >
                        <Heart v-if="goal === '认真长久'" :size="15" /><Coffee
                          v-else-if="goal === '慢慢了解'"
                          :size="15"
                        /><Users v-else :size="15" />{{ goal
                        }}<Check v-if="profile.goal === goal" :size="13" />
                      </button>
                    </div>
                  </div>
                  <div class="field-group">
                    <div class="field-title">
                      哪些小事，会让你开心？<span>可多选</span>
                    </div>
                    <div class="interest-list">
                      <button
                        v-for="interest in interestOptions"
                        :key="interest"
                        type="button"
                        :class="[
                          'interest',
                          { chosen: profile.interests.includes(interest) },
                        ]"
                        :aria-pressed="profile.interests.includes(interest)"
                        @click="toggleInterest(interest)"
                      >
                        <span>{{
                          profile.interests.includes(interest) ? "✓" : "+"
                        }}</span
                        >{{ interest }}
                      </button>
                    </div>
                  </div>
                  <div class="form-grid lifestyle">
                    <label
                      >你的生活节奏<select v-model="profile.rhythm">
                        <option>规律慢生活</option>
                        <option>自由随性</option>
                        <option>忙碌但充实</option>
                      </select></label
                    ><label
                      >理想的见面频率<select v-model="profile.companionship">
                        <option>每周 2–3 次</option>
                        <option>每周 1 次</option>
                        <option>每月 1–2 次</option>
                      </select></label
                    >
                  </div>
                  <button
                    type="button"
                    class="more-toggle"
                    :aria-expanded="more"
                    @click="more = !more"
                  >
                    <span>还有一点想补充的</span
                    ><ChevronDown :size="15" :class="{ rotated: more }" />
                  </button>
                  <div v-if="more" class="extra-field">
                    <Textarea
                      v-model="profile.note"
                      maxlength="300"
                      placeholder="比如：周末喜欢睡到自然醒，希望对方也能享受安静的相处。"
                    /><span
                      >{{ profile.note.length }} / 300 ·
                      用于画像理解与约会分析</span
                    >
                  </div>
                </fieldset>
                <p v-if="error" role="alert" class="error-text">{{ error }}</p>
                <div class="form-footer">
                  <span
                    ><span class="tiny-dot"></span
                    >偏好会保存在这台设备的浏览器中</span
                  ><Button v-if="!busy" type="submit" class="primary-action"
                    >保存资料，进入匹配助手<ArrowRight :size="16" /></Button
                  ><Button v-else type="button" variant="outline" disabled
                    >保存中…<Square :size="14"
                  /></Button>
                </div>
              </form>
            </section>

            <aside class="insight-column">
              <section class="peach-card">
                <div class="card-overline">
                  <span>你的相遇可能性</span
                  ><Sparkles :size="17" :stroke-width="1.5" />
                </div>
                <div class="peach-visual">
                  <div class="peach-ring"><span>?</span></div>
                  <i class="ring-spark">✳</i>
                </div>
                <h3>每一种你，都有可能</h3>
                <p>完成偏好后，看看你与这组<br />示例人物的契合之处。</p>
                <div class="peach-bottom">
                  <span>关系画像</span><span>共同兴趣</span
                  ><span>相处节奏</span>
                </div>
              </section>
              <section class="journey-card">
                <span class="small-index">HOW IT WORKS</span>
                <h3>三位助手，一起想一想</h3>
                <div
                  v-for="(s, i) in [
                    {
                      title: '理解你的偏好',
                      subtitle: '画像助手 · 找到关系里的关键词',
                      icon: Heart,
                    },
                    {
                      title: '发现契合的人',
                      subtitle: '匹配助手 · 比较日常与期待',
                      icon: Users,
                    },
                    {
                      title: '安排一次见面',
                      subtitle: '约会助手 · 兼顾两个人的习惯',
                      icon: Compass,
                    },
                  ]"
                  :key="s.title"
                  class="journey-row"
                >
                  <div><component :is="s.icon" :size="16" /></div>
                  <span
                    ><strong>{{ s.title }}</strong
                    ><small>{{ s.subtitle }}</small></span
                  ><span class="journey-number">0{{ i + 1 }}</span>
                </div>
              </section>
              <p class="small-disclaimer">
                这是一场关于关系偏好的小实验。<br />不定义你的价值，也不预测爱情。
              </p>
            </aside>
          </div>
        </template>

        <template v-else-if="step === 'matches'">
          <AgentWorkspace
            v-if="agentSession"
            :key="agentSession.session_id"
            :session="agentSession"
            @update="updateSession"
            @arrange="choose"
          />
        </template>

        <template v-else>
          <div class="date-layout">
            <section class="date-settings">
              <div class="panel-title">
                <div>
                  <h2>和 {{ selected.name }} 的约会</h2>
                </div>
              </div>
              <div class="date-person">
                <Portrait :variant="selected.color" small />
                <div>
                  <h3>{{ selected.name }}</h3>
                  <span>{{ selected.age }} 岁 · {{ selected.occupation }}</span>
                </div>
                <span class="person-score"
                  >{{ selectedScore }}<small>适配分</small></span
                >
              </div>
              <button class="text-button" @click="navigate('matches')">
                回到对话，重新挑选
              </button>
              <div class="preference-compare">
                <div>
                  <span>你的期待</span
                  ><strong>{{ analyzedProfile?.companionship }}见面</strong
                  ><small>{{ analyzedProfile?.rhythm }}</small>
                </div>
                <div>
                  <span>对方的日常</span
                  ><strong>{{ selected.companionship }}见面</strong
                  ><small>{{ selected.food }}</small>
                </div>
              </div>
              <div class="date-controls">
                <label
                  >今天想吃什么？<select v-model="mealPreference">
                    <option>都可以</option>
                    <option>想吃锅类</option>
                    <option>偏爱简餐</option>
                    <option>偏爱素食</option>
                  </select></label
                >
                <div class="diet-options">
                  <label
                    v-for="restriction in ['不吃辣', '素食']"
                    :key="restriction"
                    ><input
                      type="checkbox"
                      v-model="foodRestrictions"
                      :value="restriction"
                    />{{ restriction }}</label
                  >
                </div>
                <div class="spending-control">
                  <span>这次更看重什么？</span>
                  <div class="spending-options">
                    <button
                      v-for="style in ['性价比优先', '均衡安排', '体验优先']"
                      :key="style"
                      type="button"
                      :class="{ selected: spendingStyle === style }"
                      :aria-pressed="spendingStyle === style"
                      @click="spendingStyle = style"
                    >
                      {{ style }}
                    </button>
                  </div>
                </div>
                <label
                  >整场预算 <span>元 / 人</span
                  ><Input
                    v-model.number="budget"
                    type="number"
                    min="30"
                    max="500"
                /></label>
                <div class="budget-presets">
                  <button
                    v-for="amount in [60, 100, 150]"
                    :key="amount"
                    :class="{ selected: budget === amount }"
                    @click="budget = amount"
                  >
                    ¥ {{ amount }}
                  </button>
                </div>
                <p>
                  对方预算上限 ¥{{ selected.budget }} / 人，按双方较低值规划。
                </p>
                <label
                  >几点开始？<Input
                    v-model="startTime"
                    type="time"
                    min="10:00"
                    max="20:00"
                /></label>
              </div>
              <p v-if="planError" role="alert" class="error-text">
                {{ planError }}
              </p>
              <div class="date-submit">
              <Button
                class="plan-button"
                :disabled="streaming"
                @click="generatePlan"
                ><Sparkles :size="16" />{{
                  streaming ? "正在规划…" : dateDirty && planReady ? "按新条件规划" : planReady ? "重新规划" : "生成约会安排"
                }}<ArrowRight :size="16" /></Button
              >
              <p v-if="dateDirty && planReady" class="date-footnote">条件已修改，右侧保留上次行程。</p>
              </div>
            </section>
            <section class="date-output">
              <div class="date-output-header">
                <div class="date-view-switch" aria-label="约会内容">
                  <button :class="{ active: dateTab === 'plan' }" :aria-pressed="dateTab === 'plan'" @click="dateTab = 'plan'">行程</button>
                  <button :class="{ active: dateTab === 'note' }" :aria-pressed="dateTab === 'note'" @click="dateTab = 'note'">安排说明</button>
                  <button :class="{ active: dateTab === 'activity' }" :aria-pressed="dateTab === 'activity'" @click="dateTab = 'activity'">生成过程<span v-if="streaming" class="date-live-dot"></span></button>
                </div>
                <Button v-if="streaming" variant="ghost" size="sm" @click="cancel"><Square :size="12" />停止</Button>
              </div>
              <div class="date-generation-status" role="status" aria-live="polite">
                <Sparkles v-if="streaming" :size="14" /><Check v-else-if="planReady" :size="14" />
                <span>{{ streaming ? stageLabel : streamError ? '生成未完成，可重试；已有行程保留' : streamStopped ? '已停止，已有内容保留' : dateDirty && planReady ? '条件已修改，等待重新规划' : planReady ? '行程已就绪' : '调整左侧条件，开始规划' }}</span>
              </div>
              <div v-show="dateTab === 'activity'" class="date-activity date-scroll-pane">
                <p v-if="!trace.length && !dateTools.length">开始规划后，这里会显示实际执行的步骤与结果。</p>
                <ol class="date-stage-list"><li v-for="(item, index) in trace" :key="index">{{ item }}</li></ol>
              <details
                v-for="tool in dateTools"
                :key="tool.id"
                class="tool-activity"
                :class="tool.status || (streaming ? 'running' : 'error')"
              >
                <summary>
                  <Check v-if="tool.status === 'success'" :size="13" /><Sparkles
                    v-else
                    :size="13"
                  /><span
                    >{{ tool.label
                    }}<small>{{ tool.summary || (streaming ? "正在执行…" : "已中断") }}</small></span
                  >
                </summary>
                <div class="tool-details">
                  <strong>输入</strong>
                  <pre>{{ JSON.stringify(tool.input, null, 2) }}</pre>
                  <strong v-if="tool.output">返回结果</strong>
                  <pre v-if="tool.output">{{
                    JSON.stringify(tool.output, null, 2)
                  }}</pre>
                </div>
              </details>
              </div>
              <div v-show="dateTab === 'plan'" class="date-scroll-pane">
            <section v-if="!planReady" class="date-empty">
              <div class="empty-art">
                <Coffee :size="48" :stroke-width="1" /><span>+</span
                ><Leaf :size="43" :stroke-width="1" />
              </div>

              <h2>{{ streaming ? "正在为你安排这次见面" : "给见面留一点期待" }}</h2>
              <p>
                选好预算和开始时间，<br />我们会试着找到两个人都舒服的安排。
              </p>
              <div class="empty-chips">
                <span><Utensils :size="13" />照顾口味</span
                ><span><Moon :size="13" />轻松节奏</span
                ><span><Heart :size="13" />共同偏好</span>
              </div>
            </section>
            <div v-else class="plan-results">
              <section class="itinerary">
                <div class="itinerary-heading">
                  <div>
                    <span class="small-index">YOUR LITTLE DATE</span>
                    <h2>把今晚，过得慢一点</h2>
                  </div>
                  <span>{{ planDuration ? `约 ${planDuration}` : "" }}</span>
                </div>
                <div
                  v-for="(item, index) in generatedPlan"
                  :key="item.time"
                  class="timeline-item"
                >
                  <span class="timeline-time">{{ item.time }}</span>
                  <div class="timeline-node">
                    <Utensils v-if="item.kind === 'food'" :size="17" /><Leaf
                      v-else-if="item.kind === 'walk'"
                      :size="17"
                    /><Coffee v-else :size="17" />
                  </div>
                  <div class="timeline-copy">
                    <span
                      >0{{ index + 1 }} /
                      {{
                        item.kind === "food"
                          ? "DINNER"
                          : item.kind === "walk"
                            ? "A LITTLE WALK"
                            : "ONE MORE CUP"
                      }}</span
                    >
                    <h3>{{ item.title }}</h3>
                    <p>{{ item.detail }}</p>
                  </div>
                  <span class="timeline-price">{{
                    item.cost ? "¥ " + item.cost : "免费"
                  }}</span>
                </div>
                <div class="itinerary-total">
                  <span
                    >整场参考费用<small
                      >{{ latestResult?.spending_style || spendingStyle }} ·
                      目标约 ¥{{ latestResult?.target_spend || "—" }}，不含交通费</small
                    ></span
                  ><strong>¥ {{ planTotal }}<small>/ 人</small></strong>
                </div>
              </section>
              <section v-if="feedback" class="feedback-card">
                <span class="feedback-icon"><RotateCcw :size="19" /></span>
                <div>
                  <h3>关于见面频率，有一件事值得聊聊</h3>
                  <p>
                    {{ feedbackExplanation }}
                  </p>
                  <span
                    >初始 {{ selectedScore + 10 }} 分
                    <ArrowRight :size="13" /> 陪伴频率 −10
                    <ArrowRight :size="13" /><strong
                      >调整后 {{ selectedScore }} 分</strong
                    ></span
                  >
                </div>
              </section>
            </div>
              </div>
              <div v-show="dateTab === 'note'" class="date-note-pane">
              <StreamNote
                :key="planRevision"
                :content="dateNote"
                :running="streaming && streamTarget === 'date'"
                :stopped="streamStopped"
                :error="streamTarget === 'date' ? streamError : ''"
                @stop="cancel"
                @retry="generatePlan"
                title="为什么这样安排"
              />
              </div>
            </section>
          </div>
        </template>

        <footer v-if="step === 'profile'" class="page-footer">
          <span>缘析 · 让相遇更懂你</span
          ><span>候选人物为虚构数据 · 适配分不代表恋爱概率</span
          ><span>Made for a little connection.</span>
        </footer>
      </main>
    </div>

    <div
      v-if="configOpen"
      class="config-overlay"
      role="presentation"
      @keydown.esc="closeModelConfiguration"
    >
      <section
        class="config-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="config-title"
      >
        <header class="config-dialog-header">
          <span class="config-icon"><KeyRound :size="22" /></span>
          <div>
            <span class="config-kicker">LOCAL MODEL SETUP</span>
            <h2 id="config-title">
              {{ configRequired ? "先连接你的模型服务" : "模型设置" }}
            </h2>
          </div>
          <button
            v-if="!configRequired"
            class="config-close"
            type="button"
            aria-label="关闭模型设置"
            @click="closeModelConfiguration"
          >
            <X :size="18" />
          </button>
        </header>

        <div v-if="configLoading" class="config-loading">
          <span class="config-spinner" aria-hidden="true"></span>
          正在读取本地配置…
        </div>

        <form v-else class="config-form" @submit.prevent="submitModelConfiguration">
          <p class="config-intro">
            配置只保存在这台电脑上。API Key 不会显示在页面中，也不会由状态接口返回。
          </p>

          <label class="config-field">
            <span>服务类型</span>
            <select v-model="modelConfig.provider" :disabled="configSaving">
              <option value="volcengine-ark">火山方舟</option>
              <option value="openai-compatible">OpenAI 兼容服务</option>
            </select>
          </label>

          <label class="config-field">
            <span>API Key</span>
            <div class="config-secret-field">
              <Input
                v-model="modelConfig.api_key"
                :type="showApiKey ? 'text' : 'password'"
                :placeholder="
                  modelConfig.has_api_key
                    ? '已保存；留空表示不修改'
                    : '请输入服务商提供的 API Key'
                "
                :disabled="configSaving"
                autocomplete="off"
                spellcheck="false"
              />
              <button
                type="button"
                :aria-label="showApiKey ? '隐藏 API Key' : '显示 API Key'"
                :title="showApiKey ? '隐藏 API Key' : '显示 API Key'"
                @click="showApiKey = !showApiKey"
              >
                <EyeOff v-if="showApiKey" :size="17" />
                <Eye v-else :size="17" />
              </button>
            </div>
          </label>

          <label class="config-field">
            <span>API 地址</span>
            <Input
              v-model="modelConfig.base_url"
              placeholder="例如：https://example.com/v1"
              :disabled="configSaving"
              autocomplete="off"
              spellcheck="false"
            />
            <small>填写 API 根地址，不要包含 /chat/completions</small>
          </label>

          <label class="config-field">
            <span>模型名称</span>
            <Input
              v-model="modelConfig.model"
              placeholder="请输入服务商提供的模型 ID"
              :disabled="configSaving"
              autocomplete="off"
              spellcheck="false"
            />
          </label>

          <p v-if="configError" class="config-error" role="alert">
            {{ configError }}
          </p>

          <div class="config-security-note">
            <ShieldCheck :size="16" />
            <span>密钥写入本机受 Git 忽略的 config.yaml，不会保存到浏览器。</span>
          </div>

          <div class="config-actions">
            <Button
              v-if="!configRequired"
              type="button"
              variant="outline"
              :disabled="configSaving"
              @click="closeModelConfiguration"
            >
              取消
            </Button>
            <Button type="submit" :disabled="configSaving">
              <span v-if="configSaving" class="config-spinner small" aria-hidden="true"></span>
              {{ configSaving ? "正在保存…" : configRequired ? "保存并进入" : "保存设置" }}
            </Button>
          </div>
        </form>
      </section>
    </div>

    <div v-if="toast" class="toast" role="status">
      <Check :size="16" />{{ toast
      }}<button aria-label="关闭提示" @click="toast = ''">
        <X :size="14" />
      </button>
    </div>
  </div>
</template>
