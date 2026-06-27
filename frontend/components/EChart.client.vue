<script setup lang="ts">
// .client.vue → only bundled/executed on the client, so vue-echarts (which touches
// `document` at import time) never runs during SSR. This is what fixes the
// "document is not defined" crash on refresh / direct navigation.
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'
import VChart from 'vue-echarts'

use([BarChart, PieChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

defineProps<{ option: EChartsOption }>()
</script>

<template>
  <VChart class="h-full min-h-[12rem]" :option="option" autoresize />
</template>
