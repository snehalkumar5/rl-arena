import { motion } from 'framer-motion';
import { useStore } from '../store';

export function MetricsBar() {
  const { currentReplay, currentTurn } = useStore();
  if (!currentReplay) return null;

  const turnData = currentReplay.turns[currentTurn - 1];
  if (!turnData) return null;

  const actors = currentReplay.world.actors;

  // Compute metrics
  const topScore = turnData.scores.reduce((best, s) => s.total > best.total ? s : best, turnData.scores[0]);
  const leaderName = actors.find(a => a.actor_id === topScore?.actor_id)?.name ?? 'N/A';
  const totalActions = turnData.actions.length;
  const totalMessages = turnData.messages.length;
  const conflicts = turnData.resolutions.filter(r => {
    const l = r.toLowerCase();
    return l.includes('sabotage') || l.includes('raid') || l.includes('sanction') || l.includes('cyber') || l.includes('mobilize');
  }).length;
  const treaties = turnData.resolutions.filter(r => r.toLowerCase().includes('treaty') && !r.toLowerCase().includes('rejected')).length;

  const cards = [
    { label: 'CURRENT LEADER', value: leaderName, sub: `Score: ${topScore?.total?.toFixed(1) ?? '0'}`, color: '#00e676' },
    { label: 'ACTIONS', value: String(totalActions), sub: `${totalMessages} diplomatic msgs`, color: '#448aff' },
    { label: 'CONFLICTS', value: String(conflicts), sub: 'hostile resolutions', color: '#ff5252' },
    { label: 'TREATIES', value: String(treaties), sub: 'signed this turn', color: '#00e676' },
  ];

  return (
    <div className="grid grid-cols-4 gap-3">
      {cards.map((card, i) => (
        <motion.div
          key={card.label}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05 }}
          className="glass-panel px-4 py-3"
        >
          <div className="text-[10px] text-accent-cyan font-semibold uppercase tracking-widest">{card.label}</div>
          <div className="text-xl font-bold text-text-primary mt-1">{card.value}</div>
          <div className="text-[11px] mt-0.5" style={{ color: card.color }}>{card.sub}</div>
        </motion.div>
      ))}
    </div>
  );
}
