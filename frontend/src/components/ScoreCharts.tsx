import { useMemo } from 'react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
  BarChart, Bar, Cell, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from 'recharts';
import { useStore } from '../store';
import { getActorColor } from '../types';

export function ScoreProgressionChart() {
  const { currentReplay, currentTurn } = useStore();
  if (!currentReplay) return null;

  const actors = currentReplay.world.actors;

  const data = useMemo(() => {
    return currentReplay.turns.slice(0, currentTurn).map((turn) => {
      const row: Record<string, number | string> = { turn: `T${turn.turn}` };
      for (const score of turn.scores) {
        const actor = actors.find(a => a.actor_id === score.actor_id);
        if (actor) row[actor.name] = Number(score.total.toFixed(1));
      }
      return row;
    });
  }, [currentReplay, currentTurn, actors]);

  return (
    <div>
      <h3 className="text-accent-cyan text-[11px] font-semibold uppercase tracking-widest mb-3">
        Score Progression
      </h3>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data}>
          <XAxis dataKey="turn" stroke="#4a5568" fontSize={10} />
          <YAxis stroke="#4a5568" fontSize={10} />
          <Tooltip
            contentStyle={{ background: '#111827', border: '1px solid #1e2d3d', borderRadius: 6, fontSize: 11 }}
            labelStyle={{ color: '#00d2ff' }}
          />
          <Legend wrapperStyle={{ fontSize: 10 }} />
          {actors.map((actor, i) => (
            <Line
              key={actor.actor_id}
              type="monotone"
              dataKey={actor.name}
              stroke={getActorColor(i)}
              strokeWidth={2}
              dot={{ r: 3, fill: getActorColor(i) }}
              activeDot={{ r: 5 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function LeaderboardBar() {
  const { currentReplay } = useStore();
  if (!currentReplay || !currentReplay.final_scores.length) return null;

  const actors = currentReplay.world.actors;
  const data = currentReplay.final_scores.map(s => ({
    name: s.name,
    score: Number(s.final_score.toFixed(1)),
    fill: (() => {
      const idx = actors.findIndex(a => a.actor_id === s.actor_id);
      return getActorColor(idx >= 0 ? idx : 0);
    })(),
  }));

  return (
    <div>
      <h3 className="text-accent-cyan text-[11px] font-semibold uppercase tracking-widest mb-3">
        Final Leaderboard
      </h3>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} layout="vertical">
          <XAxis type="number" stroke="#4a5568" fontSize={10} />
          <YAxis type="category" dataKey="name" stroke="#78909c" fontSize={10} width={100} />
          <Tooltip
            contentStyle={{ background: '#111827', border: '1px solid #1e2d3d', borderRadius: 6, fontSize: 11 }}
          />
          <Bar dataKey="score" radius={[0, 4, 4, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ScoreBreakdownChart() {
  const { currentReplay, currentTurn } = useStore();
  if (!currentReplay) return null;

  const turnData = currentReplay.turns[currentTurn - 1];
  if (!turnData) return null;
  const actors = currentReplay.world.actors;

  const data = turnData.scores.map(s => {
    const actor = actors.find(a => a.actor_id === s.actor_id);
    return {
      name: actor?.name ?? s.actor_id,
      Economy: Number((s.economy_score * 0.2).toFixed(1)),
      Stability: Number((s.stability_score * 0.2).toFixed(1)),
      Influence: Number((s.influence_score * 0.2).toFixed(1)),
      Alliance: Number((s.alliance_score * 0.15).toFixed(1)),
      Objective: Number((s.objective_score * 0.2).toFixed(1)),
    };
  });

  return (
    <div>
      <h3 className="text-accent-cyan text-[11px] font-semibold uppercase tracking-widest mb-3">
        Score Breakdown
      </h3>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data}>
          <XAxis dataKey="name" stroke="#4a5568" fontSize={9} angle={-20} textAnchor="end" height={50} />
          <YAxis stroke="#4a5568" fontSize={10} />
          <Tooltip
            contentStyle={{ background: '#111827', border: '1px solid #1e2d3d', borderRadius: 6, fontSize: 11 }}
          />
          <Legend wrapperStyle={{ fontSize: 10 }} />
          <Bar dataKey="Economy" stackId="a" fill="#448aff" />
          <Bar dataKey="Stability" stackId="a" fill="#00e676" />
          <Bar dataKey="Influence" stackId="a" fill="#ffd740" />
          <Bar dataKey="Alliance" stackId="a" fill="#b388ff" />
          <Bar dataKey="Objective" stackId="a" fill="#ff5252" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ActorRadarChart({ actorId }: { actorId: string }) {
  const { currentReplay, currentTurn } = useStore();
  if (!currentReplay) return null;

  const turnData = currentReplay.turns[currentTurn - 1];
  const state = turnData?.state_snapshot?.[actorId];
  if (!state) return null;

  const actors = currentReplay.world.actors;
  const idx = actors.findIndex(a => a.actor_id === actorId);
  const color = getActorColor(idx >= 0 ? idx : 0);

  const data = [
    { stat: 'Treasury', value: Math.min(state.treasury / 1.5, 100) },
    { stat: 'Stability', value: state.domestic_stability },
    { stat: 'Military', value: state.military_readiness },
    { stat: 'Energy', value: state.energy },
    { stat: 'Food', value: state.food },
    { stat: 'Influence', value: state.influence },
    { stat: 'Reputation', value: state.reputation },
  ];

  return (
    <ResponsiveContainer width="100%" height={220}>
      <RadarChart data={data}>
        <PolarGrid stroke="#1e2d3d" />
        <PolarAngleAxis dataKey="stat" tick={{ fill: '#78909c', fontSize: 9 }} />
        <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
        <Radar dataKey="value" stroke={color} fill={color} fillOpacity={0.15} strokeWidth={2} />
      </RadarChart>
    </ResponsiveContainer>
  );
}
