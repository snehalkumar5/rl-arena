import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart, Bar, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line,
} from 'recharts';
import { useStore } from '../store';

export function BacktestView() {
  const { backtestReport, variants } = useStore();
  const [expandedTurn, setExpandedTurn] = useState<number | null>(null);

  if (!backtestReport) {
    return (
      <div className="flex-1 flex items-center justify-center flex-col gap-3 p-8">
        <div className="text-text-muted text-sm">No backtest report available.</div>
        <div className="text-text-muted text-xs">Run: python -m app.backtest</div>
      </div>
    );
  }

  const report = backtestReport;
  const acc = report.overall_accuracy;
  const correct = report.correct_predictions.length;
  const diverge = report.divergences.length;
  const total = correct + diverge;

  // Per-actor data
  const actorData = useMemo(() =>
    Object.entries(report.actor_accuracy)
      .sort(([, a], [, b]) => b - a)
      .map(([name, value]) => ({
        name,
        accuracy: Number((value * 100).toFixed(1)),
        fill: value >= 0.4 ? '#00e676' : value >= 0.25 ? '#ffd740' : '#ff5252',
      })),
    [report.actor_accuracy]
  );

  // Turn accuracy data
  const turnData = useMemo(() =>
    report.turn_comparisons.map(tc => ({
      label: tc.label,
      accuracy: Number((tc.turn_accuracy * 100).toFixed(1)),
    })),
    [report.turn_comparisons]
  );

  // Variant data
  const variantData = useMemo(() =>
    variants.map(v => ({
      variant: v.variant,
      accuracy: Number((v.accuracy_vs_reality * 100).toFixed(1)),
      fill: v.variant === 'baseline' ? '#00d2ff' : '#b388ff',
    })),
    [variants]
  );

  return (
    <div className="p-4 space-y-6">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-2xl font-bold text-accent-cyan">Hormuz Crisis — Backtest Analysis</h1>
        <p className="text-text-muted text-xs mt-1">
          DISCLAIMER: Simulation outputs are speculative. Not an intelligence product.
        </p>
      </div>

      {/* Top metrics */}
      <div className="grid grid-cols-3 gap-4">
        {/* Accuracy gauge */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="glass-panel p-6 flex flex-col items-center justify-center"
        >
          <div className="text-[10px] text-accent-cyan font-semibold uppercase tracking-widest mb-2">Overall Accuracy</div>
          <div className="relative w-32 h-32">
            <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
              <circle cx="50" cy="50" r="42" fill="none" stroke="#1e2d3d" strokeWidth="8" />
              <motion.circle
                cx="50" cy="50" r="42" fill="none"
                stroke={acc >= 0.5 ? '#00e676' : acc >= 0.3 ? '#ffd740' : '#ff5252'}
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={`${acc * 264} ${264 - acc * 264}`}
                initial={{ strokeDasharray: '0 264' }}
                animate={{ strokeDasharray: `${acc * 264} ${264 - acc * 264}` }}
                transition={{ duration: 1.2, ease: 'easeOut' }}
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-2xl font-bold text-text-primary">{(acc * 100).toFixed(1)}%</span>
            </div>
          </div>
        </motion.div>

        {/* Predictions */}
        <div className="space-y-3">
          <div className="glass-panel px-4 py-3">
            <div className="text-[10px] text-accent-cyan font-semibold uppercase tracking-widest">Predictions</div>
            <div className="text-xl font-bold text-text-primary mt-1">{correct} / {total}</div>
            <div className="text-[11px] text-accent-green">exact matches across all turns</div>
          </div>
          <div className="glass-panel px-4 py-3">
            <div className="text-[10px] text-accent-cyan font-semibold uppercase tracking-widest">Divergences</div>
            <div className="text-xl font-bold text-text-primary mt-1">{diverge}</div>
            <div className="text-[11px] text-accent-red">missed predictions</div>
          </div>
        </div>

        {/* Info */}
        <div className="space-y-3">
          <div className="glass-panel px-4 py-3">
            <div className="text-[10px] text-accent-cyan font-semibold uppercase tracking-widest">Baseline Date</div>
            <div className="text-xl font-bold text-text-primary mt-1">{report.baseline_date}</div>
            <div className="text-[11px] text-text-secondary">Agent: {report.agent_type}</div>
          </div>
          <div className="glass-panel px-4 py-3">
            <div className="text-[10px] text-accent-cyan font-semibold uppercase tracking-widest">Turns Simulated</div>
            <div className="text-xl font-bold text-text-primary mt-1">{report.turn_comparisons.length}</div>
            <div className="text-[11px] text-text-secondary">Apr 8 – Apr 19, 2026</div>
          </div>
        </div>
      </div>

      {/* Per-actor accuracy */}
      <div className="glass-panel p-4">
        <h3 className="text-accent-cyan text-[11px] font-semibold uppercase tracking-widest mb-3">
          Per-Actor Prediction Accuracy
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={actorData} layout="vertical">
            <XAxis type="number" domain={[0, 100]} stroke="#4a5568" fontSize={10} />
            <YAxis type="category" dataKey="name" stroke="#78909c" fontSize={10} width={120} />
            <Tooltip
              contentStyle={{ background: '#111827', border: '1px solid #1e2d3d', borderRadius: 6, fontSize: 11 }}
              formatter={(v) => `${v}%`}
            />
            <Bar dataKey="accuracy" radius={[0, 4, 4, 0]}>
              {actorData.map((d, i) => (
                <Cell key={i} fill={d.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Turn-by-turn accuracy line */}
      <div className="glass-panel p-4">
        <h3 className="text-accent-cyan text-[11px] font-semibold uppercase tracking-widest mb-3">
          Accuracy by Turn Phase
        </h3>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={turnData}>
            <XAxis dataKey="label" stroke="#4a5568" fontSize={9} angle={-10} textAnchor="end" height={50} />
            <YAxis domain={[0, 100]} stroke="#4a5568" fontSize={10} />
            <Tooltip
              contentStyle={{ background: '#111827', border: '1px solid #1e2d3d', borderRadius: 6, fontSize: 11 }}
              formatter={(v) => `${v}%`}
            />
            <Line type="monotone" dataKey="accuracy" stroke="#00d2ff" strokeWidth={3} dot={{ r: 5, fill: '#00d2ff' }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Turn detail grid */}
      <div className="glass-panel p-4">
        <h3 className="text-accent-cyan text-[11px] font-semibold uppercase tracking-widest mb-3">
          Turn-by-Turn Action Comparison
        </h3>
        <div className="space-y-2">
          {report.turn_comparisons.map(tc => (
            <div key={tc.turn} className="border border-border-subtle rounded-md overflow-hidden">
              <button
                onClick={() => setExpandedTurn(expandedTurn === tc.turn ? null : tc.turn)}
                className="w-full text-left px-4 py-2 bg-bg-elevated hover:bg-bg-card flex justify-between items-center transition-colors"
              >
                <span className="text-xs font-semibold text-text-primary">{tc.label}</span>
                <span className="text-xs font-mono text-accent-cyan">{(tc.turn_accuracy * 100).toFixed(0)}%</span>
              </button>
              {expandedTurn === tc.turn && (
                <div className="p-3 space-y-1 bg-bg-primary">
                  {tc.actor_matches.map((m, i) => {
                    const cls = m.match === 'EXACT'
                      ? 'border-l-green-500 bg-green-950/20 text-green-200'
                      : m.match === 'PARTIAL'
                        ? 'border-l-blue-500 bg-blue-950/20 text-blue-200'
                        : 'border-l-red-500 bg-red-950/20 text-red-200';
                    return (
                      <div key={i} className={`border-l-[3px] ${cls} rounded-r-md px-3 py-1.5 font-mono text-[11px]`}>
                        <span className="font-bold">[{m.match}]</span>{' '}
                        <span className="font-bold">{m.actor_id}</span> —{' '}
                        Sim: <code className="bg-black/30 px-1 rounded">{m.sim_action}</code>{' | '}
                        Real: <code className="bg-black/30 px-1 rounded">{m.real_action}</code>{' | '}
                        {(m.score * 100).toFixed(0)}%
                        <div className="text-text-muted text-[10px] mt-0.5">{m.real_description}</div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Variant comparison */}
      {variantData.length > 0 && (
        <div className="glass-panel p-4">
          <h3 className="text-accent-cyan text-[11px] font-semibold uppercase tracking-widest mb-3">
            Branching Scenario Variants
          </h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={variantData}>
              <XAxis dataKey="variant" stroke="#4a5568" fontSize={9} angle={-15} textAnchor="end" height={50} />
              <YAxis domain={[0, 100]} stroke="#4a5568" fontSize={10} />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #1e2d3d', borderRadius: 6, fontSize: 11 }}
                formatter={(v) => `${v}%`}
              />
              <Bar dataKey="accuracy" radius={[4, 4, 0, 0]}>
                {variantData.map((d, i) => (
                  <Cell key={i} fill={d.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="mt-3 space-y-1">
            {variants.map(v => {
              const top = v.final_leaderboard[0];
              return (
                <div key={v.variant} className="flex items-center gap-3 text-[11px] px-2 py-1 bg-bg-elevated rounded">
                  <span className="text-accent-cyan font-semibold w-36">{v.variant}</span>
                  <span className="text-text-secondary flex-1">{v.description}</span>
                  <span className="text-text-muted">{(v.accuracy_vs_reality * 100).toFixed(1)}%</span>
                  <span className="text-text-muted">Winner: {top?.name ?? 'N/A'}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Platform evaluation */}
      <div className="grid grid-cols-2 gap-4">
        <div className="glass-panel p-4 border-l-[3px] border-l-green-500">
          <h3 className="text-green-400 text-sm font-bold mb-3">STRENGTHS</h3>
          <ul className="space-y-2 text-xs text-text-secondary leading-relaxed">
            <li><b className="text-text-primary">Multi-actor complexity:</b> 8 actors (6 state + 2 non-state) with distinct doctrines and asymmetric info.</li>
            <li><b className="text-text-primary">Structured resolution:</b> Deterministic engine with legible, traceable causal chains.</li>
            <li><b className="text-text-primary">Branching scenarios:</b> Doctrine override system enables rapid counterfactual generation.</li>
            <li><b className="text-text-primary">Backtesting framework:</b> Ground truth comparison with per-actor/per-turn accuracy scoring.</li>
          </ul>
        </div>
        <div className="glass-panel p-4 border-l-[3px] border-l-red-500">
          <h3 className="text-red-400 text-sm font-bold mb-3">GAPS &amp; LIMITATIONS</h3>
          <ul className="space-y-2 text-xs text-text-secondary leading-relaxed">
            <li><b className="text-text-primary">Mock agent fidelity ({(acc * 100).toFixed(1)}%):</b> Rule-based agents miss context-dependent shifts.</li>
            <li><b className="text-text-primary">Single-action limit:</b> Real actors take multiple simultaneous actions per period.</li>
            <li><b className="text-text-primary">No escalation dynamics:</b> Engine lacks compounding tension mechanics.</li>
            <li><b className="text-text-primary">No economic feedback:</b> Oil price shocks, inflation not modeled.</li>
          </ul>
        </div>
      </div>

      <p className="text-center text-text-muted text-[10px] py-4">
        DISCLAIMER: Simulation outputs are speculative. Not an intelligence product.
      </p>
    </div>
  );
}
