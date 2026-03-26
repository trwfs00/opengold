import type { BotId } from '@/context/BotContext'

export const BOT_META = {
  gold: {
    symbol: 'XAUUSDM',
    label: 'GOLD',
    accent: 'text-amber-400',
    accentDim: 'text-amber-400/90',
    accentBg: 'bg-amber-500/20',
    accentSolid: 'bg-amber-500',
    accentBorder: 'border-amber-500/50',
    accentHover: 'hover:text-amber-400',
    hex: '#f59e0b',
  },
  forex: {
    symbol: 'EURUSD',
    label: 'FOREX',
    accent: 'text-blue-400',
    accentDim: 'text-blue-400/90',
    accentBg: 'bg-blue-500/20',
    accentSolid: 'bg-blue-500',
    accentBorder: 'border-blue-500/50',
    accentHover: 'hover:text-blue-400',
    hex: '#3b82f6',
  },
} as const

export type BotMeta = (typeof BOT_META)[BotId]
