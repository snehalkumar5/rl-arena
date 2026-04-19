import { useEffect, useState } from 'react';
import { useStore } from '../store';

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const { currentReplay, setTurn, setSelectedActor, setActiveView } = useStore();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setOpen(o => !o);
        setQuery('');
      }
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  if (!open) return null;

  const actors = currentReplay?.world.actors ?? [];
  const turns = currentReplay?.turns ?? [];

  type Cmd = { label: string; action: () => void; category: string };
  const commands: Cmd[] = [
    { label: 'View: Replay', action: () => { setActiveView('replay'); setOpen(false); }, category: 'Navigation' },
    { label: 'View: Backtest', action: () => { setActiveView('backtest'); setOpen(false); }, category: 'Navigation' },
    ...actors.map(a => ({
      label: `Actor: ${a.name}`,
      action: () => { setSelectedActor(a.actor_id); setOpen(false); },
      category: 'Actors',
    })),
    ...turns.map((_, i) => ({
      label: `Go to Turn ${i + 1}`,
      action: () => { setTurn(i + 1); setOpen(false); },
      category: 'Turns',
    })),
  ];

  const filtered = query
    ? commands.filter(c => c.label.toLowerCase().includes(query.toLowerCase()))
    : commands;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]" onClick={() => setOpen(false)}>
      <div className="absolute inset-0 bg-black/60" />
      <div
        className="relative w-[480px] bg-bg-card border border-border-subtle rounded-lg shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <input
          autoFocus
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Type a command..."
          className="w-full bg-transparent px-4 py-3 text-sm text-text-primary placeholder-text-muted border-b border-border-subtle focus:outline-none"
        />
        <div className="max-h-64 overflow-y-auto py-1">
          {filtered.length === 0 && (
            <div className="px-4 py-3 text-xs text-text-muted">No results</div>
          )}
          {filtered.map((cmd, i) => (
            <button
              key={i}
              onClick={cmd.action}
              className="w-full text-left px-4 py-2 text-xs hover:bg-bg-elevated text-text-primary flex justify-between"
            >
              <span>{cmd.label}</span>
              <span className="text-text-muted">{cmd.category}</span>
            </button>
          ))}
        </div>
        <div className="px-4 py-2 border-t border-border-subtle text-[10px] text-text-muted">
          ↑↓ Navigate · Enter Select · Esc Close
        </div>
      </div>
    </div>
  );
}
