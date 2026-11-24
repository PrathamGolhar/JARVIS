import React, { useState, useEffect } from 'react';

export interface ToastMessage {
  id: string;
  title: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'cyber';
  duration?: number;
  timestamp: Date;
}

// Global event bus for triggering toasts from anywhere
type ToastListener = (toast: Omit<ToastMessage, 'id' | 'timestamp'>) => void;
const listeners: Set<ToastListener> = new Set();

export const showToast = (toast: Omit<ToastMessage, 'id' | 'timestamp'>) => {
  listeners.forEach((listener) => listener(toast));
};

export const ToastNotificationSystem: React.FC = () => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => {
    const handleNewToast: ToastListener = (toast) => {
      const newToast: ToastMessage = {
        ...toast,
        id: Math.random().toString(36).substring(2, 9),
        timestamp: new Date(),
        duration: toast.duration ?? 4500,
      };

      setToasts((prev) => [...prev, newToast]);

      if (newToast.duration && newToast.duration > 0) {
        setTimeout(() => {
          setToasts((prev) => prev.filter((t) => t.id !== newToast.id));
        }, newToast.duration);
      }
    };

    listeners.add(handleNewToast);
    return () => {
      listeners.delete(handleNewToast);
    };
  }, []);

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-6 right-6 z-50 flex flex-col space-y-2.5 max-w-sm w-full pointer-events-none"
      aria-live="polite"
    >
      {toasts.map((toast) => {
        const typeStyles = {
          info: {
            border: 'border-cyan-500/50',
            bg: 'bg-slate-950/90',
            glow: 'shadow-cyan-500/20',
            iconColor: 'text-cyan-400',
            icon: (
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 16v-4" />
                <path d="M12 8h.01" />
              </svg>
            ),
          },
          success: {
            border: 'border-emerald-500/50',
            bg: 'bg-slate-950/90',
            glow: 'shadow-emerald-500/20',
            iconColor: 'text-emerald-400',
            icon: (
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 6 9 17l-5-5" />
              </svg>
            ),
          },
          warning: {
            border: 'border-amber-500/50',
            bg: 'bg-slate-950/90',
            glow: 'shadow-amber-500/20',
            iconColor: 'text-amber-400',
            icon: (
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            ),
          },
          error: {
            border: 'border-rose-500/50',
            bg: 'bg-slate-950/90',
            glow: 'shadow-rose-500/20',
            iconColor: 'text-rose-400',
            icon: (
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
              </svg>
            ),
          },
          cyber: {
            border: 'border-cyan-400',
            bg: 'bg-slate-900/95',
            glow: 'shadow-cyan-400/30',
            iconColor: 'text-cyan-300',
            icon: (
              <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <circle cx="12" cy="12" r="4" />
              </svg>
            ),
          },
        }[toast.type];

        return (
          <div
            key={toast.id}
            className={`pointer-events-auto backdrop-blur-xl ${typeStyles.bg} border ${typeStyles.border} shadow-lg ${typeStyles.glow} rounded-xl p-3.5 transition-all duration-300 transform translate-y-0 opacity-100 flex items-start space-x-3`}
          >
            <div className={`mt-0.5 shrink-0 ${typeStyles.iconColor}`}>{typeStyles.icon}</div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-slate-100 uppercase tracking-wider font-mono">{toast.title}</h4>
                <button
                  onClick={() => removeToast(toast.id)}
                  className="text-slate-500 hover:text-slate-300 transition-colors p-0.5 rounded cursor-pointer"
                  title="Dismiss notification"
                >
                  <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
              <p className="text-[11px] text-slate-300 mt-1 leading-relaxed">{toast.message}</p>
              <span className="text-[9px] text-slate-500 font-mono mt-1 block">
                {toast.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
};
