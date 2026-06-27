<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import ChatMessage from '~/components/ChatMessage.vue'
import { useChat } from '~/composables/useChat'
import { followUps, pickSuggestions } from '~/utils/suggestions'

const props = defineProps<{
  investorId: string
  enabled: boolean
  techSavviness: string | null
  companies: string[]
}>()
const { messages, isStreaming, send, clear } = useChat(() => props.investorId)

const draft = ref('')
const listEl = ref<HTMLElement | null>(null)
const suggestions = ref(pickSuggestions(props.techSavviness))

// When the assistant asks the user to choose a company, offer the investor's
// companies as one-click chips instead of making them type the name.
const ASKING_COMPANY =
  /which (company|one)|company would you like|provide a company|company name|name a company/i

const lastAssistant = computed(() => {
  const last = messages.value[messages.value.length - 1]
  return last && last.role === 'assistant' && !last.streaming && last.content ? last : null
})
const awaitingCompany = computed(
  () => lastAssistant.value !== null && ASKING_COMPANY.test(lastAssistant.value.content),
)
// Contextual next-step chips derived from the last answer's topic.
const followUpChips = computed(() =>
  lastAssistant.value && !awaitingCompany.value ? followUps(lastAssistant.value.content) : [],
)

async function submit() {
  const question = draft.value
  draft.value = ''
  await send(question)
}

function useSuggestion(text: string) {
  draft.value = text
  void submit()
}

watch(
  messages,
  async () => {
    await nextTick()
    if (listEl.value) {
      listEl.value.scrollTop = listEl.value.scrollHeight
    }
  },
  { deep: true },
)
</script>

<template>
  <div v-if="!enabled" class="flex h-full items-center justify-center p-4 text-center">
    <p class="text-sm text-neutral-500 dark:text-neutral-400">
      The assistant is not available right now.<br>
      Please contact the support team.
    </p>
  </div>

  <div v-else class="flex h-full min-h-0 flex-col">
    <div v-if="messages.length" class="mb-1 flex shrink-0 justify-end">
      <button
        type="button"
        class="text-xs text-neutral-400 transition-colors hover:text-neutral-700 dark:hover:text-neutral-200"
        @click="clear"
      >
        Clear chat
      </button>
    </div>

    <div ref="listEl" class="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
      <p v-if="!messages.length" class="text-sm text-neutral-500 dark:text-neutral-400">
        Ask about your holdings, fees, valuations, distributions or account statement. Every figure
        is computed from your data and cites the rows it came from.
      </p>
      <ChatMessage v-for="(m, i) in messages" :key="i" :message="m" />
    </div>

    <!-- Starter suggestions (empty chat). -->
    <div v-if="!messages.length" class="mt-2 flex flex-wrap gap-1.5">
      <button
        v-for="s in suggestions"
        :key="s"
        type="button"
        class="equitie-chip border border-neutral-300 text-left text-neutral-600 dark:border-neutral-700 dark:text-neutral-300"
        @click="useSuggestion(s)"
      >
        {{ s }}
      </button>
    </div>

    <!-- Company picker when the assistant asks which company. -->
    <div
      v-else-if="awaitingCompany && companies.length"
      class="mt-2 flex flex-wrap items-center gap-1.5"
    >
      <span class="text-xs text-neutral-400">Pick:</span>
      <button
        v-for="c in companies"
        :key="c"
        type="button"
        class="equitie-chip border border-equitie-blue/40 text-equitie-blue-dark dark:text-equitie-blue"
        @click="useSuggestion(c)"
      >
        {{ c }}
      </button>
    </div>

    <!-- Contextual follow-ups after an answer. -->
    <div
      v-else-if="followUpChips.length"
      class="mt-2 flex flex-wrap items-center gap-1.5"
    >
      <span class="text-xs text-neutral-400">Next:</span>
      <button
        v-for="s in followUpChips"
        :key="s"
        type="button"
        class="equitie-chip border border-neutral-300 text-left text-neutral-600 dark:border-neutral-700 dark:text-neutral-300"
        @click="useSuggestion(s)"
      >
        {{ s }}
      </button>
    </div>

    <form class="mt-3 flex gap-2" @submit.prevent="submit">
      <input
        v-model="draft"
        class="equitie-input flex-1"
        placeholder="Ask a question…"
        :disabled="isStreaming"
        maxlength="2000"
      >
      <button class="equitie-btn" type="submit" :disabled="isStreaming || !draft.trim()">
        Send
      </button>
    </form>
  </div>
</template>
