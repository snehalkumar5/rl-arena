import { useEffect, useRef } from 'react';
import { useStore } from '../store';

export function TurnControls() {
  const {
    currentTurn, currentReplay, isPlaying, playSpeed,
    setTurn, nextTurn, prevTurn, togglePlay, setPlaySpeed,
  } = useStore();

  const maxTurn = currentReplay?.turns.length ?? 1;
  const turnData = currentReplay?.turns[currentTurn - 1];
  const events = currentReplay?.world.initial_events ?? [];
  const turnEvent = events.find(e => e.turn === currentTurn);

  // Auto-play timer
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => {
    if (isPlaying) {
      timerRef.current = setInterval(() => nextTurn(), playSpeed);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [isPlaying, playSpeed, nextTurn]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') nextTurn();
      else if (e.key === 'ArrowLeft') prevTurn();
      else if (e.key === ' ') { e.preventDefault(); togglePlay(); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [nextTurn, prevTurn, togglePlay]);

  return (
    <div className="h-14 bg-bg-secondary border-t border-border-subtle flex items-center gap-3 px-4 flex-shrink-0">
      {/* Prev */}
      <button
        onClick={prevTurn}
        disabled={currentTurn <= 1}
        className="w-8 h-8 rounded flex items-center justify-center text-text-secondary hover:text-accent-cyan hover:bg-bg-elevated disabled:opacity-30 transition-colors"
      >
        ◀
      </button>

      {/* Play/Pause */}
      <button
        onClick={togglePlay}
        className="w-8 h-8 rounded flex items-center justify-center text-accent-cyan hover:bg-accent-cyan/15 transition-colors text-lg"
      >
        {isPlaying ? '⏸' : '▶'}
      </button>

      {/* Next */}
      <button
        onClick={nextTurn}
        disabled={currentTurn >= maxTurn}
        className="w-8 h-8 rounded flex items-center justify-center text-text-secondary hover:text-accent-cyan hover:bg-bg-elevated disabled:opacity-30 transition-colors"
      >
        ▶
      </button>

      {/* Turn label */}
      <div className="flex-1 flex items-center gap-3">
        <span className="text-accent-cyan font-mono text-sm font-bold">
          T{currentTurn}/{maxTurn}
        </span>
        {turnEvent && (
          <span className="text-text-secondary text-xs truncate">
            {turnEvent.public_text.slice(0, 80)}
          </span>
        )}
        {!turnEvent && turnData?.public_news?.[0] && (
          <span className="text-text-secondary text-xs truncate">
            {turnData.public_news[0].slice(0, 80)}
          </span>
        )}
      </div>

      {/* Turn slider */}
      <input
        type="range"
        min={1}
        max={maxTurn}
        value={currentTurn}
        onChange={(e) => setTurn(Number(e.target.value))}
        className="w-40 accent-accent-cyan"
      />

      {/* Speed control */}
      <select
        value={playSpeed}
        onChange={(e) => setPlaySpeed(Number(e.target.value))}
        className="bg-bg-elevated border border-border-subtle rounded px-2 py-1 text-[10px] text-text-secondary focus:outline-none"
      >
        <option value={3000}>0.5x</option>
        <option value={2000}>1x</option>
        <option value={1000}>2x</option>
        <option value={500}>4x</option>
      </select>
    </div>
  );
}
