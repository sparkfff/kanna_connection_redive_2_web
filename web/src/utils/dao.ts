// Shared by dashboard distribution tags and group daily-statistics images.
export function daoNumColor(dao: number): string {
  const colors: Record<number, string> = {
    3: '#10b981', 2.5: '#14b8a6', 2: '#f59e0b', 1.5: '#f97316',
    1: '#f43f5e', 0.5: '#ef4444', 0: '#94a3b8'
  }
  return colors[dao] || '#6366f1'
}
