<script setup lang="ts">
const colorMode = useColorMode()

function toggle() {
  colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'
}
</script>

<template>
  <button
    class="equitie-icon-btn"
    type="button"
    :aria-label="`Switch to ${colorMode.value === 'dark' ? 'light' : 'dark'} mode`"
    :title="`Switch to ${colorMode.value === 'dark' ? 'light' : 'dark'} mode`"
    @click="toggle"
  >
    <span aria-hidden="true">{{ colorMode.value === 'dark' ? '☀' : '☾' }}</span>
  </button>
</template>
