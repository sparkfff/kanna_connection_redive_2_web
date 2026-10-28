import type { BossInfoCounter } from './index'

export interface StatusMember {
  name: string
  text: string
  lap: number
}

export interface StatusBoss extends Omit<BossInfoCounter, 'subscribe' | 'apply' | 'tree'> {
  subscribe: StatusMember[]
  apply: StatusMember[]
  tree: StatusMember[]
}

export interface StatusImageData {
  clan_name: string
  stage: string
  rank: number
  state: string
  monitor_name: string
  generated_at: string
  full_count: number
  tail_count: number
  carry_count: number
  remaining_carries?: { pcrid: number; name: string; detail: string; uncertain: boolean }[]
  boss: StatusBoss[]
}
