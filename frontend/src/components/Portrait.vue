<script setup lang="ts">
defineProps<{ variant: string; small?: boolean }>();
</script>

<template>
  <div class="portrait" :class="[variant, { small }]" aria-hidden="true">
    <div class="portrait-sun"></div>
    <div class="portrait-orbit"></div>
    <div class="portrait-body"></div>
    <div class="portrait-hair"></div>
    <div class="portrait-face"></div>
    <div class="portrait-fringe"></div>
    <div class="portrait-neck"></div>
    <span class="portrait-caption">a little more connection.</span>
  </div>
</template>
