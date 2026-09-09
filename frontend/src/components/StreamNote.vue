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
watch(
  () => props.content,
  async () => {
    if (follow.value) {
      await nextTick();
      viewport.value?.scrollTo({ top: viewport.value.scrollHeight });
    }
  },
);
function onScroll() {
  const el = viewport.value;
  if (el) follow.value = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
}
function latest() {
  follow.value = true;
  viewport.value?.scrollTo({
    top: viewport.value.scrollHeight,
    behavior: "smooth",
  });
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
onBeforeUnmount(() => clearTimeout(copyTimer));
</script>
<template>
  <section class="stream-note">
    <div class="stream-heading">
      <span><Sparkles :size="15" />{{ title || "给你的一点观察" }}</span
      ><span class="tiny-label">豆包生成</span>
    </div>
    <div
      ref="viewport"
      class="stream-viewport"
      :aria-busy="running"
      @scroll="onScroll"
    >
      <MessageResponse :content="content" /><span
        v-if="running"
        class="stream-cursor"
      ></span>
      <p v-if="!content && running">正在准备说明，行程和生成过程可随时切换查看。</p>
      <p v-if="!content && !running">
        {{ error ? "暂未生成说明，请重试。" : "说明尚未生成。" }}
      </p>
    </div>
    <div class="stream-actions">
      <span class="stream-status" role="status">{{
        running
          ? "正在生成安排说明…"
          : error
            ? "生成失败，已保留当前内容"
            : stopped
              ? "已停止，保留当前内容"
              : content ? "说明已完成" : "等待生成说明"
      }}</span>
      <div>
        <Button v-if="!follow" variant="ghost" size="sm" @click="latest"
          ><ArrowDown :size="14" />最新</Button
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
