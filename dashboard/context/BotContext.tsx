'use client'
import { createContext, useContext, useState, ReactNode } from 'react'

export type BotId = 'gold' | 'forex'

interface BotContextValue {
  bot: BotId
  setBot: (bot: BotId) => void
}

const BotContext = createContext<BotContextValue>({
  bot: 'gold',
  setBot: () => {},
})

export function BotProvider({ children }: { children: ReactNode }) {
  const [bot, setBot] = useState<BotId>('gold')
  return (
    <BotContext.Provider value={{ bot, setBot }}>
      {children}
    </BotContext.Provider>
  )
}

export function useBot(): BotContextValue {
  return useContext(BotContext)
}
