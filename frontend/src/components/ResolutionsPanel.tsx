import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store';

function getResClass(res: string) {
  const r = res.toLowerCase();
  if (r.includes('treaty')) return 'border-l-green-500 bg-green-950/30 text-green-200';
  if (r.includes('sanction')) return 'border-l-red-500 bg-red-950/30 text-red-200';
  if (r.includes('trade') || r.includes('aid')) return 'border-l-blue-500 bg-blue-950/30 text-blue-200';
  if (r.includes('mobilize') || r.includes('military')) return 'border-l-purple-500 bg-purple-950/30 text-purple-200';
  if (r.includes('covert') || r.includes('cyber') || r.includes('exposed')) return 'border-l-slate-400 bg-slate-800/30 text-slate-300';
  return 'border-l-zinc-500 bg-zinc-800/30 text-zinc-300';
}

export function ResolutionsPanel() {
  const { currentReplay, currentTurn } = useStore();
  if (!currentReplay) return null;
  const turnData = currentReplay.turns[currentTurn - 1];
  if (!turnData) return null;

  return (
    <div className="space-y-1">
      <h3 className="text-accent-cyan text-[11px] font-semibold uppercase tracking-widest mb-2">
        Resolutions
      </h3>
      <AnimatePresence mode="popLayout">
        {turnData.resolutions.map((res, i) => (
          <motion.div
            key={`${currentTurn}-res-${i}`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ delay: i * 0.04, duration: 0.2 }}
            className={`border-l-[3px] rounded-r-md px-3 py-1.5 font-mono text-[11px] leading-snug ${getResClass(res)}`}
          >
            {res}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
