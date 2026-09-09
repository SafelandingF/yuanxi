<script setup lang="ts">
import {
  computed,
  defineAsyncComponent,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
} from "vue";
import {
  ArrowDown,
  Check,
  ChevronDown,
  Send,
  SlidersHorizontal,
  Sparkles,
  Square,
  Wrench,
} from "@lucide/vue";
import { Button } from "@/components/ui/button";
import AgentCardView from "./AgentCard.vue";
import type { AgentPart, AgentSession, AgentTurn } from "@/lib/agent";
import { preferenceLabels, sessionRequest } from "@/lib/agent";
import { readStream, type RankedCandidate } from "@/lib/api";
const MessageResponse = defineAsyncComponent(
  () => import("./ai-elements/message/MessageResponse.vue"),
);
const props = defineProps<{ session: AgentSession }>();
const emit = defineEmits<{
  update: [session: AgentSession];
  arrange: [candidate: RankedCandidate];
}>();
const input = ref(""),
  busy = ref(false),
  error = ref(""),
  pending = ref<AgentTurn | null>(null);
const scroll = ref<HTMLElement>(),
  composer = ref<HTMLTextAreaElement>(),
  following = ref(true);
let controller: AbortController | undefined;
let lastRequest:
  | {
      request_id: string;
      text: string;
      selection?: { candidate_id: number; revision: number };
    }
  | undefined;
let disposed = false;
const turns = computed(() => [
  ...props.session.turns,
  ...(pending.value ? [pending.value] : []),
]);
const chosen = computed(() =>
  props.session.candidates.find((c) => c.id === props.session.selected_id),
);
const actionLabel = computed(() => {
  const running = pending.value?.parts.find((p) => p.type === "tool_start");
  return running?.label || "匹配助手正在回复";
});
function toolsFor(turn: AgentTurn) {
  return turn.parts.filter(
    (p) => p.type === "tool_start" || p.type === "tool_end",
  );
}
function contentFor(turn: AgentTurn) {
  return turn.parts.filter((p) => p.type === "text" || p.type === "card");
}
function toolSummary(turn: AgentTurn) {
  const tools = toolsFor(turn);
  const running = tools.find((p) => p.type === "tool_start");
  if (running) return running.label;
  if (tools.some((p) => p.status === "error")) return "处理记录 · 有操作未完成";
  return `已完成 ${tools.length} 项操作`;
}
function resizeComposer() {
  const el = composer.value;
  if (!el) return;
  el.style.height = "auto";
  el.style.height = `${Math.min(el.scrollHeight, 144)}px`;
}
function trackScroll() {
  const el = scroll.value;
  if (el)
    following.value = el.scrollHeight - el.scrollTop - el.clientHeight < 100;
}
async function scrollLatest(force = false) {
  await nextTick();
  if (scroll.value && (following.value || force))
    scroll.value.scrollTop = scroll.value.scrollHeight;
}
function stop() {
  controller?.abort();
}
function receivePart(item: AgentPart) {
  if (!pending.value) return;
  const parts = pending.value.parts;
  if (item.type === "text" && parts.at(-1)?.type === "text")
    parts.at(-1)!.text += item.text || "";
  else if (item.type === "tool_end") {
    const started = parts.find((p) => p.id === item.id);
    if (started) Object.assign(started, item);
  } else parts.push(item);
  void scrollLatest();
}
async function send(
  text: string,
  selection?: { candidate_id: number; revision: number },
  retry = false,
) {
  if (busy.value || (!text.trim() && !selection)) return;
  const request =
    retry && lastRequest
      ? lastRequest
      : {
          request_id: crypto.randomUUID(),
          text: text.trim(),
          ...(selection ? { selection } : {}),
        };
  lastRequest = request;
  pending.value = { id: request.request_id, user: request.text, parts: [] };
  error.value = "";
  busy.value = true;
  input.value = "";
  void nextTick(resizeComposer);
  following.value = true;
  controller = new AbortController();
  void scrollLatest(true);
  try {
    await readStream(
      `/api/agent/sessions/${props.session.session_id}/chat`,
      request,
      controller.signal,
      (event) => {
        if (event.type === "delta")
          receivePart({ type: "text", text: event.text });
        if (
          event.type === "tool_start" ||
          event.type === "tool_end" ||
          event.type === "card"
        )
          receivePart(event);
        if (event.type === "state") {
          emit("update", event.session);
          pending.value = null;
        }
      },
    );
  } catch (e) {
    if (disposed) return;
    // Reconcile a response that committed just before a connection dropped.
    let committed = false;
    try {
      const latest = await sessionRequest(
        `/api/agent/sessions/${props.session.session_id}`,
      );
      emit("update", latest);
      committed = latest.turns.some((t) => t.id === request.request_id);
    } catch {}
    if (committed) pending.value = null;
    else {
      error.value = controller.signal.aborted
        ? "已停止。本轮尚未保存，可以重新发送。"
        : `${e instanceof Error ? e.message : "连接失败"}。本轮修改未保存。`;
      if (pending.value) {
        pending.value.failed = true;
        for (const part of pending.value.parts)
          if (part.type === "tool_start") {
            part.type = "tool_end";
            part.status = "error";
            part.summary = "本轮已中断";
          }
      }
    }
  } finally {
    if (!disposed) {
      busy.value = false;
      void scrollLatest();
    }
  }
}
function select(candidate: RankedCandidate, revision: number) {
  void send(`我选择 ${candidate.name}`, {
    candidate_id: candidate.id,
    revision,
  });
}
function arrange() {
  if (chosen.value && !busy.value) emit("arrange", chosen.value);
}
function keydown(e: KeyboardEvent) {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    void send(input.value);
  }
}
onMounted(() => {
  if (!props.session.turns.length)
    void send(
      "请根据我的资料理解我的偏好，推荐几位有共同点的人，并说明值得商量的差异。",
    );
  else void scrollLatest(true);
});
onBeforeUnmount(() => {
  disposed = true;
  controller?.abort();
});
</script>
<template>
  <section class="agent-workspace" aria-label="匹配助手">
    <section class="conversation" aria-label="与匹配助手的对话">
      <div ref="scroll" class="conversation-scroll" @scroll="trackScroll">
        <div class="conversation-content">
          <article
            v-for="turn in turns"
            :key="turn.id"
            class="chat-turn"
            :class="{ 'turn-failed': turn.failed }"
          >
            <div class="user-message">
              <span>{{ turn.user }}</span>
            </div>
            <div class="assistant-message">
              <div class="assistant-byline">
                <Sparkles :size="15" /><small v-if="turn.failed"
                  >本轮未保存</small
                >
              </div>
              <details v-if="toolsFor(turn).length" class="turn-tools">
                <summary>
                  <span
                    class="working-dot"
                    v-if="toolsFor(turn).some((p) => p.type === 'tool_start')"
                  ></span
                  ><Check v-else :size="12" /><span>{{
                    toolSummary(turn)
                  }}</span
                  ><ChevronDown :size="12" />
                </summary>
                <details
                  v-for="part in toolsFor(turn)"
                  :key="part.id"
                  class="tool-activity"
                  :class="part.status || 'running'"
                >
                  <summary>
                    <Wrench :size="12" /><span>{{ part.label }}</span
                    ><em v-if="part.duration_ms !== undefined"
                      >{{ (part.duration_ms / 1000).toFixed(1) }}s</em
                    ><ChevronDown :size="12" />
                  </summary>
                  <div class="tool-details">
                    <p>{{ part.summary || "正在执行…" }}</p>
                    <strong>输入 · {{ part.name }}</strong>
                    <pre>{{ JSON.stringify(part.input, null, 2) }}</pre>
                    <template v-if="part.output"
                      ><strong>结果</strong>
                      <pre>{{ JSON.stringify(part.output, null, 2) }}</pre>
                    </template>
                  </div>
                </details>
              </details>
              <template v-for="(part, index) in contentFor(turn)" :key="index">
                <div v-if="part.type === 'text'" class="agent-markdown">
                  <MessageResponse :content="part.text || ''" />
                </div>
                <AgentCardView
                  v-else-if="part.card"
                  :card="part.card"
                  :revision="session.revision"
                  :candidate-ids="session.candidates.map((c) => c.id)"
                  :selected-id="session.selected_id"
                  :disabled="busy || Boolean(turn.failed)"
                  @select="select"
                  @prompt="send"
                  @arrange="arrange"
                />
              </template>
              <div
                v-if="
                  busy &&
                  pending?.id === turn.id &&
                  !toolsFor(turn).some((p) => p.type === 'tool_start')
                "
                class="agent-working"
                role="status"
              >
                <span class="working-dot"></span>{{ actionLabel }}
              </div>
            </div>
          </article>
        </div>
      </div>
      <div class="composer-area">
        <div class="composer-content">
          <button
            v-if="!following"
            class="jump-latest"
            @click="scrollLatest(true)"
          >
            <ArrowDown :size="13" />最新消息
          </button>
          <div v-if="error" class="chat-error" role="alert">
            <span>{{ error }}</span
            ><button
              :disabled="busy"
              @click="
                send(lastRequest?.text || '', lastRequest?.selection, true)
              "
            >
              重试
            </button>
          </div>
          <form class="chat-composer" @submit.prevent="send(input)">
            <textarea
              ref="composer"
              v-model="input"
              aria-label="给匹配助手发消息"
              placeholder="聊聊你更在意什么…"
              rows="1"
              maxlength="2000"
              @input="resizeComposer"
              @keydown="keydown"
            ></textarea>
            <div class="sender-toolbar">
              <details class="sender-preferences">
                <summary>
                  <SlidersHorizontal :size="13" />筛选条件<ChevronDown
                    :size="11"
                  />
                </summary>
                <div class="preferences-popover">
                  <span
                    v-for="tag in preferenceLabels(session.preferences)"
                    :key="tag"
                    >{{ tag }}</span
                  ><small>在对话中说出你想调整的条件</small>
                </div>
              </details>
              <Button
                v-if="busy"
                type="button"
                variant="outline"
                size="sm"
                @click="stop"
                ><Square :size="13" />停止</Button
              >
              <Button
                v-else
                type="submit"
                size="sm"
                :disabled="!input.trim()"
                aria-label="发送消息"
                ><Send :size="15"
              /></Button>
            </div>
          </form>
        </div>
      </div>
    </section>
  </section>
</template>
