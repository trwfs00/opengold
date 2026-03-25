'use client'
import { StatusData } from '@/lib/api'

interface Props {
  status: StatusData | null
  onKillSwitch: (active: boolean) => void
}

export default function StatusBar({ status, onKillSwitch }: Props) {
  if (!status) {
    return (
      <div className="h-9 bg-zinc-900 border-b border-zinc-800 animate-pulse" />
    )
  }

  const alive = status.bot_alive
  const ksActive = status.kill_switch_active

  return (
    <div className="flex items-center justify-between px-5 h-9 bg-zinc-900 border-b border-zinc-800 text-xs font-mono">
      <div className="flex items-center gap-5">
        <span className={`flex items-center gap-1.5 font-semibold tracking-wide ${alive ? 'text-amber-400' : 'text-red-400'}`}>
          <span className={`inline-block w-1.5 h-1.5 rounded-full ${alive ? 'bg-amber-400 animate-pulse' : 'bg-red-400'}`} />
          {alive ? 'BOT ALIVE' : 'BOT OFFLINE'}
        </span>
        {status.dry_run && (
          <span className="text-amber-500/70 border border-amber-500/30 px-1.5 py-0.5 rounded text-[10px] tracking-widest">
            DRY RUN
          </span>
        )}
      </div>
      <button
        onClick={() => onKillSwitch(!ksActive)}
        className={`px-3 py-1 rounded text-[11px] font-semibold tracking-wide transition-all ${
          ksActive
            ? 'bg-red-600 hover:bg-red-700 text-white ring-1 ring-red-500'
            : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700'
        }`}
      >
        {ksActive ? '⚠ KILL SWITCH ACTIVE — Click to Resume' : 'Kill Switch'}
      </button>
    </div>
  )
}
