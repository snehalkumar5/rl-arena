import { getActorColor } from '../types';

const ACTION_COLORS: Record<string, string> = {
  sanction: '#ef4444', mobilize: '#ef4444', raid: '#ef4444', sabotage: '#ef4444',
  trade_offer: '#22c55e', aid: '#22c55e', treaty_proposal: '#22c55e', ceasefire_offer: '#22c55e',
  proxy_support: '#a855f7', cyber_operation: '#a855f7', intel_share: '#a855f7', propaganda: '#a855f7',
  seek_sponsor: '#06b6d4', recruit: '#06b6d4',
  hold: '#64748b',
};

interface ReasoningPanelProps {
  action: {
    actor_id?: string;
    actor?: string;
    action_type: string;
    target?: string | null;
    target_name?: string | null;
    parameters?: Record<string, unknown>;
    rationale?: string;
    public_statement?: string;
  };
  trace?: {
    actor_id?: string;
    latency_ms?: number;
    prompt_tokens?: number | null;
    completion_tokens?: number | null;
    was_coerced?: boolean;
    coercion_reason?: string | null;
    parse_success?: boolean;
    parse_error?: string | null;
  } | null;
  resolution?: string | null;
  actorIndex?: number;
}

function getActionBadgeColor(actionType: string): string {
  return ACTION_COLORS[actionType] ?? '#64748b';
}

export default function ReasoningPanel({ action, trace, resolution, actorIndex = 0 }: ReasoningPanelProps) {
  const actorId = action.actor_id ?? action.actor ?? 'unknown';
  const actionType = action.action_type;
  const target = action.target_name ?? action.target;
  const badgeColor = getActionBadgeColor(actionType);
  const actorColor = getActorColor(actorIndex);

  // Trace stats
  const latency = trace?.latency_ms;
  const totalTokens = (trace?.prompt_tokens ?? 0) + (trace?.completion_tokens ?? 0);
  const wasCoerced = trace?.was_coerced ?? false;
  const parseSuccess = trace?.parse_success;

  // Parameters
  const params = action.parameters ?? {};
  const paramEntries = Object.entries(params);

  const hasContent = paramEntries.length > 0 || action.rationale || resolution || action.public_statement;

  return (
    <details className="group rounded bg-slate-900 border border-slate-700/60 text-xs">
      <summary className="flex items-center gap-2 px-3 py-2 cursor-pointer select-none hover:bg-slate-800/60 transition-colors list-none">
        {/* Expand indicator */}
        <span className="text-slate-500 text-[10px] group-open:rotate-90 transition-transform w-3">
          ▶
        </span>

        {/* Actor */}
        <span className="font-semibold" style={{ color: actorColor }}>
          {actorId}
        </span>

        {/* Action badge */}
        <span
          className="px-1.5 py-0.5 rounded text-[10px] font-bold"
          style={{
            backgroundColor: badgeColor + '20',
            color: badgeColor,
            border: `1px solid ${badgeColor}40`,
          }}
        >
          {actionType}
        </span>

        {/* Target */}
        {target && (
          <>
            <span className="text-slate-500">→</span>
            <span className="text-slate-300">{target}</span>
          </>
        )}

        {/* Spacer */}
        <span className="flex-1" />

        {/* Trace badges */}
        {wasCoerced && (
          <span className="text-[9px] px-1 py-0.5 rounded bg-red-900/30 text-red-400 border border-red-800/40">
            COERCED
          </span>
        )}
        {parseSuccess === false && (
          <span className="text-[9px] px-1 py-0.5 rounded bg-amber-900/30 text-amber-400 border border-amber-800/40">
            PARSE FAIL
          </span>
        )}
        <span className="text-[10px] text-slate-500 font-mono tabular-nums">
          {latency != null ? `${latency.toFixed(0)}ms` : ''}
          {totalTokens > 0 ? ` | ${totalTokens.toLocaleString()} tok` : ''}
        </span>
      </summary>

      {hasContent && (
        <div className="px-4 pb-3 pt-1 space-y-2 border-t border-slate-700/40">
          {/* Parameters */}
          {paramEntries.length > 0 && (
            <div>
              <div className="text-[9px] uppercase tracking-widest text-slate-500 font-semibold mb-1">
                Parameters
              </div>
              <div className="rounded bg-slate-800/80 border border-slate-700/50 px-3 py-2 font-mono text-[11px] text-slate-300 space-y-0.5">
                {paramEntries.map(([key, val]) => (
                  <div key={key}>
                    <span className="text-slate-500">{key}:</span>{' '}
                    <span className="text-slate-200">{String(val)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Reasoning / Rationale */}
          {action.rationale && (
            <div>
              <div className="text-[9px] uppercase tracking-widest text-slate-500 font-semibold mb-1">
                Reasoning
              </div>
              <div className="rounded bg-slate-800/80 border border-slate-700/50 px-3 py-2 text-[11px] text-slate-300 italic leading-relaxed">
                &ldquo;{action.rationale}&rdquo;
              </div>
            </div>
          )}

          {/* Public statement */}
          {action.public_statement && (
            <div>
              <div className="text-[9px] uppercase tracking-widest text-slate-500 font-semibold mb-1">
                Public Statement
              </div>
              <div className="rounded bg-cyan-900/10 border border-cyan-800/30 px-3 py-2 text-[11px] text-cyan-300 leading-relaxed">
                {action.public_statement}
              </div>
            </div>
          )}

          {/* Resolution */}
          {resolution && (
            <div>
              <div className="text-[9px] uppercase tracking-widest text-slate-500 font-semibold mb-1">
                Resolution
              </div>
              <div className="rounded bg-slate-800/80 border border-slate-700/50 px-3 py-2 text-[11px] text-emerald-400 font-mono">
                ✓ {resolution}
              </div>
            </div>
          )}

          {/* Coercion info */}
          {wasCoerced && trace?.coercion_reason && (
            <div>
              <div className="text-[9px] uppercase tracking-widest text-red-500 font-semibold mb-1">
                Coercion Reason
              </div>
              <div className="rounded bg-red-900/10 border border-red-800/30 px-3 py-2 text-[11px] text-red-400">
                {trace.coercion_reason}
              </div>
            </div>
          )}

          {/* Parse error */}
          {parseSuccess === false && trace?.parse_error && (
            <div>
              <div className="text-[9px] uppercase tracking-widest text-amber-500 font-semibold mb-1">
                Parse Error
              </div>
              <div className="rounded bg-amber-900/10 border border-amber-800/30 px-3 py-2 text-[11px] text-amber-400 font-mono">
                {trace.parse_error}
              </div>
            </div>
          )}
        </div>
      )}
    </details>
  );
}
