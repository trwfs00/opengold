import type { Metadata } from 'next'
import './globals.css'
import { I18nProvider } from '@/lib/i18n-context'
import { BotProvider } from '@/context/BotContext'

export const metadata: Metadata = {
  title: 'OpenGold Dashboard',
  description: 'Live trading monitor',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-gray-100 min-h-screen">
        <BotProvider>
          <I18nProvider>{children}</I18nProvider>
        </BotProvider>
      </body>
    </html>
  )
}
