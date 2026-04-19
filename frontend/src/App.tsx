import { useEffect } from 'react';
import { useStore } from './store';
import { Sidebar } from './components/Sidebar';
import { ReplayView } from './views/ReplayView';
import { BacktestView } from './views/BacktestView';
import CompareView from './views/CompareView';
import { TurnControls } from './components/TurnControls';
import { CommandPalette } from './components/CommandPalette';
import TraceViewer from './components/TraceViewer';

export default function App() {
  const { activeView, fetchReplayList, fetchBacktestReport, fetchVariants, currentReplay } = useStore();

  useEffect(() => {
    fetchReplayList();
    fetchBacktestReport();
    fetchVariants();
  }, [fetchReplayList, fetchBacktestReport, fetchVariants]);

  return (
    <div className="flex h-screen overflow-hidden bg-bg-primary">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto">
          {activeView === 'replay' && <ReplayView />}
          {activeView === 'backtest' && <BacktestView />}
          {activeView === 'compare' && <CompareView />}
          {activeView === 'runs' && <CompareView />}
        </div>
        {activeView === 'replay' && currentReplay && <TurnControls />}
      </main>
      <CommandPalette />
      <TraceViewer />
    </div>
  );
}
