<script setup lang="ts">
import { ref } from 'vue';
import type { InvestorSummary } from '~/types/portfolio';

const base = useApiBase();
const { data: investors, error } = await useFetch<InvestorSummary[]>(
  `${base}/api/investors`,
);
const selected = ref('');
</script>

<template>
  <div
    class="relative flex min-h-screen flex-col items-center justify-center p-6"
  >
    <div class="absolute right-4 top-4">
      <ThemeToggle />
    </div>
    <div class="equitie-panel w-full max-w-lg">
      <h1 class="text-xl font-semibold">EquiTie Investor Assistant</h1>
      <p class="mb-4 mt-1 text-sm text-neutral-500 dark:text-neutral-400">
        No login for the prototype — pick the investor to sign in as. The
        selection drives the personalisation (tone and depth adapt to their
        tech-savviness).
      </p>
      <p
        v-if="error"
        class="text-sm text-red-500"
      >
        Could not reach the API — is the backend running on port 8000?
      </p>

      <select
        v-model="selected"
        class="equitie-input mb-4 w-full"
      >
        <option
          value=""
          disabled
        >
          Choose an investor…
        </option>
        <option
          v-for="inv in investors ?? []"
          :key="inv.investor_id"
          :value="inv.investor_id"
        >
          {{ inv.investor_name }} — {{ inv.investor_type }} ·
          {{ inv.reporting_currency }} · {{ inv.tech_savviness ?? '—' }} tech ·
          {{ inv.num_deals }} deals
        </option>
      </select>

      <NuxtLink
        v-if="selected"
        :to="`/dashboard/${selected}`"
        class="equitie-btn block w-full text-center"
      >
        Open dashboard
      </NuxtLink>
      <button
        v-else
        type="button"
        disabled
        class="equitie-btn block w-full cursor-not-allowed text-center opacity-60"
      >
        Open dashboard
      </button>
    </div>
  </div>
</template>
