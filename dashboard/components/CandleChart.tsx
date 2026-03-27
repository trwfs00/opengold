'use client'
import { useEffect, useRef, useState, useCallback } from 'react'
import { fetchCandles, CandleBar } from '@/lib/api'
import { useBot } from '@/context/BotContext'
import { BOT_META } from '@/lib/bot-meta'

const RANGES = [
  { label: '30m', limit: 30 },
  { label: '1H',  limit: 60 },
  { label: '4H',  limit: 240 },
  { label: '1D',  limit: 1440 },
] as const

type RangeLabel = typeof RANGES[number]['label']

export default function CandleChart() {
  const containerRef = useRef<HTMLDivElement>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const chartRef = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const seriesRef = useRef<any>(null)
  const [range, setRange] = useState<RangeLabel>('4H')
  const [candles, setCandles] = useState<CandleBar[]>([])

  const { bot } = useBot()
  const meta = BOT_META[bot]

  const load = useCallback(async (lbl: RangeLabel) => {
    const limit = RANGES.find(r => r.label === lbl)!.limit
    try {
      const data = await fetchCandles(bot, limit)
      setCandles(data)
    } catch {
      // silently ignore fetch errors — chart keeps last data
    }
  }, [bot])

  // Reload when range changes + poll every 2s for real-time updates
  useEffect(() => { load(range) }, [range, load])
  useEffect(() => {
    const id = setInterval(() => load(range), 1000)
    return () => clearInterval(id)
  }, [range, load])

  // Create chart on mount only
  useEffect(() => {
    if (!containerRef.current) return

    import('lightweight-charts').then(({ createChart, ColorType }) => {
      if (chartRef.current) chartRef.current.remove()

      const chart = createChart(containerRef.current!, {
        layout: {
          background: { type: ColorType.Solid, color: '#18181b' },
          textColor: '#71717a',
        },
        grid: {
          vertLines: { color: '#27272a' },
          horzLines: { color: '#27272a' },
        },
        width: containerRef.current!.clientWidth,
        height: 320,
        timeScale: {
          timeVisible: true,
          secondsVisible: false,
          borderColor: '#27272a',
        },
        rightPriceScale: { borderColor: '#27272a' },
        crosshair: {
          vertLine: { color: '#52525b', labelBackgroundColor: '#3f3f46' },
          horzLine: { color: '#52525b', labelBackgroundColor: '#3f3f46' },
        },
      })

      const series = chart.addCandlestickSeries({
        upColor: meta.hex,
        downColor: '#ef4444',
        borderVisible: false,
        wickUpColor: meta.hex,
        wickDownColor: '#ef4444',
      })

      chartRef.current = chart
      seriesRef.current = series
    })

    return () => {
      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
        seriesRef.current = null
      }
    }
  }, [bot]) // recreate chart when bot changes (candle color)

  // Update data without recreating chart
  useEffect(() => {
    if (seriesRef.current && candles.length) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      seriesRef.current.setData(candles as any)
      chartRef.current?.timeScale().fitContent()
    }
  }, [candles])

  return (
    <section className="bg-zinc-900 border border-zinc-800 rounded">
      <div className="px-4 pt-3 pb-1 flex items-center justify-between">
        <h2 className="text-zinc-500 text-[10px] font-mono font-semibold uppercase tracking-widest">
          {meta.symbol} · {bot === 'forex' ? 'M5' : 'M1'}
        </h2>
        <div className="flex items-center gap-1">
          {candles.length === 0 && (
            <span className="text-zinc-600 text-[10px] font-mono mr-2">No data</span>
          )}
          <div className="flex items-center rounded overflow-hidden border border-zinc-800">
            {RANGES.map((r, i) => (
              <button
                key={r.label}
                onClick={() => setRange(r.label)}
                className={`px-2.5 py-0.5 text-[10px] font-mono font-semibold tracking-wide transition-colors ${
                  range === r.label
                    ? `${meta.accentBg} ${meta.accent}`
                    : 'text-zinc-600 hover:text-zinc-300'
                } ${i > 0 ? 'border-l border-zinc-800' : ''}`}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>
      </div>
      <div ref={containerRef} />
    </section>
  )
}
