export function useApiBase(): string {
  return useRuntimeConfig().public.apiBase as string
}
