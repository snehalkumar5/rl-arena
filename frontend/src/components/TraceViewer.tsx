import { motion, AnimatePresence } from 'framer-motion';
import type { ReactNode } from 'react';
import { useStore } from '../store';
import { getActorColorById } from '../types';

export default function TraceViewer() {
  const { selectedTrace, selectTrace, currentReplay } = useStore();

  if (!selectedTrace) return null;

  const t = selectedTrace;
  const totalTokens = (t.prompt_tokens || 0) + (t.completion_tokens || 0);
  const actors = currentReplay?.world.actors ?? [];
  const actorColor = getActorColorById(t.actor_id, actors);

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
        onClick={() => selectTrace(null)}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="relative max-h-[90vh] w-[900px] overflow-y-auto rounded-lg border border-slate-700 bg-slate-900 p-6 shadow-2xl"
          onClick={e => e.stopPropagation()}
        >
          {/* Header */}
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-3 w-3 rounded-full" style={{ backgroundColor: actorColor }} />
              <h2 className="text-lg font-semibold text-slate-100">
                LLM Trace: <span style={{ color: actorColor }}>{t.actor_id}</span> — Turn {t.turn}
              </h2>
            </div>
            <button
              onClick={() => selectTrace(null)}
              className="text-slate-400 hover:text-slate-200 text-xl"
            >×</button>
          </div>

          {/* Meta bar */}
          <div className="mb-4 flex flex-wrap gap-3 text-xs">
            <span className="rounded bg-slate-800 px-2 py-1 text-cyan-400">{t.model}</span>
            <span className="rounded bg-slate-800 px-2 py-1 text-slate-300">{t.provider}</span>
            <span className="rounded bg-slate-800 px-2 py-1 text-slate-300">temp={t.temperature}</span>
            <span className="rounded bg-slate-800 px-2 py-1 text-amber-400">{t.latency_ms.toFixed(0)}ms</span>
            <span className="rounded bg-slate-800 px-2 py-1 text-slate-300">{totalTokens} tokens</span>
            <span className="rounded bg-slate-800 px-2 py-1 text-slate-300">attempt {t.attempt_number}</span>
            {t.was_coerced && (
              <span className="rounded bg-red-900/50 px-2 py-1 text-red-400">COERCED: {t.coercion_reason}</span>
            )}
            {t.parse_success ? (
              <span className="rounded bg-emerald-900/50 px-2 py-1 text-emerald-400">Parse OK</span>
            ) : (
              <span className="rounded bg-red-900/50 px-2 py-1 text-red-400">Parse Failed</span>
            )}
          </div>

          {/* Collapsible sections */}
          <TraceSection title="System Prompt" tokens={t.prompt_tokens ? Math.floor(t.prompt_tokens * 0.3) : null}>
            <pre className="max-h-60 overflow-auto whitespace-pre-wrap font-mono text-xs text-slate-300">
              {t.system_prompt || '(empty)'}
            </pre>
          </TraceSection>

          <TraceSection title="User Prompt (Observation)" tokens={t.prompt_tokens ? Math.floor(t.prompt_tokens * 0.7) : null}>
            <pre className="max-h-80 overflow-auto whitespace-pre-wrap font-mono text-xs text-slate-300">
              {t.user_prompt || '(empty)'}
            </pre>
          </TraceSection>

          <TraceSection title="Raw LLM Completion" tokens={t.completion_tokens}>
            <pre className="max-h-80 overflow-auto whitespace-pre-wrap font-mono text-xs text-emerald-300">
              {t.raw_completion || '(empty)'}
            </pre>
          </TraceSection>

          {t.repair_attempted && (
            <TraceSection title="Repair Attempt" tokens={null}>
              <pre className="max-h-40 overflow-auto whitespace-pre-wrap font-mono text-xs text-amber-300">
                {t.repair_completion || '(no repair output)'}
              </pre>
            </TraceSection>
          )}

          <TraceSection title="Parsed Action" tokens={null}>
            {t.parsed_action ? (
              <div className="text-sm text-slate-300">
                <span className="text-cyan-400 font-semibold">{t.parsed_action.action_type}</span>
                {t.parsed_action.target && (
                  <span className="text-slate-400"> → {t.parsed_action.target}</span>
                )}
                {t.parsed_action.parameters && Object.keys(t.parsed_action.parameters).length > 0 && (
                  <pre className="mt-1 text-xs text-slate-400">
                    {JSON.stringify(t.parsed_action.parameters, null, 2)}
                  </pre>
                )}
              </div>
            ) : (
              <span className="text-red-400 text-sm">No action parsed</span>
            )}
          </TraceSection>

          {t.parse_error && (
            <div className="mt-3 rounded border border-red-800 bg-red-900/20 p-3">
              <span className="text-xs font-semibold text-red-400">Parse Error:</span>
              <pre className="mt-1 whitespace-pre-wrap font-mono text-xs text-red-300">{t.parse_error}</pre>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

function TraceSection({ title, tokens, children }: { title: string; tokens: number | null; children: ReactNode }) {
  return (
    <details className="group mb-3">
      <summary className="cursor-pointer rounded bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-750">
        <span>{title}</span>
        {tokens !== null && <span className="ml-2 text-xs text-slate-500">{tokens} tokens</span>}
      </summary>
      <div className="mt-1 rounded border border-slate-800 bg-slate-950 p-3">
        {children}
      </div>
    </details>
  );
}
