// Shared by the interactive dashboard and its image view.
export const bossAvatarUrl = (unitId: number) =>
  `https://redive.estertion.win/icon/unit/${unitId}.webp`

export type LapLevel = '' | 'low' | 'high'

export function bossLapLevel(lap: number, bosses: Array<{ lap: number }>): LapLevel {
  const laps = [...new Set(bosses.map(boss => boss.lap).filter(value => value > 0))].sort((a, b) => a - b)
  // Only distinguish the two concurrently visible laps. Unknown or anomalous
  // snapshots must not be assigned a misleading high/low label.
  if (laps.length !== 2) return ''
  return lap === laps[0] ? 'low' : lap === laps[1] ? 'high' : ''
}

