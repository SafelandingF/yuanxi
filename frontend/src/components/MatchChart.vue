<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from "vue";
import { init, use, type EChartsType } from "echarts/core";
import { PieChart } from "echarts/charts";
import { TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
use([PieChart, TooltipComponent, CanvasRenderer]);
const props = defineProps<{
  distribution: { high: number; medium: number; low: number };
  total: number;
}>();
const host = ref<HTMLDivElement>();
let chart: EChartsType | undefined, observer: ResizeObserver | undefined;
const items = () => [
  {
    name: "较高契合",
    value: props.distribution.high,
    itemStyle: { color: "#8c9a75" },
  },
  {
    name: "有待了解",
    value: props.distribution.medium,
    itemStyle: { color: "#b8bfa9" },
  },
  {
    name: "差异较多",
    value: props.distribution.low,
    itemStyle: { color: "#e0e3d6" },
  },
];
function render() {
  chart?.setOption({
    animation: false,
    tooltip: { trigger: "item", formatter: "{b}: {c} 人（{d}%）" },
    series: [
      {
        type: "pie",
        radius: ["60%", "82%"],
        center: ["50%", "50%"],
        label: { show: false },
        emphasis: { scale: false },
        data: items(),
      },
    ],
  });
}
onMounted(() => {
  if (!host.value) return;
  chart = init(host.value);
  render();
  observer = new ResizeObserver(() => chart?.resize());
  observer.observe(host.value);
});
watch(() => props.distribution, render, { deep: true });
onBeforeUnmount(() => {
  observer?.disconnect();
  chart?.dispose();
});
</script>
<template>
  <section class="match-chart">
    <span class="small-index">这组样本里的相遇可能</span>
    <h3>看看更完整的分布</h3>
    <div class="chart-wrap">
      <div ref="host" class="chart-canvas" aria-hidden="true"></div>
      <div class="chart-center">
        <strong>{{ total }}</strong
        ><span>位虚构候选</span>
      </div>
    </div>
    <ul>
      <li v-for="item in items()" :key="item.name">
        <i :style="{ background: item.itemStyle.color }"></i
        ><span>{{ item.name }}</span
        ><strong>{{ item.value }} 人</strong>
      </li>
    </ul>
    <p>较高 ≥80 分 · 中等 60–79 分<br />仅反映当前样本的规则分布</p>
  </section>
</template>
