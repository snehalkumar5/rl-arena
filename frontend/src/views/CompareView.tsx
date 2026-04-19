import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { useStore } from '../store';
import { getActorColor } from '../types';

// Since comparison data doesn't always carry the actor ordering,
// we hash the actor_id to a stable index into the color palette.
function colorForActor(actorId: string): string {
  let h = 0;
  for (let i = 0; i < actorId.length; i++) {
    h = (h * 31 + actorId.charCodeAt(i)) >>> 0;
  }
  return getActorColor(h % 10);
}

export default function CompareView() {
  const { runs, selectedRunIds, comparison, fetchRuns, fetchComparison, toggleRunForComparison } = useStore();

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  useEffect(() => {
    if (selectedRunIds.length === 2) {
      fetchComparison(selectedRunIds);
    }
  }, [selectedRunIds, fetchComparison]);

  return (
    <div className="space-y-6 p-4">
      <h2 className="text-xl font-bold text-slate-100">Run Comparison</h2>

      {/* Run selector */}
      <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-300">Select 2 runs to compare:</h3>
        {runs.length === 0 ? (
          <p className="text-sm text-slate-500">No runs found. Run a simulation first.</p>
        ) : (
          <div className="max-h-60 overflow-y-auto space-y-1">
            {runs.map(run => (
              <label
                key={run.run_id}
                className={`flex cursor-pointer items-center gap-3 rounded px-3 py-2 text-sm transition-colors ${
                  selectedRunIds.includes(run.run_id)
                    ? 'bg-cyan-900/30 border border-cyan-700'
                    : 'hover:bg-slate-700/50 border border-transparent'
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedRunIds.includes(run.run_id)}
                  onChange={() => toggleRunForComparison(run.run_id)}
                  disabled={!selectedRunIds.includes(run.run_id) && selectedRunIds.length >= 2}
                  className="accent-cyan-500"
                />
                <span className="font-mono text-xs text-slate-400">{run.run_id}</span>
                <span className="text-slate-300">{run.scenario}</span>
                {run.model && (
                  <span className="rounded bg-slate-700 px-1.5 py-0.5 text-xs text-cyan-400">{run.model}</span>
                )}
                <span className="text-xs text-slate-500">seed={run.seed}</span>
                <span className="text-xs text-slate-500">{run.turns}t</span>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Comparison results */}
      {comparison && selectedRunIds.length === 2 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Config comparison */}
          <div className="grid grid-cols-2 gap-4">
            {selectedRunIds.map((rid, i) => {
              const cfg = comparison.configs[rid] ?? { model: null, agent_type: null, seed: null };
              return (
                <div key={rid} className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
                  <h4 className="mb-2 text-sm font-semibold text-slate-300">
                    Run {i === 0 ? 'A' : 'B'}
                  </h4>
                  <div className="space-y-1 text-xs text-slate-400">
                    <p>Model: <span className="text-cyan-400">{cfg.model || 'mock'}</span></p>
                    <p>Agent: {cfg.agent_type ?? '—'}</p>
                    <p>Seed: {cfg.seed ?? '—'}</p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Score diffs */}
          {comparison.score_diffs && (
            <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
              <h3 className="mb-3 text-sm font-semibold text-slate-300">Score Comparison</h3>
              <div className="space-y-2">
                {Object.entries(comparison.score_diffs).map(([actorId, diff]) => (
                  <div key={actorId} className="flex items-center gap-3 text-sm">
                    <div className="h-2 w-2 rounded-full" style={{ backgroundColor: colorForActor(actorId) }} />
                    <span className="w-24 text-slate-300">{actorId}</span>
                    <span className="w-16 text-right text-slate-400">{diff.run_a.toFixed(1)}</span>
                    <span className="text-slate-600">vs</span>
                    <span className="w-16 text-slate-400">{diff.run_b.toFixed(1)}</span>
                    <span
                      className={`w-16 text-right font-semibold ${
                        diff.delta > 0
                          ? 'text-emerald-400'
                          : diff.delta < 0
                            ? 'text-red-400'
                            : 'text-slate-500'
                      }`}
                    >
                      {diff.delta > 0 ? '+' : ''}
                      {diff.delta.toFixed(1)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action diffs */}
          {comparison.action_diffs && comparison.action_diffs.length > 0 && (
            <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
              <h3 className="mb-3 text-sm font-semibold text-slate-300">Action Divergences</h3>
              {comparison.action_diffs.map((td, i) => (
                <div key={i} className="mb-3 rounded border border-slate-700 bg-slate-900 p-3">
                  <p className="mb-2 text-xs font-semibold text-slate-400">Turn {td.turn}</p>
                  {Object.entries(td.diffs).map(([actorId, diff]) => (
                    <div key={actorId} className="mb-1 flex items-center gap-2 text-xs">
                      <span className="w-20 font-medium" style={{ color: colorForActor(actorId) }}>
                        {actorId}
                      </span>
                      <span className="rounded bg-slate-800 px-2 py-0.5 text-slate-300">{diff.run_a}</span>
                      <span className="text-slate-600">→</span>
                      <span className="rounded bg-slate-800 px-2 py-0.5 text-slate-300">{diff.run_b}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}

          {/* Trace stats comparison */}
          <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
            <h3 className="mb-3 text-sm font-semibold text-slate-300">Trace Statistics</h3>
            <div className="grid grid-cols-2 gap-4">
              {selectedRunIds.map((rid, i) => {
                const stats = comparison.trace_stats[rid] ?? {
                  total_traces: 0,
                  total_tokens: 0,
                  total_latency_ms: 0,
                  coercion_count: 0,
                };
                return (
                  <div key={rid} className="text-xs text-slate-400 space-y-1">
                    <p className="text-sm font-semibold text-slate-300">Run {i === 0 ? 'A' : 'B'}</p>
                    <p>API calls: <span className="text-slate-200">{stats.total_traces || 0}</span></p>
                    <p>
                      Total tokens:{' '}
                      <span className="text-slate-200">{(stats.total_tokens || 0).toLocaleString()}</span>
                    </p>
                    <p>
                      Total latency:{' '}
                      <span className="text-slate-200">{((stats.total_latency_ms || 0) / 1000).toFixed(1)}s</span>
                    </p>
                    <p>
                      Coercions:{' '}
                      <span className={stats.coercion_count > 0 ? 'text-red-400' : 'text-emerald-400'}>
                        {stats.coercion_count || 0}
                      </span>
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}
