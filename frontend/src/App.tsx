import { useEffect } from 'react';
import { useStore } from './store';
import { Sidebar } from './components/Sidebar';
import { ReplayView } from './views/ReplayView';
import { BacktestView } from './views/BacktestView';
import CompareView from './views/CompareView';
import LiveSimView from './views/LiveSimView';
import { TurnControls } from './components/TurnControls';
import { CommandPalette } from './components/CommandPalette';
import TraceViewer from './components/TraceViewer';

/**
 * URL hash routing:
 *   #simulate           → open simulate tab
 *   #simulate/JOB_ID    → open simulate tab and attach to job
 *   #replay             → open replay tab
 *   #replay/REPLAY_ID   → open replay tab and load specific replay
 *   #backtest           → open backtest tab
 *   #compare            → open compare tab
 */
function parseHash(): { view?: string; id?: string } {
  const hash = window.location.hash.replace('#', '');
  if (!hash) return {};
  const [view, id] = hash.split('/');
  return { view, id };
}

export default function App() {
  const { activeView, fetchReplayList, fetchBacktestReport, fetchVariants, currentReplay, setActiveView } = useStore();

  useEffect(() => {
    fetchReplayList();
    fetchBacktestReport();
    fetchVariants();

    // Handle URL hash on initial load
    const { view, id } = parseHash();
    if (view === 'simulate') {
      setActiveView('simulate');
      if (id) {
        // Auto-attach to job via store — defer to let LiveSimView mount
        setTimeout(() => {
          useStore.setState({ simulationJobId: id, simulationStatus: 'running', liveTurns: [], simulationError: null });
          // Start polling
          const poll = async () => {
            try {
              const res = await fetch(`/api/simulate/${id}/turns`);
              if (!res.ok) return;
              const data = await res.json();
              useStore.setState({ liveTurns: data.turns || [] });
              if (data.status === 'running') {
                setTimeout(poll, 3000);
              } else {
                useStore.setState({ simulationStatus: data.status });
                useStore.getState().fetchReplayList();
              }
            } catch { setTimeout(poll, 5000); }
          };
          poll();
        }, 500);
      }
    } else if (view === 'replay') {
      setActiveView('replay');
      if (id) {
        useStore.getState().loadReplay(id);
      }
    } else if (view === 'backtest') {
      setActiveView('backtest');
    } else if (view === 'compare') {
      setActiveView('compare');
    }

    // Sync hash when view changes
    const unsub = useStore.subscribe((state, prev) => {
      if (state.activeView !== prev.activeView) {
        const jobId = state.simulationJobId;
        if (state.activeView === 'simulate' && jobId) {
          window.location.hash = `simulate/${jobId}`;
        } else {
          window.location.hash = state.activeView;
        }
      }
      // Update hash when simulation starts
      if (state.simulationJobId && state.simulationJobId !== prev.simulationJobId) {
        window.location.hash = `simulate/${state.simulationJobId}`;
      }
    });
    return () => unsub();
  }, [fetchReplayList, fetchBacktestReport, fetchVariants, setActiveView]);

  return (
    <div className="flex h-screen overflow-hidden bg-bg-primary">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto">
          {activeView === 'replay' && <ReplayView />}
          {activeView === 'backtest' && <BacktestView />}
          {activeView === 'compare' && <CompareView />}
          {activeView === 'runs' && <CompareView />}
          {activeView === 'simulate' && <LiveSimView />}
        </div>
        {activeView === 'replay' && currentReplay && <TurnControls />}
      </main>
      <CommandPalette />
      <TraceViewer />
    </div>
  );
}
