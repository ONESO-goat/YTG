import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { api, localSession } from '@/lib/api'

export const Route = createFileRoute('/guardian/waiting_for_connection')({
  component: RouteComponent,
})

function RouteComponent() {
  const [numberId, setNumberId] = useState(0)
  const [session, setSession] = useState<any>(null)
  const [copied, setCopied] = useState(false)
  const nav = useNavigate()

  useEffect(() => {
    const activeSession = localSession.get()
    if (!activeSession) {
      nav({ to: "/auth" })
      return
    }
    setSession(activeSession)
  }, [nav])

  useEffect(() => {
    if (!session?.user_id) return

    const interval = setInterval(async () => {
      try {
        const u: any = await api.getUser(session?.user_id)
        const connection: any = await api.getConnectionIfUserHasOne(u?.id)
        if (connection !== null) {
          nav({ to: "/guardian/dashboard" })
          return
        }
        setNumberId(u?.number_id)
      } catch (err) {
        console.error("Polling connection status error:", err)
      }
    }, 3000)

    return () => clearInterval(interval)
  }, [session, nav])

  const handleCopyId = () => {
    if (!numberId) return
    navigator.clipboard.writeText(String(numberId))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    // Assuming AppShell supports hiding sidebars via variant/props or custom layout wrapper

      <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-white p-6">
        <div className="max-w-md w-full bg-slate-800/60 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-8 shadow-2xl text-center space-y-6">
          
          {/* Animated Radar Pulse Loader */}
          <div className="relative flex items-center justify-center my-4">
            <div className="absolute w-24 h-24 bg-indigo-500/20 rounded-full animate-ping"></div>
            <div className="absolute w-36 h-36 bg-purple-500/10 rounded-full animate-pulse"></div>
            <div className="relative z-10 w-16 h-16 bg-gradient-to-tr from-indigo-600 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-500/30">
              <svg className="w-8 h-8 text-white animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
          </div>

          <div className="space-y-2">
            <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-white via-indigo-200 to-indigo-400 bg-clip-text text-transparent">
              Waiting for Connection
            </h1>
            <p className="text-sm text-slate-400">
              Share your unique ID with a trusted guardian member to connect.
            </p>
          </div>

          {/* ID Card Display Box */}
          <div className="bg-slate-900/80 border border-indigo-500/30 rounded-xl p-4 flex flex-col items-center space-y-3 shadow-inner">
            <span className="text-xs uppercase tracking-widest text-indigo-400 font-medium">Your Dependent ID</span>
            <div className="text-4xl font-mono font-black tracking-wider text-indigo-100">
              {numberId || "----"}
            </div>
            
            <button
              onClick={handleCopyId}
              disabled={!numberId}
              className="w-full mt-2 py-2 px-4 bg-indigo-600 hover:bg-indigo-500 active:scale-95 disabled:opacity-50 text-white text-sm font-semibold rounded-lg transition-all shadow-md shadow-indigo-600/20 flex items-center justify-center gap-2"
            >
              {copied ? (
                <>
                  <svg className="w-4 h-4 text-emerald-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" /></svg>
                  Copied to Clipboard!
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" /></svg>
                  Copy ID
                </>
              )}
            </button>
          </div>

          <div className="text-xs text-slate-500">
            This screen will automatically redirect once your guardian accepts connection.
          </div>

        </div>
      </div>

  )
}