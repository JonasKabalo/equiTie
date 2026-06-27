<script setup lang="ts">
import { ref } from 'vue'
import type { Portfolio } from '~/types/portfolio'

defineProps<{ portfolio: Portfolio }>()
const switcherOpen = ref(false)
</script>

<template>
  <header
    class="flex h-10 shrink-0 items-center justify-between gap-2 border-b border-neutral-200 px-3 dark:border-neutral-800"
  >
    <div class="flex min-w-0 items-center gap-2">
      <span class="shrink-0 font-semibold tracking-tight">EquiTie</span>
      <span class="shrink-0 text-neutral-300 dark:text-neutral-700">/</span>
      <span class="truncate font-medium">{{ portfolio.investor_name }}</span>
      <span class="equitie-chip hidden shrink-0 bg-equitie-blue-dark/15 text-equitie-blue-dark sm:inline-flex dark:text-equitie-blue">
        {{ portfolio.reporting_currency }}
      </span>
      <span
        class="equitie-chip hidden shrink-0 bg-neutral-200 text-neutral-600 sm:inline-flex dark:bg-neutral-800 dark:text-neutral-300"
      >
        {{ portfolio.signals.tech_savviness ?? '—' }} tech · {{ portfolio.signals.num_deals }} deals
      </span>
    </div>

    <div class="flex shrink-0 items-center gap-1.5">
      <ThemeToggle />
      <button
        class="equitie-icon-btn"
        type="button"
        aria-label="Switch investor"
        title="Switch investor"
        @click="switcherOpen = true"
      >
        <span aria-hidden="true">⇄</span>
      </button>
      <NuxtLink class="equitie-icon-btn" to="/" aria-label="Back to start" title="Back to start">
        <span aria-hidden="true">⏻</span>
      </NuxtLink>
    </div>

    <InvestorSwitcher
      :open="switcherOpen"
      :current="portfolio.investor_id"
      @close="switcherOpen = false"
    />
  </header>
</template>
