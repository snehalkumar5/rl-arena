import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store';

export function NewsBulletin() {
  const { currentReplay, currentTurn } = useStore();
  if (!currentReplay) return null;

  const turnData = currentReplay.turns[currentTurn - 1];
  const news = turnData?.public_news ?? [];
  if (news.length === 0) return null;

  return (
    <div className="space-y-1">
      <h3 className="text-amber-400 text-[11px] font-semibold uppercase tracking-widest mb-2">
        Public Bulletin
      </h3>
      <AnimatePresence mode="popLayout">
        {news.map((item, i) => (
          <motion.div
            key={`${currentTurn}-news-${i}`}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0 }}
            transition={{ delay: i * 0.08 }}
            className="border-l-[3px] border-l-amber-500 bg-amber-950/20 rounded-r-md px-3 py-1.5 text-[12px] text-amber-100"
          >
            {item}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
