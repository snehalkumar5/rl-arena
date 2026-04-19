import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store';
import { getActorColorById } from '../types';

const ACTION_STYLES: Record<string, { bg: string; border: string; label: string }> = {
  treaty_proposal: { bg: 'bg-green-950/50', border: 'border-l-green-500', label: 'TREATY' },
  sanction: { bg: 'bg-red-950/50', border: 'border-l-red-500', label: 'SANCTION' },
  trade_offer: { bg: 'bg-blue-950/50', border: 'border-l-blue-500', label: 'TRADE' },
  aid: { bg: 'bg-blue-950/50', border: 'border-l-blue-400', label: 'AID' },
  mobilize: { bg: 'bg-purple-950/50', border: 'border-l-purple-500', label: 'MOBILIZE' },
  cyber_operation: { bg: 'bg-slate-800/50', border: 'border-l-slate-400', label: 'CYBER' },
  intel_share: { bg: 'bg-slate-800/50', border: 'border-l-slate-400', label: 'INTEL' },
  proxy_support: { bg: 'bg-orange-950/50', border: 'border-l-orange-500', label: 'PROXY' },
  hold: { bg: 'bg-zinc-800/50', border: 'border-l-zinc-500', label: 'HOLD' },
  sabotage: { bg: 'bg-red-950/50', border: 'border-l-red-400', label: 'SABOTAGE' },
  raid: { bg: 'bg-red-950/50', border: 'border-l-red-400', label: 'RAID' },
  recruit: { bg: 'bg-orange-950/50', border: 'border-l-orange-400', label: 'RECRUIT' },
  propaganda: { bg: 'bg-amber-950/50', border: 'border-l-amber-400', label: 'PROPAGANDA' },
  seek_sponsor: { bg: 'bg-teal-950/50', border: 'border-l-teal-400', label: 'SEEK SPONSOR' },
  ceasefire_offer: { bg: 'bg-emerald-950/50', border: 'border-l-emerald-400', label: 'CEASEFIRE' },
};

const DEFAULT_STYLE = { bg: 'bg-zinc-800/50', border: 'border-l-zinc-500', label: 'ACTION' };

export function ActionsPanel() {
  const { currentReplay, currentTurn, currentTraces, selectTrace } = useStore();
  if (!currentReplay) return null;

  const turnData = currentReplay.turns[currentTurn - 1];
  if (!turnData) return null;

  const actors = currentReplay.world.actors;

  return (
    <div className="space-y-1">
      <h3 className="text-accent-cyan text-[11px] font-semibold uppercase tracking-widest mb-2">
        Actions
      </h3>
      <AnimatePresence mode="popLayout">
        {turnData.actions.map((action, i) => {
          const style = ACTION_STYLES[action.action_type] ?? DEFAULT_STYLE;
          const color = getActorColorById(action.actor_id, actors);
          return (
            <motion.div
              key={`${currentTurn}-${action.actor_id}-${i}`}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ delay: i * 0.06, duration: 0.25 }}
              className={`${style.bg} border-l-[3px] ${style.border} rounded-r-md px-3 py-2`}
            >
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-black/30 text-text-secondary">
                  {style.label}
                </span>
                <span className="text-xs font-semibold" style={{ color }}>{action.actor_name}</span>
                {action.target_name && (
                  <span className="text-text-muted text-xs">→ {action.target_name}</span>
                )}
              </div>
              {action.rationale && (
                <p className="text-text-muted text-[11px] mt-1 italic leading-tight">{action.rationale}</p>
              )}
              {/* Inspect trace button */}
              {(() => {
                const trace = currentTraces.find(
                  (t) => t.actor_id === action.actor_id && t.turn === currentTurn
                );
                return trace ? (
                  <button
                    onClick={(e) => { e.stopPropagation(); selectTrace(trace); }}
                    className="mt-2 text-xs text-cyan-400 hover:text-cyan-300 underline"
                  >
                    Inspect LLM Trace →
                  </button>
                ) : null;
              })()}
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
