import { getActorColor } from '../types';

const ACTION_COLORS: Record<string, string> = {
  sanction: '#ef4444', mobilize: '#ef4444', raid: '#ef4444', sabotage: '#ef4444',
  trade_offer: '#22c55e', aid: '#22c55e', treaty_proposal: '#22c55e', ceasefire_offer: '#22c55e',
  proxy_support: '#a855f7', cyber_operation: '#a855f7', intel_share: '#a855f7', propaganda: '#a855f7',
  seek_sponsor: '#06b6d4', recruit: '#06b6d4',
  hold: '#64748b',
};

const ACTOR_POSITIONS: Record<string, { x: number; y: number }> = {
  iran:     { x: 200, y: 60 },
  usa:      { x: 500, y: 60 },
  israel:   { x: 650, y: 160 },
  saudi:    { x: 650, y: 280 },
  china:    { x: 50, y: 160 },
  pakistan:  { x: 50, y: 280 },
  houthis:  { x: 200, y: 340 },
  shipping: { x: 500, y: 340 },
};

const ACTOR_ORDER = ['iran', 'usa', 'israel', 'saudi', 'china', 'pakistan', 'houthis', 'shipping'];
const NODE_RADIUS = 28;

function getActionColor(actionType: string): string {
  return ACTION_COLORS[actionType] ?? '#64748b';
}

/** Normalize actor id to match position keys */
function normalizeId(id: string): string {
  const lower = id.toLowerCase().replace(/[\s_-]/g, '');
  if (lower.includes('houthi')) return 'houthis';
  if (lower.includes('shipping') || lower.includes('maritime')) return 'shipping';
  if (lower.includes('saudi')) return 'saudi';
  for (const key of ACTOR_ORDER) {
    if (lower.includes(key)) return key;
  }
  return lower;
}

interface ActionFlowDiagramProps {
  actions: Array<{
    actor_id?: string;
    actor?: string;
    action_type: string;
    target?: string | null;
    parameters?: Record<string, unknown>;
  }>;
}

export default function ActionFlowDiagram({ actions }: ActionFlowDiagramProps) {
  if (!actions || actions.length === 0) return null;

  // Collect unique actors referenced
  const referencedActors = new Set<string>();
  for (const a of actions) {
    const actorId = normalizeId(a.actor_id ?? a.actor ?? '');
    if (actorId) referencedActors.add(actorId);
    if (a.target) {
      const targetId = normalizeId(a.target);
      if (targetId) referencedActors.add(targetId);
    }
  }

  // Build positions — use predefined or auto-place unknowns
  const positions: Record<string, { x: number; y: number }> = {};
  let unknownIdx = 0;
  for (const id of referencedActors) {
    if (ACTOR_POSITIONS[id]) {
      positions[id] = ACTOR_POSITIONS[id];
    } else {
      // Place unknowns along bottom
      positions[id] = { x: 100 + unknownIdx * 120, y: 380 };
      unknownIdx++;
    }
  }

  // Track arrows to offset bidirectional ones
  const arrowPairs = new Set<string>();

  function getArrowPath(
    fromId: string,
    toId: string,
    _pairIndex: number,
  ): { path: string; labelX: number; labelY: number } {
    const from = positions[fromId];
    const to = positions[toId];
    if (!from || !to) return { path: '', labelX: 0, labelY: 0 };

    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;

    // Unit vector
    const ux = dx / dist;
    const uy = dy / dist;

    // Start and end points at circle edge
    const startX = from.x + ux * NODE_RADIUS;
    const startY = from.y + uy * NODE_RADIUS;
    const endX = to.x - ux * NODE_RADIUS;
    const endY = to.y - uy * NODE_RADIUS;

    // Perpendicular for curve offset
    const px = -uy;
    const py = ux;

    // Check if reverse arrow exists — use opposite curve
    const pairKey = `${fromId}->${toId}`;
    const reverseKey = `${toId}->${fromId}`;
    const hasBidirectional = arrowPairs.has(reverseKey);
    arrowPairs.add(pairKey);

    const curveOffset = hasBidirectional ? 25 : 12;
    const sign = hasBidirectional ? 1 : 1;

    const midX = (startX + endX) / 2 + px * curveOffset * sign;
    const midY = (startY + endY) / 2 + py * curveOffset * sign;

    const path = `M ${startX} ${startY} Q ${midX} ${midY} ${endX} ${endY}`;

    // Label at 50% of the bezier
    const labelX = 0.25 * startX + 0.5 * midX + 0.25 * endX;
    const labelY = 0.25 * startY + 0.5 * midY + 0.25 * endY;

    return { path, labelX, labelY };
  }

  return (
    <svg
      viewBox="0 0 700 400"
      width="100%"
      className="mb-2"
      style={{ maxHeight: 300 }}
    >
      <defs>
        {/* Arrowhead markers for each color */}
        {Object.entries(ACTION_COLORS).map(([key, color]) => (
          <marker
            key={key}
            id={`arrow-${key}`}
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill={color} />
          </marker>
        ))}
        {/* Fallback gray marker */}
        <marker
          id="arrow-default"
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b" />
        </marker>
      </defs>

      {/* Draw arrows */}
      {actions.map((action, i) => {
        const actorId = normalizeId(action.actor_id ?? action.actor ?? '');
        const actionType = action.action_type;
        const color = getActionColor(actionType);

        if (!action.target || actionType === 'hold') {
          // Hold — draw a pulsing dot at the actor position
          const pos = positions[actorId];
          if (!pos) return null;
          return (
            <g key={`hold-${i}`}>
              <circle
                cx={pos.x + NODE_RADIUS + 8}
                cy={pos.y - NODE_RADIUS + 4}
                r="4"
                fill={color}
                opacity={0.7}
              >
                <animate
                  attributeName="r"
                  values="3;6;3"
                  dur="1.5s"
                  repeatCount="indefinite"
                />
                <animate
                  attributeName="opacity"
                  values="0.7;0.3;0.7"
                  dur="1.5s"
                  repeatCount="indefinite"
                />
              </circle>
              <text
                x={pos.x + NODE_RADIUS + 16}
                y={pos.y - NODE_RADIUS + 8}
                fontSize="8"
                fill={color}
                fontFamily="monospace"
              >
                hold
              </text>
            </g>
          );
        }

        const targetId = normalizeId(action.target);
        if (!positions[actorId] || !positions[targetId]) return null;

        const { path, labelX, labelY } = getArrowPath(actorId, targetId, i);
        if (!path) return null;

        const markerId = ACTION_COLORS[actionType] ? `arrow-${actionType}` : 'arrow-default';

        return (
          <g key={`action-${i}`}>
            <path
              d={path}
              fill="none"
              stroke={color}
              strokeWidth="1.5"
              strokeOpacity={0.8}
              markerEnd={`url(#${markerId})`}
            />
            <rect
              x={labelX - 2}
              y={labelY - 8}
              width={actionType.length * 5.5 + 4}
              height={12}
              rx="2"
              fill="#0f172a"
              fillOpacity={0.85}
            />
            <text
              x={labelX}
              y={labelY + 1}
              fontSize="7.5"
              fill={color}
              fontFamily="monospace"
              fontWeight="bold"
            >
              {actionType}
            </text>
          </g>
        );
      })}

      {/* Draw actor nodes on top */}
      {Object.entries(positions).map(([id, pos]) => {
        const actorIdx = ACTOR_ORDER.indexOf(id);
        const color = getActorColor(actorIdx >= 0 ? actorIdx : 0);
        return (
          <g key={`node-${id}`}>
            <circle
              cx={pos.x}
              cy={pos.y}
              r={NODE_RADIUS}
              fill="#0f172a"
              stroke={color}
              strokeWidth="2"
            />
            <text
              x={pos.x}
              y={pos.y + 1}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize="10"
              fontWeight="bold"
              fill={color}
              fontFamily="sans-serif"
            >
              {id}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
