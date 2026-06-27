<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ title?: string, expandable?: boolean }>()
const expanded = ref(false)
</script>

<template>
  <!-- Single root: when expanded, the section becomes a fixed overlay (its slot
       content stays mounted, so charts/chat keep their state). A teleported
       backdrop sits behind it. -->
  <section
    :class="[
      'equitie-panel flex min-h-0 flex-col',
      expanded ? 'fixed inset-2 z-50 !h-auto sm:inset-6 lg:inset-10' : '',
    ]"
  >
    <div class="mb-2 flex items-center justify-between gap-2">
      <div class="equitie-stat-label truncate">{{ title }}</div>
      <button
        v-if="expandable"
        type="button"
        class="equitie-icon-btn !h-6 !w-6 !border-0 text-base"
        :aria-label="expanded ? 'Collapse panel' : 'Expand panel'"
        :title="expanded ? 'Collapse' : 'Expand'"
        @click="expanded = !expanded"
      >
        <span aria-hidden="true">{{ expanded ? '✕' : '⤢' }}</span>
      </button>
    </div>
    <div class="min-h-0 flex-1 overflow-auto">
      <slot />
    </div>
    <Teleport to="body">
      <div
        v-if="expanded"
        class="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
        @click="expanded = false"
      />
    </Teleport>
  </section>
</template>
