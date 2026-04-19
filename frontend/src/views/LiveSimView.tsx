import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store';
import ActionFlowDiagram from '../components/ActionFlowDiagram';
import ReasoningPanel from '../components/ReasoningPanel';
import ScoreDeltaBar from '../components/ScoreDeltaBar';

export default function LiveSimView() {
  const {
    simulationJobId, simulationStatus, liveTurns, simulationError,
    startSimulation, fetchReplayList, loadReplay, setActiveView,
  } = useStore();

  const [scenario, setScenario] = useState('hormuz_crisis_apr8');
  const [model, setModel] = useState('qwen3.6-plus');
  const [agentType] = useState('llm');
  const [seed, setSeed] = useState(42);
  const [attachJobId, setAttachJobId] = useState('');

  const isRunning = simulationStatus === 'running' || simulationStatus === 'starting';

  // Attach to an existing running job — poll turns instead of SSE
  const attachToJob = async (jobId: string) => {
    useStore.setState({ simulationJobId: jobId, simulationStatus: 'running', liveTurns: [], simulationError: null });
    const poll = async () => {
      try {
        const res = await fetch(`/api/simulate/${jobId}/turns`);
        if (!res.ok) return;
        const data = await res.json();
        useStore.setState({ liveTurns: data.turns || [] });
        if (data.status === 'running') {
          setTimeout(poll, 3000);
        } else {
          useStore.setState({ simulationStatus: data.status });
          useStore.getState().fetchReplayList();
        }
      } catch { /* retry */ setTimeout(poll, 5000); }
    };
    poll();
  };

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-100">Live Simulation</h2>
        <p className="text-sm text-slate-400 mt-1">Run an LLM simulation and watch decisions unfold in real-time</p>
      </div>

      {/* Config panel */}
      <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4 grid grid-cols-4 gap-4">
        <div>
          <label className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold">Scenario</label>
          <select
            value={scenario}
            onChange={e => setScenario(e.target.value)}
            disabled={isRunning}
            className="w-full mt-1 bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 disabled:opacity-50"
          >
            <option value="hormuz_crisis_apr8">Strait of Hormuz Crisis</option>
            <option value="saffron_sea_crisis">Saffron Sea Crisis</option>
          </select>
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold">Model</label>
          <select
            value={model}
            onChange={e => setModel(e.target.value)}
            disabled={isRunning}
            className="w-full mt-1 bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 disabled:opacity-50"
          >
            <optgroup label="Paid (with credits)">
              <option value="qwen3.6-plus">qwen3.6-plus</option>
              <option value="qwen3.5-plus">qwen3.5-plus</option>
              <option value="minimax-m2.5">minimax-m2.5</option>
              <option value="glm-5.1">glm-5.1</option>
              <option value="kimi-k2.5">kimi-k2.5</option>
              <option value="claude-sonnet-4">claude-sonnet-4</option>
              <option value="claude-haiku-4-5">claude-haiku-4-5</option>
            </optgroup>
            <optgroup label="Free (rate limited)">
              <option value="big-pickle">big-pickle</option>
              <option value="gpt-5-nano">gpt-5-nano</option>
              <option value="nemotron-3-super-free">nemotron-3-super-free</option>
              <option value="minimax-m2.5-free">minimax-m2.5-free</option>
            </optgroup>
          </select>
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold">Seed</label>
          <input
            type="number"
            value={seed}
            onChange={e => setSeed(Number(e.target.value))}
            disabled={isRunning}
            className="w-full mt-1 bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 disabled:opacity-50"
          />
        </div>
        <div className="flex items-end">
          <button
            onClick={() => startSimulation(scenario, agentType, model, seed)}
            disabled={isRunning}
            className={`w-full px-4 py-1.5 rounded text-xs font-semibold tracking-wide transition-all ${
              isRunning
                ? 'bg-amber-900/30 text-amber-400 border border-amber-700 cursor-wait'
                : 'bg-cyan-900/40 text-cyan-400 border border-cyan-700 hover:bg-cyan-900/60 cursor-pointer'
            }`}
          >
            {isRunning ? `Running... (${liveTurns.length} turns)` : 'Run Simulation'}
          </button>
        </div>
      </div>

      {/* Attach to existing job */}
      {!isRunning && (
        <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-3 flex gap-3 items-center">
          <label className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold whitespace-nowrap">Attach to running job:</label>
          <input
            type="text"
            value={attachJobId}
            onChange={e => setAttachJobId(e.target.value)}
            placeholder="paste job_id (e.g. e4898220)"
            className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
          />
          <button
            onClick={() => { if (attachJobId.trim()) attachToJob(attachJobId.trim()); }}
            className="px-4 py-1.5 rounded bg-amber-900/30 text-amber-400 border border-amber-700 hover:bg-amber-900/50 text-xs font-semibold"
          >
            Attach
          </button>
        </div>
      )}

      {/* Error */}
      {simulationError && (
        <div className="rounded border border-red-800 bg-red-900/20 p-3 text-sm text-red-400">
          {simulationError}
        </div>
      )}

      {/* Status bar */}
      {simulationJobId && (
        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span className="font-mono bg-slate-800 px-2 py-0.5 rounded">{simulationJobId}</span>
          <span className={`px-2 py-0.5 rounded ${
            simulationStatus === 'running' ? 'bg-amber-900/30 text-amber-400' :
            simulationStatus === 'complete' ? 'bg-emerald-900/30 text-emerald-400' :
            simulationStatus === 'error' ? 'bg-red-900/30 text-red-400' :
            'bg-slate-800 text-slate-400'
          }`}>
            {simulationStatus}
          </span>
          {isRunning && (
            <div className="flex gap-1">
              {[1,2,3,4,5].map(t => (
                <div
                  key={t}
                  className={`w-8 h-1.5 rounded-full transition-colors ${
                    t <= liveTurns.length ? 'bg-cyan-500' : 'bg-slate-700'
                  }`}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Live turn feed */}
      <AnimatePresence>
        {liveTurns.map((turn, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="rounded-lg border border-slate-700 bg-slate-800/50"
          >
            {/* Turn header */}
            <div className="flex items-center justify-between p-4 pb-2">
              <h3 className="text-sm font-bold text-slate-200">Turn {turn.turn}</h3>
              <div className="flex gap-2">
                {turn.traces?.map((t: any, i: number) => (
                  <span key={i} className={`text-[10px] px-1.5 py-0.5 rounded ${
                    t.was_coerced ? 'bg-red-900/30 text-red-400' :
                    t.parse_success !== false ? 'bg-emerald-900/30 text-emerald-400' :
                    'bg-slate-700 text-slate-400'
                  }`}>
                    {t.actor_id}: {t.latency_ms?.toFixed(0) ?? '?'}ms
                  </span>
                ))}
              </div>
            </div>

            {/* News */}
            {turn.public_news?.length > 0 && (
              <div className="mx-4 mb-3 p-2 rounded bg-amber-900/10 border border-amber-800/30">
                {turn.public_news.map((news: string, i: number) => (
                  <p key={i} className="text-xs text-amber-300">{news}</p>
                ))}
              </div>
            )}

            {/* Action Flow Diagram */}
            <div className="px-4">
              <ActionFlowDiagram actions={turn.actions || []} />
            </div>

            {/* Reasoning panels for each action */}
            <div className="px-4 py-2 space-y-1">
              {turn.actions?.map((action: any, i: number) => {
                const trace = turn.traces?.find((t: any) => t.actor_id === (action.actor_id || action.actor));
                const resolution = turn.resolutions?.find((r: string) => 
                  r.toLowerCase().includes((action.actor_id || action.actor || '').toLowerCase())
                );
                // Attach public_statement from turn data if available
                const publicStatement = turn.public_statements?.[action.actor_id || action.actor];
                const enrichedAction = publicStatement
                  ? { ...action, public_statement: publicStatement }
                  : action;
                return (
                  <ReasoningPanel 
                    key={i} 
                    action={enrichedAction} 
                    trace={trace}
                    resolution={resolution}
                    actorIndex={i}
                  />
                );
              })}
            </div>

            {/* Score delta bars */}
            <div className="px-4 pb-4">
              <ScoreDeltaBar 
                scores={turn.scores || []} 
                prevScores={idx > 0 ? liveTurns[idx - 1]?.scores : undefined}
              />
            </div>
          </motion.div>
        ))}
      </AnimatePresence>

      {/* Completion — view full replay */}
      {simulationStatus === 'complete' && liveTurns.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="rounded-lg border border-emerald-800 bg-emerald-900/20 p-4 text-center space-y-3"
        >
          <p className="text-emerald-400 font-semibold">Simulation complete — {liveTurns.length} turns</p>
          <button
            onClick={async () => {
              // Refresh replay list then load the latest replay and switch to replay view
              await fetchReplayList();
              const list = useStore.getState().replayList;
              if (list.length > 0) {
                // Load the most recent replay (the one we just ran)
                await loadReplay(list[0].id);
                setActiveView('replay');
              }
            }}
            className="px-6 py-2 rounded bg-cyan-900/40 text-cyan-400 border border-cyan-700 hover:bg-cyan-900/60 text-sm font-semibold tracking-wide transition-all"
          >
            View Full Replay →
          </button>
          <p className="text-[10px] text-slate-500">
            Opens the full replay with map, charts, actions, diplomacy panels
          </p>
        </motion.div>
      )}
    </div>
  );
}
