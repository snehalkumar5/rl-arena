import { useStore } from '../store';
import { getActorColorById } from '../types';

export function DiplomacyPanel() {
  const { currentReplay, currentTurn } = useStore();
  if (!currentReplay) return null;

  const turnData = currentReplay.turns[currentTurn - 1];
  if (!turnData) return null;
  const actors = currentReplay.world.actors;

  const statements = Object.entries(turnData.public_statements).filter(([, v]) => v);
  const messages = turnData.messages;

  return (
    <div className="space-y-3">
      <h3 className="text-accent-cyan text-[11px] font-semibold uppercase tracking-widest">
        Diplomacy
      </h3>

      {/* Public statements */}
      {statements.length > 0 && (
        <div className="space-y-1">
          {statements.map(([actorId, text]) => {
            const name = actors.find(a => a.actor_id === actorId)?.name ?? actorId;
            const color = getActorColorById(actorId, actors);
            return (
              <div key={actorId} className="border-l-[3px] border-l-cyan-500 bg-cyan-950/20 rounded-r-md px-3 py-1.5">
                <span className="text-[11px] font-semibold" style={{ color }}>{name}:</span>
                <span className="text-[11px] text-cyan-200 ml-1">{text}</span>
              </div>
            );
          })}
        </div>
      )}

      {/* Private messages */}
      {messages.length > 0 && (
        <div>
          <div className="text-[10px] text-purple-400 font-semibold uppercase tracking-widest mb-1">
            Private Channels (Intercepted)
          </div>
          <div className="space-y-1">
            {messages.map((msg, i) => {
              const fromName = actors.find(a => a.actor_id === msg.from)?.name ?? msg.from;
              const toName = actors.find(a => a.actor_id === msg.to)?.name ?? msg.to;
              return (
                <div key={i} className="border-l-[3px] border-l-purple-500 bg-purple-950/20 rounded-r-md px-3 py-1.5">
                  <span className="text-[11px] text-purple-300">
                    <b>{fromName}</b> → <b>{toName}</b>: {msg.text}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {statements.length === 0 && messages.length === 0 && (
        <p className="text-text-muted text-xs italic">No diplomatic activity this turn.</p>
      )}
    </div>
  );
}
