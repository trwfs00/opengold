'use client'
import { useEffect, useRef } from 'react'
import { CandleBar } from '@/lib/api'

interface Props {
  candles: CandleBar[]
}

export default function CandleChart({ candles }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const chartRef = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const seriesRef = useRef<any>(null)

  // Create chart on mount only
  useEffect(() => {
    if (!containerRef.current) return

    import('lightweight-charts').then(({ createChart, ColorType }) => {
      // Clean up if somehow called twice
      if (chartRef.current) {
        chartRef.current.remove()
      }

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
        rightPriceScale: {
          borderColor: '#27272a',
        },
        crosshair: {
          vertLine: { color: '#52525b', labelBackgroundColor: '#3f3f46' },
          horzLine: { color: '#52525b', labelBackgroundColor: '#3f3f46' },
        },
      })

      const series = chart.addCandlestickSeries({
        upColor: '#f59e0b',        // amber — gold trading theme
        downColor: '#ef4444',
        borderVisible: false,
        wickUpColor: '#f59e0b',
        wickDownColor: '#ef4444',
      })

      chartRef.current = chart
      seriesRef.current = series

      if (candles.length) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        series.setData(candles as any)
        chart.timeScale().fitContent()
      }
    })

    return () => {
      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
        seriesRef.current = null
      }
    }
  }, []) // mount only — intentional empty dep array

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
          XAUUSD · 1H
        </h2>
        {candles.length === 0 && (
          <span className="text-zinc-600 text-[10px] font-mono">No data</span>
        )}
      </div>
      <div ref={containerRef} />
    </section>
  )
}
