const apiBase = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8000'

export function resolveMediaUrl(path: string | null | undefined): string | null {
  if (!path) return null
  if (path.startsWith('http') || path.startsWith('blob:') || path.startsWith('data:')) return path
  return `${apiBase}${path}`
}
