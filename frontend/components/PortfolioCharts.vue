<script setup lang="ts">
// Type-only import — erased at compile, so no echarts runtime code runs here on
// the server. The actual chart renders in <EChart> (a .client component).
import type { EChartsOption } from 'echarts'
import { computed } from 'vue'
import type { Portfolio } from '~/types/portfolio'

const props = defineProps<{ portfolio: Portfolio }>()

const BLUES = ['#2f81f7', '#1f6feb', '#0d419d', '#388bfd', '#79c0ff', '#1158c7', '#58a6ff']
const AXIS = '#8b949e'

const hasHoldings = computed(() => props.portfolio.holdings.length > 0)

const valueByCompany = computed<EChartsOption>(() => {
  const holdings = [...props.portfolio.holdings].sort((a, b) => b.current_value - a.current_value)
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 8, right: 16, top: 12, bottom: 4, containLabel: true },
    xAxis: { type: 'value', axisLabel: { color: AXIS }, splitLine: { show: false } },
    yAxis: {
      type: 'category',
      inverse: true,
      data: holdings.map(h => h.company_name),
      axisLabel: { color: AXIS },
    },
    series: [
      {
        type: 'bar',
        data: holdings.map(h => Math.round(h.current_value)),
        itemStyle: { color: '#2f81f7', borderRadius: [0, 3, 3, 0] },
      },
    ],
  }
})

const bySector = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'item' },
  // Legend on top so slice labels never overlap it.
  legend: { top: 0, type: 'scroll', textStyle: { color: AXIS } },
  series: [
    {
      type: 'pie',
      radius: ['42%', '66%'],
      center: ['50%', '60%'],
      label: { show: false },
      data: props.portfolio.top_sectors.map((s, i) => ({
        name: s.sector,
        value: Math.round(s.contributed),
        itemStyle: { color: BLUES[i % BLUES.length] },
      })),
    },
  ],
}))
</script>

<template>
  <div class="grid h-full grid-cols-1 gap-2 sm:grid-cols-2">
    <Panel title="Current value by company" expandable>
      <EChart v-if="hasHoldings" :option="valueByCompany" />
      <div v-else class="flex h-full items-center justify-center p-2 text-sm text-neutral-500">
        No holdings to chart yet.
      </div>
    </Panel>
    <Panel title="Capital by sector" expandable>
      <EChart v-if="hasHoldings" :option="bySector" />
      <div v-else class="flex h-full items-center justify-center p-2 text-sm text-neutral-500">
        No holdings to chart yet.
      </div>
    </Panel>
  </div>
</template>
