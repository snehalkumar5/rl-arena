import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store';
import { getActorColor } from '../types';
import { ActorRadarChart } from './ScoreCharts';

export function ActorDossier({ actorId }: { actorId: string }) {
  const [expanded, setExpanded] = useState(false);
  const { currentReplay, currentTurn } = useStore();
  if (!currentReplay) return null;

  const actors = currentReplay.world.actors;
  const actor = actors.find(a => a.actor_id === actorId);
  if (!actor) return null;

  const idx = actors.indexOf(actor);
  const color = getActorColor(idx);
  const turnData = currentReplay.turns[currentTurn - 1];
  const state = turnData?.state_snapshot?.[actorId];

  return (
    <div
      className="glass-panel overflow-hidden cursor-pointer"
      style={{ borderLeft: `3px solid ${color}` }}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="px-4 py-3 flex items-center justify-between">
        <div>
          <div className="text-sm font-bold" style={{ color }}>{actor.name}</div>
          <div className="text-[10px] text-text-muted">
            {actor.actor_type === 'state' ? '● State' : '◆ Non-State'} · {actor.archetype.replace(/_/g, ' ')}
          </div>
        </div>
        <span className="text-text-muted text-xs">{expanded ? '▲' : '▼'}</span>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4">
              {/* Radar */}
              <ActorRadarChart actorId={actorId} />

              {/* Stats */}
              {state && (
                <div className="grid grid-cols-3 gap-2 text-[10px] mt-2">
                  {[
                    ['Treasury', state.treasury],
                    ['Stability', state.domestic_stability],
                    ['Military', state.military_readiness],
                    ['Energy', state.energy],
                    ['Influence', state.influence],
                    ['Reputation', state.reputation],
                  ].map(([label, val]) => (
                    <div key={label as string} className="bg-bg-primary rounded px-2 py-1">
                      <div className="text-text-muted">{label as string}</div>
                      <div className="font-bold font-mono" style={{ color }}>{(val as number).toFixed(0)}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* Objectives */}
              {actor.visible_objectives.length > 0 && (
                <div className="mt-3 text-[10px] text-text-muted">
                  <span className="text-text-secondary font-semibold">Objectives: </span>
                  {actor.visible_objectives.join(', ')}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
