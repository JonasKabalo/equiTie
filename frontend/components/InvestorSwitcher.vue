<script setup lang="ts">
import { ref, watch } from 'vue'
import type { InvestorSummary } from '~/types/portfolio'

const props = defineProps<{ open: boolean, current?: string }>()
const emit = defineEmits<{ close: [] }>()

const base = useApiBase()
const { data: investors } = useFetch<InvestorSummary[]>(`${base}/api/investors`, { lazy: true })
const selected = ref(props.current ?? '')

watch(() => props.current, v => (selected.value = v ?? ''))

function go() {
  if (selected.value && selected.value !== props.current) {
    void navigateTo(`/dashboard/${selected.value}`)
  }
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      @click.self="emit('close')"
    >
      <div class="equitie-panel w-full max-w-md">
        <div class="mb-3 flex items-center justify-between">
          <h2 class="text-base font-semibold">Switch investor</h2>
          <button
            class="equitie-icon-btn !h-7 !w-7 !border-0"
            type="button"
            aria-label="Close"
            @click="emit('close')"
          >
            <span aria-hidden="true">✕</span>
          </button>
        </div>
        <select v-model="selected" class="equitie-input mb-3 w-full">
          <option value="" disabled>Choose an investor…</option>
          <option v-for="inv in investors ?? []" :key="inv.investor_id" :value="inv.investor_id">
            {{ inv.investor_name }} — {{ inv.investor_type }} · {{ inv.reporting_currency }} ·
            {{ inv.tech_savviness ?? '—' }} tech
          </option>
        </select>
        <button class="equitie-btn w-full" type="button" :disabled="!selected" @click="go">
          Open dashboard
        </button>
      </div>
    </div>
  </Teleport>
</template>
