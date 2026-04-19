import { getActorColor } from '../types';

interface ScoreEntry {
  actor_id: string;
  total?: number;
  final_score?: number;
  economy_score?: number;
  stability_score?: number;
  influence_score?: number;
  alliance_score?: number;
  objective_score?: number;
  war_cost?: number;
}

interface ScoreDeltaBarProps {
  scores: ScoreEntry[];
  prevScores?: Array<{
    actor_id: string;
    total?: number;
    final_score?: number;
  }>;
}

const DIMENSIONS: Array<{
  key: keyof ScoreEntry;
  label: string;
  color: string;
}> = [
  { key: 'economy_score',   label: 'Economy',   color: '#06b6d4' }, // cyan
  { key: 'stability_score', label: 'Stability', color: '#10b981' }, // emerald
  { key: 'influence_score', label: 'Influence', color: '#f59e0b' }, // amber
  { key: 'alliance_score',  label: 'Alliance',  color: '#3b82f6' }, // blue
  { key: 'objective_score', label: 'Objective', color: '#a855f7' }, // purple
  { key: 'war_cost',        label: 'War Cost',  color: '#ef4444' }, // red
];

// Known actor order for color assignment
const ACTOR_ORDER = ['iran', 'usa', 'israel', 'saudi', 'china', 'pakistan', 'houthis', 'shipping'];

function getTotal(score: ScoreEntry): number {
  return score.total ?? score.final_score ?? 0;
}

export default function ScoreDeltaBar({ scores, prevScores }: ScoreDeltaBarProps) {
  if (!scores || scores.length === 0) return null;

  // Sort by total descending
  const sorted = [...scores].sort((a, b) => getTotal(b) - getTotal(a));

  // Find max total for bar scaling
  const maxTotal = Math.max(...sorted.map(s => {
    const dims = DIMENSIONS.reduce((sum, d) => {
      const val = s[d.key] as number | undefined;
      return sum + Math.abs(val ?? 0);
    }, 0);
    return Math.max(dims, getTotal(s), 1);
  }));

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-3 mb-2 flex-wrap">
        {DIMENSIONS.map(d => (
          <span key={d.key} className="flex items-center gap-1 text-[9px] text-slate-500">
            <span
              className="inline-block w-2 h-2 rounded-sm"
              style={{ backgroundColor: d.color }}
            />
            {d.label}
          </span>
        ))}
      </div>

      {sorted.map((score) => {
        const actorId = score.actor_id;
        const total = getTotal(score);
        const actorIdx = ACTOR_ORDER.indexOf(actorId.toLowerCase());
        const actorColor = getActorColor(actorIdx >= 0 ? actorIdx : 0);

        // Delta from previous turn
        let delta: number | null = null;
        if (prevScores) {
          const prev = prevScores.find(p => p.actor_id === actorId);
          if (prev) {
            delta = total - (prev.total ?? prev.final_score ?? 0);
          }
        }

        // Calculate dimension percentages
        const segments = DIMENSIONS.map(d => {
          const val = score[d.key] as number | undefined;
          return {
            ...d,
            value: val ?? 0,
            absValue: Math.abs(val ?? 0),
          };
        });
        const totalAbsSegments = segments.reduce((s, seg) => s + seg.absValue, 0);

        return (
          <div key={actorId} className="flex items-center gap-2 text-xs">
            {/* Actor name */}
            <span
              className="w-16 text-right font-semibold truncate text-[11px]"
              style={{ color: actorColor }}
            >
              {actorId}
            </span>

            {/* Total + delta */}
            <span className="w-10 text-right font-mono text-slate-300 text-[11px]">
              {total.toFixed(1)}
            </span>
            <span className="w-12 text-right font-mono text-[10px]">
              {delta !== null ? (
                <span className={delta >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                  {delta >= 0 ? '+' : ''}{delta.toFixed(1)}
                </span>
              ) : (
                <span className="text-slate-600">--</span>
              )}
            </span>

            {/* Stacked bar */}
            <div className="flex-1 h-3 bg-slate-900 rounded overflow-hidden flex">
              {segments.map((seg) => {
                if (seg.absValue === 0) return null;
                const widthPct = maxTotal > 0
                  ? (seg.absValue / maxTotal) * 100
                  : 0;
                return (
                  <div
                    key={seg.key}
                    title={`${seg.label}: ${seg.value.toFixed(1)}`}
                    className="h-full transition-all duration-300"
                    style={{
                      width: `${widthPct}%`,
                      backgroundColor: seg.color,
                      opacity: seg.key === 'war_cost' ? 0.7 : 0.85,
                    }}
                  />
                );
              })}
              {/* If no dimension data, show total as a single bar */}
              {totalAbsSegments === 0 && total > 0 && (
                <div
                  title={`Total: ${total.toFixed(1)}`}
                  className="h-full"
                  style={{
                    width: `${(total / maxTotal) * 100}%`,
                    backgroundColor: actorColor,
                    opacity: 0.6,
                  }}
                />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
