/* ── Zustand store: single source of truth for app state ── */

import { create } from 'zustand';
import type {
  ReplayLog, BacktestReport, VariantResult, ReplaySummary,
  RunSummary, RunComparison, LLMTrace,
} from './types';

const API = '';

export type ActiveView = 'replay' | 'backtest' | 'runs' | 'compare';

interface AppState {
  /* ── Data ── */
  replayList: ReplaySummary[];
  currentReplay: ReplayLog | null;
  backtestReport: BacktestReport | null;
  variants: VariantResult[];

  /* ── Observability data ── */
  runs: RunSummary[];
  selectedRunIds: string[]; // for comparison (max 2)
  comparison: RunComparison | null;
  currentTraces: LLMTrace[];
  selectedTrace: LLMTrace | null;

  /* ── UI state ── */
  currentTurn: number;
  selectedActorId: string | null;
  activeView: ActiveView;
  isPlaying: boolean;
  playSpeed: number; // ms per turn

  /* ── Loading ── */
  loading: boolean;
  error: string | null;

  /* ── Actions ── */
  fetchReplayList: () => Promise<void>;
  loadReplay: (id: string) => Promise<void>;
  fetchBacktestReport: () => Promise<void>;
  fetchVariants: () => Promise<void>;
  setTurn: (turn: number) => void;
  nextTurn: () => void;
  prevTurn: () => void;
  setSelectedActor: (id: string | null) => void;
  setActiveView: (view: ActiveView) => void;
  togglePlay: () => void;
  setPlaySpeed: (ms: number) => void;

  /* ── Observability actions ── */
  fetchRuns: () => Promise<void>;
  fetchTraces: (runId: string, actor?: string) => Promise<void>;
  fetchComparison: (runIds: string[]) => Promise<void>;
  selectTrace: (trace: LLMTrace | null) => void;
  toggleRunForComparison: (runId: string) => void;
}

export const useStore = create<AppState>((set, get) => ({
  replayList: [],
  currentReplay: null,
  backtestReport: null,
  variants: [],

  runs: [],
  selectedRunIds: [],
  comparison: null,
  currentTraces: [],
  selectedTrace: null,

  currentTurn: 1,
  selectedActorId: null,
  activeView: 'replay',
  isPlaying: false,
  playSpeed: 2000,

  loading: false,
  error: null,

  fetchReplayList: async () => {
    try {
      const res = await fetch(`${API}/api/replays`);
      const data = await res.json();
      set({ replayList: data.replays });
    } catch (e) {
      set({ error: `Failed to fetch replays: ${e}` });
    }
  },

  loadReplay: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const res = await fetch(`${API}/api/replays/${id}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: ReplayLog = await res.json();
      set({ currentReplay: data, currentTurn: 1, loading: false, selectedActorId: null });
    } catch (e) {
      set({ loading: false, error: `Failed to load replay: ${e}` });
    }
  },

  fetchBacktestReport: async () => {
    try {
      const res = await fetch(`${API}/api/backtest/report`);
      if (!res.ok) return;
      const data: BacktestReport = await res.json();
      set({ backtestReport: data });
    } catch {
      // Silently fail — backtest may not exist yet
    }
  },

  fetchVariants: async () => {
    try {
      const res = await fetch(`${API}/api/backtest/variants`);
      if (!res.ok) return;
      const data: VariantResult[] = await res.json();
      set({ variants: data });
    } catch {
      // Silently fail
    }
  },

  setTurn: (turn: number) => set({ currentTurn: turn }),

  nextTurn: () => {
    const { currentTurn, currentReplay } = get();
    if (currentReplay && currentTurn < currentReplay.turns.length) {
      set({ currentTurn: currentTurn + 1 });
    } else {
      set({ isPlaying: false });
    }
  },

  prevTurn: () => {
    const { currentTurn } = get();
    if (currentTurn > 1) set({ currentTurn: currentTurn - 1 });
  },

  setSelectedActor: (id) => set({ selectedActorId: id }),
  setActiveView: (view) => set({ activeView: view }),

  togglePlay: () => set(s => ({ isPlaying: !s.isPlaying })),
  setPlaySpeed: (ms) => set({ playSpeed: ms }),

  /* ── Observability actions ── */
  fetchRuns: async () => {
    try {
      const res = await fetch(`${API}/api/runs`);
      if (res.ok) {
        const data = await res.json();
        set({ runs: data });
      }
    } catch (e) {
      console.error('Failed to fetch runs:', e);
    }
  },

  fetchTraces: async (runId: string, actor?: string) => {
    try {
      let url = `${API}/api/runs/${runId}/traces`;
      if (actor) url += `?actor=${actor}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        set({ currentTraces: data.traces || [] });
      }
    } catch (e) {
      console.error('Failed to fetch traces:', e);
    }
  },

  fetchComparison: async (runIds: string[]) => {
    try {
      const res = await fetch(`${API}/api/compare?run_ids=${runIds.join(',')}`);
      if (res.ok) {
        const data = await res.json();
        set({ comparison: data });
      }
    } catch (e) {
      console.error('Failed to fetch comparison:', e);
    }
  },

  selectTrace: (trace: LLMTrace | null) => set({ selectedTrace: trace }),

  toggleRunForComparison: (runId: string) => {
    const current = get().selectedRunIds;
    if (current.includes(runId)) {
      set({ selectedRunIds: current.filter(id => id !== runId) });
    } else if (current.length < 2) {
      set({ selectedRunIds: [...current, runId] });
    }
  },
}));
