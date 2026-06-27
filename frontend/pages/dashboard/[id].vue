<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Portfolio } from '~/types/portfolio'
import { formatCurrency, formatMoic, formatNumber } from '~/utils/format'

const route = useRoute()
const investorId = computed(() => String(route.params.id))
const base = useApiBase()

const { data: portfolio } = await useFetch<Portfolio>(
  () => `${base}/api/portfolio/${investorId.value}`,
)
const { data: health } = await useFetch<{ chat_enabled: boolean }>(`${base}/api/health`)
const chatEnabled = computed(() => health.value?.chat_enabled ?? false)

const ccy = computed(() => portfolio.value?.reporting_currency ?? 'USD')
// Personalisation: less-technical investors also get inline explanations on the dashboard.
const verbose = computed(() => portfolio.value?.signals.tech_savviness !== 'High')

// Company names offered as one-click picks in the chat when the assistant asks.
const companies = computed(() =>
  portfolio.value
    ? [
        ...portfolio.value.holdings.map(h => h.company_name),
        ...portfolio.value.pending_commitments.map(p => p.company_name),
      ]
    : [],
)

const expanded = ref(new Set<string>())
function toggle(id: string) {
  if (expanded.value.has(id)) {
    expanded.value.delete(id)
  } else {
    expanded.value.add(id)
  }
}

function money(value: number): string {
  return formatCurrency(value, ccy.value)
}
</script>

<template>
  <div v-if="portfolio" class="flex min-h-[100dvh] flex-col lg:h-[100dvh] lg:overflow-hidden">
    <AppHeader :portfolio="portfolio" />

    <main class="flex-1 p-2 lg:min-h-0 lg:overflow-hidden">
      <div
        class="flex flex-col gap-2 lg:grid lg:h-full lg:grid-cols-3 lg:grid-rows-[auto_minmax(0,1fr)]"
      >
        <!-- KPIs -->
        <div class="grid grid-cols-2 gap-2 lg:col-span-3 lg:grid-cols-4">
          <KpiTile
            label="Portfolio value"
            :value="money(portfolio.total_current_value)"
            :explain="verbose ? 'Current marked value of your live holdings.' : undefined"
          />
          <KpiTile
            label="Blended MOIC"
            :value="formatMoic(portfolio.portfolio_moic)"
            :sub="`DPI ${formatMoic(portfolio.dpi)} · RVPI ${formatMoic(portfolio.rvpi)}`"
            :explain="verbose ? 'Times your contributed capital is now worth, incl. distributions.' : undefined"
          />
          <KpiTile
            label="Contributed"
            :value="money(portfolio.total_contributed)"
            :sub="`of ${money(portfolio.total_committed)} committed`"
            :explain="verbose ? 'What you have actually paid in so far.' : undefined"
          />
          <KpiTile
            label="Distributions"
            :value="money(portfolio.total_net_distributions)"
            :sub="`${portfolio.num_companies} companies · ${portfolio.num_deals} deals`"
            :explain="verbose ? 'Cash returned to you, net of carry.' : undefined"
          />
        </div>

        <!-- Left: charts (hidden on mobile) + holdings. On mobile this sits last. -->
        <div class="order-3 flex flex-col gap-2 lg:order-none lg:col-span-2 lg:row-start-2 lg:min-h-0">
          <div class="hidden md:block lg:min-h-0 lg:flex-1">
            <PortfolioCharts :portfolio="portfolio" />
          </div>

          <Panel
            title="Holdings — click a row for the per-round breakdown"
            expandable
            class="h-[22rem] lg:h-auto lg:min-h-0 lg:flex-1"
          >
            <table v-if="portfolio.holdings.length" class="equitie-table">
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Sector</th>
                  <th>Status</th>
                  <th class="!text-right">Value</th>
                  <th class="!text-right">Contributed</th>
                  <th class="!text-right">MOIC</th>
                </tr>
              </thead>
              <tbody>
                <template v-for="h in portfolio.holdings" :key="h.company_id">
                  <tr
                    class="cursor-pointer hover:bg-neutral-100 dark:hover:bg-neutral-800/50"
                    @click="toggle(h.company_id)"
                  >
                    <td>
                      <span class="inline-block w-3 text-neutral-400">
                        {{ expanded.has(h.company_id) ? '▾' : '▸' }}
                      </span>
                      {{ h.company_name }}
                      <span v-if="h.rounds.length > 1" class="ml-1 text-[10px] text-neutral-400">
                        ×{{ h.rounds.length }} rounds
                      </span>
                    </td>
                    <td class="text-neutral-500">{{ h.sector }}</td>
                    <td>{{ h.company_status }}</td>
                    <td class="text-right">{{ money(h.current_value) }}</td>
                    <td class="text-right">{{ money(h.contributed) }}</td>
                    <td class="text-right">{{ formatMoic(h.moic) }}</td>
                  </tr>
                  <tr v-if="expanded.has(h.company_id)" class="bg-neutral-50 dark:bg-neutral-900/40">
                    <td colspan="6" class="p-2">
                      <table class="equitie-table">
                        <thead>
                          <tr>
                            <th>Round</th>
                            <th>Deal</th>
                            <th class="!text-right">Price paid</th>
                            <th class="!text-right">Latest</th>
                            <th class="!text-right">Units</th>
                            <th class="!text-right">Value</th>
                            <th class="!text-right">Contributed</th>
                            <th class="!text-right">MOIC</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="r in h.rounds" :key="r.deal_id">
                            <td>{{ r.round }}</td>
                            <td class="text-neutral-500">{{ r.deal_id }} · {{ r.deal_currency }}</td>
                            <td class="text-right">{{ formatNumber(r.effective_share_price, 2) }}</td>
                            <td class="text-right">{{ formatNumber(r.latest_share_price, 2) }}</td>
                            <td class="text-right">{{ formatNumber(r.units) }}</td>
                            <td class="text-right">{{ money(r.current_value_reporting) }}</td>
                            <td class="text-right">{{ money(r.contributed_reporting) }}</td>
                            <td class="text-right">{{ formatMoic(r.moic) }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
            <div
              v-else
              class="flex h-full flex-col items-center justify-center gap-2 p-4 text-center"
            >
              <template v-if="portfolio.pending_commitments.length">
                <p class="text-base font-medium">Commitment pending</p>
                <p class="max-w-md text-sm text-neutral-500 dark:text-neutral-400">
                  You've committed
                  <span class="equitie-num font-medium text-neutral-700 dark:text-neutral-200">
                    {{ money(portfolio.pending_commitments[0].outstanding_reporting) }}
                  </span>
                  to {{ portfolio.pending_commitments[0].company_name }}
                  ({{ portfolio.pending_commitments[0].round }}), but it hasn't been called yet —
                  no capital is deployed, so there is nothing to value. It will appear here once the
                  capital call is funded.
                </p>
              </template>
              <template v-else>
                <p class="text-base font-medium">No investments yet</p>
                <p class="max-w-md text-sm text-neutral-500 dark:text-neutral-400">
                  {{ portfolio.investor_name }} is onboarded but hasn't funded any deals. Your
                  holdings, valuations and MOIC will appear here once your first commitment is called.
                </p>
              </template>
              <p class="text-xs text-neutral-400 dark:text-neutral-500">
                KYC: {{ portfolio.signals.kyc_status }}
                <template v-if="portfolio.signals.onboarded_date">
                  · onboarded {{ portfolio.signals.onboarded_date }}
                </template>
              </p>
            </div>
            <p
              v-if="portfolio.holdings.length && portfolio.pending_commitments.length"
              class="mt-2 text-xs text-neutral-500"
            >
              Pending (unfunded):
              {{
                portfolio.pending_commitments
                  .map(p => `${p.company_name} ${money(p.outstanding_reporting)}`)
                  .join(', ')
              }}
            </p>
          </Panel>
        </div>

        <!-- Right: chat. On mobile this sits directly under the KPIs. -->
        <Panel
          title="Ask your assistant"
          expandable
          class="order-2 h-[26rem] lg:order-none lg:h-auto lg:col-start-3 lg:row-start-2 lg:min-h-0"
        >
          <ClientOnly>
            <ChatPanel
              :key="investorId"
              :investor-id="investorId"
              :enabled="chatEnabled"
              :tech-savviness="portfolio.signals.tech_savviness"
              :companies="companies"
            />
          </ClientOnly>
        </Panel>
      </div>
    </main>
  </div>

  <div v-else class="flex min-h-screen flex-col items-center justify-center gap-3">
    <p class="text-neutral-500">Investor not found.</p>
    <NuxtLink to="/" class="equitie-btn">Back to picker</NuxtLink>
  </div>
</template>
