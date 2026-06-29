// Recover from a failed route-chunk dynamic import. Two cases we want to survive:
//   • prod — a new deployment changed the chunk hashes while this client still
//     holds the old HTML, so the requested chunk 404s on the next navigation;
//   • dev — Vite re-optimises a newly-seen dependency mid-navigation and 504s the
//     in-flight request (the "first click does nothing" symptom).
// Nuxt's built-in handler only reacts to Vite *preload* errors, so it misses the
// dep-504 case. We match the navigation error ourselves and hard-load the target
// route; by then the chunk (or freshly-optimised dep) is available.
const DYNAMIC_IMPORT_ERROR =
  /Failed to fetch dynamically imported module|error loading dynamically imported module|Importing a module script failed/i

export default defineNuxtPlugin(() => {
  const router = useRouter()
  router.onError((error, to) => {
    const message = error instanceof Error ? error.message : String(error)
    if (DYNAMIC_IMPORT_ERROR.test(message) && to?.fullPath) {
      window.location.assign(to.fullPath)
    }
  })
})
