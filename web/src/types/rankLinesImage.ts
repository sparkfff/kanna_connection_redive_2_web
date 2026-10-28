import type { RankLine } from '@/api'

export interface RankLinesImageData {
  clan_battle_id: number
  lines: (RankLine | null)[]
  my: RankLine | null
  updated_at: number
  cached: boolean
  stale: boolean
}
