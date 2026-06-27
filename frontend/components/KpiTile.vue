<script setup lang="ts">
defineProps<{ label: string, value: string, sub?: string, explain?: string }>()
</script>

<template>
  <div class="equitie-panel min-w-0 overflow-hidden">
    <div class="equitie-stat-label">{{ label }}</div>
    <div class="equitie-stat-value">{{ value }}</div>
    <div v-if="sub" class="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{{ sub }}</div>
    <div
      v-if="explain"
      class="mt-1.5 text-[11px] leading-snug text-neutral-400 dark:text-neutral-500"
    >
      {{ explain }}
    </div>
  </div>
</template>
