<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMessage } from '~/composables/useChat'
import { renderMarkdown } from '~/utils/markdown'

const props = defineProps<{ message: ChatMessage }>()
const html = computed(() => renderMarkdown(props.message.content))
</script>

<template>
  <div :class="message.role === 'user' ? 'flex justify-end' : 'flex justify-start'">
    <div
      :class="[
        'max-w-[90%] rounded-lg px-3 py-2 text-sm',
        message.role === 'user' ? 'bg-equitie-blue-dark text-white' : 'equitie-panel',
      ]"
    >
      <!-- While thinking, show which tools are running; clear them once the answer streams. -->
      <div v-if="message.streaming && !message.content" class="flex flex-col gap-1.5">
        <div v-if="message.tools.length" class="flex flex-wrap gap-1">
          <span
            v-for="(t, i) in message.tools"
            :key="i"
            class="equitie-chip bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300"
          >
            ⚙ {{ t }}
          </span>
        </div>
        <span class="animate-pulse text-neutral-400">Thinking…</span>
      </div>

      <template v-else>
        <!-- html is sanitised by DOMPurify in renderMarkdown -->
        <div class="equitie-markdown" v-html="html" />
        <span v-if="message.streaming" class="ml-0.5 animate-pulse">▍</span>
        <ul
          v-if="message.citations.length"
          class="mt-2 flex flex-wrap items-center gap-1 border-t border-neutral-200 pt-2 dark:border-neutral-800"
        >
          <li class="mr-1 text-[10px] font-medium uppercase tracking-wide text-neutral-400">
            sources
          </li>
          <li
            v-for="(c, i) in message.citations"
            :key="i"
            class="equitie-chip bg-neutral-100 text-[10px] text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400"
          >
            {{ c.row_id }}
          </li>
        </ul>
      </template>
    </div>
  </div>
</template>
