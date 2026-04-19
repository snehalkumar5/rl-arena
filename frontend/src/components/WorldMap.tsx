import { useMemo } from 'react';
import { Map } from 'react-map-gl/maplibre';
import DeckGL from '@deck.gl/react';
import { ScatterplotLayer, ArcLayer, TextLayer } from '@deck.gl/layers';
import { useStore } from '../store';
import { REGION_COORDS, getActorColor } from '../types';
import type { Region, ActorState } from '../types';
import 'maplibre-gl/dist/maplibre-gl.css';

const INITIAL_VIEW = {
  longitude: 52,
  latitude: 26,
  zoom: 4.2,
  pitch: 20,
  bearing: 0,
};

const DARK_BASEMAP = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

interface RegionPoint {
  position: [number, number];
  region: Region;
  controller: string | null;
  colorIdx: number;
  isChokepoint: boolean;
}

interface RelationArc {
  source: [number, number];
  target: [number, number];
  sourceActor: string;
  targetActor: string;
  value: number;
}

export function WorldMap() {
  const { currentReplay, currentTurn } = useStore();
  if (!currentReplay) return <MapPlaceholder />;

  const world = currentReplay.world;
  const turnData = currentReplay.turns[currentTurn - 1];
  const actors = world.actors;
  const actorIndex = useMemo(() => {
    const m: Record<string, number> = {};
    actors.forEach((a, i) => m[a.actor_id] = i);
    return m;
  }, [actors]);

  // Region points
  const regionPoints: RegionPoint[] = useMemo(() => {
    return world.regions.map(r => {
      const controller = turnData?.state_snapshot
        ? Object.keys(turnData.state_snapshot).find(aid =>
            world.regions.find(reg => reg.region_id === r.region_id)?.controller === aid
          ) ?? r.controller
        : r.controller;
      return {
        position: REGION_COORDS[r.region_id] ?? [50, 25],
        region: r,
        controller,
        colorIdx: controller ? (actorIndex[controller] ?? -1) : -1,
        isChokepoint: r.resource_tags.includes('chokepoint'),
      };
    });
  }, [world.regions, turnData, actorIndex]);

  // Relations arcs
  const arcs: RelationArc[] = useMemo(() => {
    const result: RelationArc[] = [];
    const snapshot = turnData?.state_snapshot;
    if (!snapshot) return result;

    const seen = new Set<string>();
    for (const [aid, state] of Object.entries(snapshot)) {
      const typedState = state as ActorState;
      if (!typedState.relations) continue;
      const sourceRegion = world.regions.find(r => r.controller === aid);
      const sourcePos = sourceRegion ? REGION_COORDS[sourceRegion.region_id] : null;
      if (!sourcePos) continue;

      for (const [otherId, value] of Object.entries(typedState.relations)) {
        const key = [aid, otherId].sort().join('-');
        if (seen.has(key)) continue;
        seen.add(key);
        if (Math.abs(value) < 0.2) continue;

        const targetRegion = world.regions.find(r => r.controller === otherId);
        const targetPos = targetRegion ? REGION_COORDS[targetRegion.region_id] : null;
        if (!targetPos) continue;

        result.push({
          source: sourcePos,
          target: targetPos,
          sourceActor: aid,
          targetActor: otherId,
          value,
        });
      }
    }
    return result;
  }, [turnData, world.regions]);

  const layers = [
    // Relations arcs
    new ArcLayer({
      id: 'relations',
      data: arcs,
      getSourcePosition: (d: RelationArc) => d.source,
      getTargetPosition: (d: RelationArc) => d.target,
      getSourceColor: (d: RelationArc) => d.value > 0 ? [0, 230, 118, 140] : [255, 82, 82, 140],
      getTargetColor: (d: RelationArc) => d.value > 0 ? [0, 230, 118, 140] : [255, 82, 82, 140],
      getWidth: (d: RelationArc) => Math.abs(d.value) * 4 + 0.5,
      greatCircle: true,
      pickable: true,
    }),
    // Region scatter
    new ScatterplotLayer({
      id: 'regions',
      data: regionPoints,
      getPosition: (d: RegionPoint) => d.position,
      getFillColor: (d: RegionPoint) => {
        if (d.colorIdx < 0) return [80, 80, 80, 180];
        const hex = getActorColor(d.colorIdx);
        return hexToRgb(hex, 200);
      },
      getRadius: (d: RegionPoint) => d.isChokepoint ? 35000 : 22000,
      radiusUnits: 'meters' as const,
      stroked: true,
      getLineColor: [15, 52, 96, 255],
      getLineWidth: 2,
      lineWidthUnits: 'pixels' as const,
      pickable: true,
    }),
    // Region labels
    new TextLayer({
      id: 'region-labels',
      data: regionPoints,
      getPosition: (d: RegionPoint) => d.position,
      getText: (d: RegionPoint) => d.region.name,
      getSize: 12,
      getColor: [224, 224, 224, 220],
      getTextAnchor: 'middle' as const,
      getAlignmentBaseline: 'bottom' as const,
      getPixelOffset: [0, -20],
      fontFamily: 'Inter, sans-serif',
      fontWeight: 600,
      outlineWidth: 3,
      outlineColor: [6, 9, 15, 255],
    }),
  ];

  return (
    <div className="relative w-full h-full min-h-[400px]">
      <DeckGL
        initialViewState={INITIAL_VIEW}
        controller={true}
        layers={layers}
        getTooltip={({ object }: { object?: RegionPoint | RelationArc }) => {
          if (!object) return null;
          if ('region' in object) {
            const r = object as RegionPoint;
            const ctrlName = r.controller
              ? actors.find(a => a.actor_id === r.controller)?.name ?? 'Unknown'
              : 'Contested';
            return {
              html: `<div style="font-family:Inter;font-size:12px">
                <b>${r.region.name}</b><br/>
                Type: ${r.region.type}<br/>
                Controller: ${ctrlName}<br/>
                Stability: ${(r.region.stability * 100).toFixed(0)}%<br/>
                Tags: ${r.region.resource_tags.join(', ')}
              </div>`,
              style: { background: '#111827', color: '#e0e0e0', border: '1px solid #1e2d3d', borderRadius: '6px', padding: '8px' },
            };
          }
          if ('sourceActor' in object) {
            const a = object as RelationArc;
            const sName = actors.find(x => x.actor_id === a.sourceActor)?.name ?? a.sourceActor;
            const tName = actors.find(x => x.actor_id === a.targetActor)?.name ?? a.targetActor;
            return {
              html: `<div style="font-family:Inter;font-size:12px">
                <b>${sName} ↔ ${tName}</b><br/>
                Relation: ${a.value > 0 ? '+' : ''}${a.value.toFixed(2)}
              </div>`,
              style: { background: '#111827', color: '#e0e0e0', border: '1px solid #1e2d3d', borderRadius: '6px', padding: '8px' },
            };
          }
          return null;
        }}
      >
        <Map mapStyle={DARK_BASEMAP} />
      </DeckGL>
      {/* Legend */}
      <div className="absolute bottom-3 left-3 glass-panel px-3 py-2 text-[10px] space-y-1">
        <div className="text-text-muted font-semibold uppercase tracking-widest mb-1">Legend</div>
        {actors.map((a, i) => (
          <div key={a.actor_id} className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: getActorColor(i) }} />
            <span className="text-text-secondary">{a.name}</span>
          </div>
        ))}
        <div className="flex items-center gap-2 mt-1 pt-1 border-t border-border-subtle">
          <span className="w-4 h-0.5 bg-accent-green inline-block rounded" />
          <span className="text-text-muted">Ally</span>
          <span className="w-4 h-0.5 bg-accent-red inline-block rounded ml-2" />
          <span className="text-text-muted">Hostile</span>
        </div>
      </div>
    </div>
  );
}

function MapPlaceholder() {
  return (
    <div className="w-full h-full min-h-[400px] bg-bg-secondary flex items-center justify-center">
      <p className="text-text-muted text-sm">Select a replay to view the map</p>
    </div>
  );
}

function hexToRgb(hex: string, alpha: number = 255): [number, number, number, number] {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return [r, g, b, alpha];
}
