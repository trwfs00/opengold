'use client'
import { useBot, BotId } from '@/context/BotContext'

const TABS: { id: BotId; label: string }[] = [
  { id: 'gold',  label: 'GOLD' },
  { id: 'forex', label: 'FOREX' },
]

export default function BotTabSwitcher() {
  const { bot, setBot } = useBot()
  return (
    <div className="flex items-center gap-0.5 bg-zinc-800/60 rounded-full p-0.5">
      {TABS.map(tab => (
        <button
          key={tab.id}
          onClick={() => setBot(tab.id)}
          className={`px-3 py-0.5 rounded-full text-[10px] font-semibold tracking-widest transition-all ${
            bot === tab.id
              ? tab.id === 'gold'
                ? 'bg-amber-500 text-zinc-950'
                : 'bg-blue-500 text-zinc-950'
              : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}
