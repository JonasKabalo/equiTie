// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-01-15',
  devtools: { enabled: false },
  modules: ['@nuxtjs/tailwindcss', '@nuxtjs/color-mode', '@nuxt/eslint'],
  tailwindcss: {
    cssPath: '~/assets/css/main.css',
    configPath: 'tailwind.config.ts',
  },
  colorMode: {
    classSuffix: '',
    preference: 'dark',
    fallback: 'dark',
  },
  // We don't use route rules / payload revalidation; disabling the app manifest
  // removes the dev-only "Failed to resolve import #app-manifest" warning.
  experimental: {
    appManifest: false,
  },
  vite: {
    optimizeDeps: {
      // These deps are only reached from the dashboard route. Without pre-bundling
      // them at dev-server startup, the first navigation makes Vite discover and
      // re-optimise them mid-request — it returns a 504 "Outdated Optimize Dep",
      // the route's dynamic import rejects, and the click silently does nothing
      // (you have to click again once optimisation finishes). Production builds
      // pre-bundle everything via Rollup, so this only bites in `nuxt dev`.
      include: [
        'markdown-it',
        'dompurify',
        'vue-echarts',
        'echarts/core',
        'echarts/charts',
        'echarts/components',
        'echarts/renderers',
      ],
    },
  },
  runtimeConfig: {
    // Override at runtime with NUXT_PUBLIC_API_BASE (Nuxt maps it automatically).
    public: {
      apiBase: 'http://localhost:8000',
    },
  },
  app: {
    head: {
      title: 'EquiTie Investor Assistant',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      ],
    },
  },
})
