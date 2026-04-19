import { useEffect } from 'react';
import { useStore } from '../store';
import { getActorColor } from '../types';

export function Sidebar() {
  const {
    replayList, currentReplay, activeView,
    loadReplay, setActiveView, loading,
  } = useStore();

  // Auto-load first replay
  useEffect(() => {
    if (replayList.length > 0 && !currentReplay && !loading) {
      loadReplay(replayList[0].id);
    }
  }, [replayList, currentReplay, loading, loadReplay]);

  const actors = currentReplay?.world.actors ?? [];

  return (
    <aside className="w-64 flex-shrink-0 bg-bg-secondary border-r border-border-subtle flex flex-col h-full overflow-hidden">
      {/* Logo */}
      <div className="p-4 border-b border-border-subtle">
        <h1 className="text-accent-cyan font-bold text-lg tracking-wider">WORLD ENGINE</h1>
        <p className="text-text-muted text-xs mt-0.5">Geopolitical Simulation Platform</p>
      </div>

      {/* Nav */}
      <div className="p-3 border-b border-border-subtle grid grid-cols-2 gap-1">
        <button
          onClick={() => setActiveView('replay')}
          className={`px-3 py-1.5 rounded text-xs font-semibold tracking-wide transition-colors ${
            activeView === 'replay'
              ? 'bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30'
              : 'text-text-secondary hover:text-text-primary hover:bg-bg-elevated'
          }`}
        >
          REPLAY
        </button>
        <button
          onClick={() => setActiveView('backtest')}
          className={`px-3 py-1.5 rounded text-xs font-semibold tracking-wide transition-colors ${
            activeView === 'backtest'
              ? 'bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30'
              : 'text-text-secondary hover:text-text-primary hover:bg-bg-elevated'
          }`}
        >
          BACKTEST
        </button>
        <button
          onClick={() => setActiveView('runs')}
          className={`px-3 py-1.5 rounded text-xs font-semibold tracking-wide transition-colors ${
            activeView === 'runs'
              ? 'bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30'
              : 'text-text-secondary hover:text-text-primary hover:bg-bg-elevated'
          }`}
        >
          RUNS
        </button>
        <button
          onClick={() => setActiveView('compare')}
          className={`px-3 py-1.5 rounded text-xs font-semibold tracking-wide transition-colors ${
            activeView === 'compare'
              ? 'bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30'
              : 'text-text-secondary hover:text-text-primary hover:bg-bg-elevated'
          }`}
        >
          COMPARE
        </button>
      </div>

      {/* Replay selector */}
      <div className="p-3 border-b border-border-subtle">
        <label className="text-text-muted text-[10px] uppercase tracking-widest font-semibold">Scenario</label>
        <select
          className="w-full mt-1 bg-bg-elevated border border-border-subtle rounded px-2 py-1.5 text-xs text-text-primary focus:outline-none focus:border-accent-cyan"
          value={currentReplay?.world.world_id ?? ''}
          onChange={(e) => {
            const r = replayList.find(r => r.world_id === e.target.value);
            if (r) loadReplay(r.id);
          }}
        >
          {replayList.map(r => (
            <option key={r.id} value={r.world_id}>{r.name}</option>
          ))}
        </select>
      </div>

      {/* Actor list */}
      <div className="flex-1 overflow-y-auto p-3">
        <label className="text-text-muted text-[10px] uppercase tracking-widest font-semibold">Actors</label>
        <div className="mt-2 space-y-1">
          {actors.map((actor, i) => (
            <button
              key={actor.actor_id}
              onClick={() => useStore.getState().setSelectedActor(actor.actor_id)}
              className="w-full text-left px-2 py-1.5 rounded transition-colors hover:bg-bg-elevated group"
              style={{ borderLeft: `3px solid ${getActorColor(i)}` }}
            >
              <div className="text-xs font-semibold" style={{ color: getActorColor(i) }}>
                {actor.name}
              </div>
              <div className="text-[10px] text-text-muted">
                {actor.actor_type === 'state' ? '● State' : '◆ Non-State'} · {actor.archetype.replace(/_/g, ' ')}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Info footer */}
      {currentReplay && (
        <div className="p-3 border-t border-border-subtle text-[10px] text-text-muted space-y-0.5">
          <div><span className="text-text-secondary">Regions:</span> {currentReplay.world.regions.length}</div>
          <div><span className="text-text-secondary">Turns:</span> {currentReplay.world.turn_limit}</div>
          <div><span className="text-text-secondary">Agent:</span> {currentReplay.metadata.agent_type}</div>
        </div>
      )}
    </aside>
  );
}
