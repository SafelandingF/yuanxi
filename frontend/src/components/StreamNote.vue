<script setup lang="ts">
import { ref, watch, nextTick, onBeforeUnmount } from "vue";
import {
  ArrowDown,
  Check,
  Copy,
  RotateCcw,
  Square,
  Sparkles,
} from "@lucide/vue";
import MessageResponse from "@/components/ai-elements/message/MessageResponse.vue";
import { Button } from "@/components/ui/button";
const props = defineProps<{
  content: string;
  title?: string;
  compact?: boolean;
  running?: boolean;
  stopped?: boolean;
  error?: string;
}>();
const emit = defineEmits<{ stop: []; retry: [] }>();
const copied = ref(false),
  copyError = ref(false),
  follow = ref(true);
const viewport = ref<HTMLElement>();
let copyTimer: ReturnType<typeof setTimeout> | undefined;
let scrollFrame: number | undefined;
let disposed = false;
function pauseFollow() {
  follow.value = false;
  if (scrollFrame !== undefined) cancelAnimationFrame(scrollFrame);
  scrollFrame = undefined;
}
function scrollToLatest() {
  if (!follow.value || disposed || scrollFrame !== undefined) return;
  scrollFrame = requestAnimationFrame(() => {
    scrollFrame = undefined;
    if (!follow.value || disposed) return;
    const el = viewport.value;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "instant" });
  });
}
watch(
  () => props.content,
  async () => {
    if (!follow.value) return;
    await nextTick();
    // User input may have paused following while Vue was rendering.
    scrollToLatest();
  },
);
function onWheel(event: WheelEvent) {
  if (event.deltaY !== 0) pauseFollow();
}
function onKeydown(event: KeyboardEvent) {
  if (["ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home", "End", " "].includes(event.key)) {
    pauseFollow();
  }
}
function latest() {
  follow.value = true;
  scrollToLatest();
}
async function copy() {
  try {
    await navigator.clipboard.writeText(props.content);
    copied.value = true;
    copyError.value = false;
    clearTimeout(copyTimer);
    copyTimer = setTimeout(() => (copied.value = false), 1800);
  } catch {
    copyError.value = true;
  }
}
onBeforeUnmount(() => {
  disposed = true;
  pauseFollow();
  clearTimeout(copyTimer);
});
</script>
<template>
  <section class="stream-note">
    <div v-if="!compact" class="stream-heading">
      <span><Sparkles :size="15" />{{ title || "给你的一点观察" }}</span
      ><span class="tiny-label">豆包生成</span>
    </div>
    <div
      ref="viewport"
      class="stream-viewport"
      :aria-busy="running"
      tabindex="0"
      aria-label="生成内容，可滚动阅读"
      @wheel.passive="onWheel"
      @pointerdown="pauseFollow"
      @touchstart.passive="pauseFollow"
      @keydown="onKeydown"
    >
      <MessageResponse :content="content" /><span
        v-if="running"
        class="stream-cursor"
      ></span>
      <p v-if="!content && running">正在整理资料…</p>
      <p v-if="!content && !running">
        {{ error ? "暂未生成说明，请重试。" : "说明尚未生成。" }}
      </p>
    </div>
    <div class="stream-actions">
      <span class="stream-status" role="status">{{
        running
          ? "正在生成…"
          : error
            ? "生成失败，已保留当前内容"
            : stopped
              ? "已停止，保留当前内容"
              : content ? "说明已完成" : "等待生成说明"
      }}</span>
      <div>
        <Button v-if="!follow" variant="ghost" size="sm" @click="latest"
          ><ArrowDown :size="14" />回到最新</Button
        ><Button v-if="running" variant="ghost" size="sm" @click="emit('stop')"
          ><Square :size="12" />停止</Button
        ><Button v-else variant="ghost" size="sm" @click="emit('retry')"
          ><RotateCcw :size="13" />重新生成</Button
        ><Button
          variant="ghost"
          size="icon"
          :disabled="!content"
          :aria-label="copied ? '已复制' : '复制观察'"
          @click="copy"
          ><Check v-if="copied" :size="14" /><Copy v-else :size="14"
        /></Button>
      </div>
    </div>
    <p v-if="error" role="alert" class="error-text">{{ error }}</p>
    <p v-if="copyError" role="alert" class="error-text">
      复制失败，请手动选择文字复制。
    </p>
  </section>
</template>
