import { useMemo, useState } from 'react';
import { useViewer } from './store/useViewer';
import ProfileList from './components/ProfileList';
import StepList from './components/StepList';
import Timeline from './components/Timeline';
import EventDetail from './components/EventDetail';
import StatusBar from './components/StatusBar';
import SearchFilter from './components/SearchFilter';
import { CATEGORY_ROW_ORDER } from './utils/colors';

export default function App() {
  const v = useViewer();
  const [hiddenCategories, setHiddenCategories] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState('');
  const [profilesCollapsed, setProfilesCollapsed] = useState(false);
  const [stepsCollapsed, setStepsCollapsed] = useState(false);

  const presentCategories = useMemo(() => {
    if (!v.stepDetail) return [];
    const present = new Set(v.stepDetail.events.map((e) => e.category));
    return CATEGORY_ROW_ORDER.filter((c) => present.has(c));
  }, [v.stepDetail]);

  const toggleCategory = (cat: string) => {
    setHiddenCategories((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  };

  return (
    <div className="h-screen flex flex-col bg-gray-950 text-gray-100">
      <header className="flex items-center gap-3 px-4 py-2 border-b border-gray-800 bg-gray-900">
        <span className="text-base font-bold tracking-tight">
          SGLang <span className="text-sky-400">Profiler Viewer</span>
        </span>
        <span className="text-xs text-gray-500">
          local · semantic timeline · raw trace preserved
        </span>
      </header>

      <StatusBar
        monitor={v.monitor}
        wsConnected={v.wsConnected}
        autoFollow={v.autoFollow}
        onAutoFollowChange={v.setAutoFollow}
      />

      {v.error && (
        <div className="px-4 py-1.5 text-xs text-red-400 bg-red-950/40 border-b border-red-900/50">
          {v.error}
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        {/* Left: profile list */}
        <aside className={`shrink-0 border-r border-gray-800 bg-gray-900/30 transition-all duration-200 ${profilesCollapsed ? 'w-10' : 'w-72'}`}>
          <ProfileList
            profiles={v.profiles}
            selectedId={v.selectedProfileId}
            onSelect={v.selectProfile}
            collapsed={profilesCollapsed}
            onToggleCollapse={() => setProfilesCollapsed((c) => !c)}
          />
        </aside>

        {/* Middle-left: step list + filters */}
        <aside className={`shrink-0 border-r border-gray-800 bg-gray-900/30 flex flex-col transition-all duration-200 ${stepsCollapsed ? 'w-10' : 'w-64'}`}>
          {stepsCollapsed ? (
            <button
              onClick={() => setStepsCollapsed(false)}
              className="flex flex-col items-center pt-2 gap-2 text-gray-400 hover:text-gray-200 hover:bg-gray-800/60 transition-colors"
              title="Expand steps panel"
            >
              <span className="text-xs">▶</span>
              <span className="text-[10px] tracking-wider" style={{ writingMode: 'vertical-rl' }}>
                STEPS
              </span>
            </button>
          ) : (
            <>
              <div className="flex-1 min-h-0">
                <StepList
                  steps={v.steps}
                  loading={v.stepsLoading}
                  selectedId={v.selectedStepId}
                  onSelect={v.selectStep}
                  collapsed={stepsCollapsed}
                  onToggleCollapse={() => setStepsCollapsed(true)}
                />
              </div>
              <div className="border-t border-gray-800 max-h-64 overflow-y-auto">
                <SearchFilter
                  search={search}
                  onSearchChange={setSearch}
                  presentCategories={presentCategories}
                  hiddenCategories={hiddenCategories}
                  onToggleCategory={toggleCategory}
                />
              </div>
            </>
          )}
        </aside>

        {/* Main: timeline + event detail */}
        <main className="flex-1 flex flex-col min-w-0">
          <div className="flex-1 min-h-0">
            {v.stepDetail ? (
              <Timeline
                detail={v.stepDetail}
                selectedEventId={v.selectedEventId}
                onSelectEvent={(id) => v.selectEvent(id)}
                hiddenCategories={hiddenCategories}
                search={search}
              />
            ) : (
              <div className="h-full flex items-center justify-center text-gray-500 text-sm">
                {v.stepDetailLoading
                  ? 'Loading step…'
                  : 'Select a profile and a step to view the timeline.'}
              </div>
            )}
          </div>
          <div className="h-72 shrink-0 border-t border-gray-800 bg-gray-900/30">
            <EventDetail detail={v.eventDetail} loading={v.eventDetailLoading} />
          </div>
        </main>
      </div>
    </div>
  );
}
