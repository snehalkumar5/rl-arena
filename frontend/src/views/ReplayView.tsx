import { useStore } from '../store';
import { WorldMap } from '../components/WorldMap';
import { MetricsBar } from '../components/MetricsBar';
import { NewsBulletin } from '../components/NewsBulletin';
import { ActionsPanel } from '../components/ActionsPanel';
import { ResolutionsPanel } from '../components/ResolutionsPanel';
import { ScoreProgressionChart, LeaderboardBar, ScoreBreakdownChart } from '../components/ScoreCharts';
import { DiplomacyPanel } from '../components/DiplomacyPanel';
import { ActorDossier } from '../components/ActorDossier';

export function ReplayView() {
  const { currentReplay, currentTurn, loading } = useStore();

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-accent-cyan text-sm animate-pulse">Loading simulation data...</div>
      </div>
    );
  }

  if (!currentReplay) {
    return (
      <div className="flex-1 flex items-center justify-center flex-col gap-3">
        <div className="text-text-muted text-sm">No replay loaded.</div>
        <div className="text-text-muted text-xs">Run a simulation or select a replay from the sidebar.</div>
      </div>
    );
  }

  const world = currentReplay.world;

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-2xl font-bold text-accent-cyan">{world.name}</h1>
        <p className="text-text-secondary text-xs mt-1">
          Turn {currentTurn} of {world.turn_limit} · {world.actors.length} Actors · {world.regions.length} Regions
        </p>
      </div>

      {/* Metrics bar */}
      <MetricsBar />

      {/* News */}
      <NewsBulletin />

      {/* Map row */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="glass-panel overflow-hidden" style={{ height: 440 }}>
          <WorldMap />
        </div>
        <div className="glass-panel p-4 overflow-y-auto" style={{ maxHeight: 440 }}>
          <DiplomacyPanel />
        </div>
      </div>

      {/* Actions + Resolutions */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="glass-panel p-4 max-h-[400px] overflow-y-auto">
          <ActionsPanel />
        </div>
        <div className="glass-panel p-4 max-h-[400px] overflow-y-auto">
          <ResolutionsPanel />
        </div>
      </div>

      {/* Score charts */}
      <div className="grid grid-cols-1 xl:grid-cols-5 gap-4">
        <div className="xl:col-span-3 glass-panel p-4">
          <ScoreProgressionChart />
        </div>
        <div className="xl:col-span-2 glass-panel p-4">
          <LeaderboardBar />
        </div>
      </div>

      {/* Score breakdown */}
      <div className="glass-panel p-4">
        <ScoreBreakdownChart />
      </div>

      {/* Actor dossiers */}
      <div>
        <h2 className="text-accent-cyan text-sm font-semibold uppercase tracking-widest mb-3">
          Actor Dossiers
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {world.actors.map(actor => (
            <ActorDossier key={actor.actor_id} actorId={actor.actor_id} />
          ))}
        </div>
      </div>

      {/* Disclaimer */}
      <p className="text-center text-text-muted text-[10px] py-4">
        DISCLAIMER: Simulation outputs are speculative. Not an intelligence product.
      </p>
    </div>
  );
}
