import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import type {
  EventDetail,
  MonitorStatus,
  ProfileSummary,
  StepDetail,
  StepSummary,
  WsMessage,
} from '../models/types';

function upsertProfile(list: ProfileSummary[], p: ProfileSummary): ProfileSummary[] {
  const idx = list.findIndex((x) => x.id === p.id);
  if (idx === -1) return [...list, p].sort((a, b) => (a.createdAt ?? 0) - (b.createdAt ?? 0));
  const next = list.slice();
  next[idx] = p;
  return next;
}

export function useViewer() {
  const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
  const [monitor, setMonitor] = useState<MonitorStatus | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
  const [steps, setSteps] = useState<StepSummary[]>([]);
  const [stepsLoading, setStepsLoading] = useState(false);
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
  const [stepDetail, setStepDetail] = useState<StepDetail | null>(null);
  const [stepDetailLoading, setStepDetailLoading] = useState(false);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [eventDetail, setEventDetail] = useState<EventDetail | null>(null);
  const [eventDetailLoading, setEventDetailLoading] = useState(false);
  const [autoFollow, setAutoFollow] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const autoFollowRef = useRef(autoFollow);
  autoFollowRef.current = autoFollow;
  const selectedProfileRef = useRef(selectedProfileId);
  selectedProfileRef.current = selectedProfileId;

  const loadStepDetail = useCallback(async (profileId: string, stepId: string) => {
    setSelectedStepId(stepId);
    setStepDetailLoading(true);
    setStepDetail(null);
    setSelectedEventId(null);
    setEventDetail(null);
    try {
      const detail = await api.stepDetail(profileId, stepId);
      setStepDetail(detail);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setStepDetailLoading(false);
    }
  }, []);

  const loadSteps = useCallback(
    async (profileId: string, autoSelect = true) => {
      setStepsLoading(true);
      try {
        const { steps: list } = await api.steps(profileId);
        setSteps(list);
        if (autoSelect && list.length > 0) {
          // Prefer the first DECODE step, else the first step.
          const decode = list.find((s) => s.stage === 'DECODE');
          await loadStepDetail(profileId, (decode ?? list[0]).id);
        } else {
          setStepDetail(null);
          setSelectedStepId(null);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setStepsLoading(false);
      }
    },
    [loadStepDetail],
  );

  const selectProfile = useCallback(
    (profileId: string) => {
      setSelectedProfileId(profileId);
      setSteps([]);
      setStepDetail(null);
      setSelectedStepId(null);
      setEventDetail(null);
      setSelectedEventId(null);
      void loadSteps(profileId);
    },
    [loadSteps],
  );

  const selectStep = useCallback(
    (stepId: string) => {
      if (selectedProfileRef.current) void loadStepDetail(selectedProfileRef.current, stepId);
    },
    [loadStepDetail],
  );

  const selectEvent = useCallback(async (eventId: string | null) => {
    setSelectedEventId(eventId);
    setEventDetail(null);
    if (!eventId || !selectedProfileRef.current) return;
    setEventDetailLoading(true);
    try {
      const detail = await api.eventDetail(selectedProfileRef.current, eventId);
      setEventDetail(detail);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setEventDetailLoading(false);
    }
  }, []);

  // Initial load + WebSocket connection.
  useEffect(() => {
    let disposed = false;
    let ws: WebSocket | null = null;
    let retryTimer: number | undefined;

    api
      .profiles()
      .then(({ profiles: list }) => {
        if (disposed) return;
        setProfiles(list);
        const ready = list.find((p) => p.status === 'ready');
        if (ready) selectProfile(ready.id);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));

    function connect() {
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
      ws = new WebSocket(`${proto}://${window.location.host}/api/ws`);
      ws.onopen = () => setWsConnected(true);
      ws.onmessage = (msg) => {
        const data = JSON.parse(msg.data) as WsMessage;
        if (data.type === 'init') {
          setMonitor(data.monitor);
          setProfiles(data.profiles);
          return;
        }
        if (data.type === 'monitor_status') {
          setMonitor(data.monitor);
          return;
        }
        if (data.type === 'profile_discovered' || data.type === 'profile_ready') {
          setProfiles((prev) => upsertProfile(prev, data.profile));
          if (data.type === 'profile_ready' && autoFollowRef.current) {
            if (selectedProfileRef.current === data.profileId) {
              void loadSteps(data.profileId, false);
            } else {
              selectProfile(data.profileId);
            }
          }
          return;
        }
        if (data.type === 'profile_parsing' || data.type === 'profile_failed') {
          // Refresh the list to pick up status changes.
          api
            .profiles()
            .then(({ profiles: list }) => setProfiles(list))
            .catch(() => undefined);
          if (data.type === 'profile_failed' && !data.temporary) {
            setError(`Profile ${data.profileId} failed: ${data.error}`);
          }
          return;
        }
        if (data.type === 'profile_removed') {
          setProfiles((prev) => prev.filter((p) => p.id !== data.profileId));
          if (selectedProfileRef.current === data.profileId) {
            setSelectedProfileId(null);
            setSteps([]);
            setStepDetail(null);
          }
        }
      };
      ws.onclose = () => {
        setWsConnected(false);
        if (!disposed) retryTimer = window.setTimeout(connect, 2000);
      };
      ws.onerror = () => ws?.close();
    }
    connect();

    return () => {
      disposed = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      ws?.close();
    };
  }, [loadSteps, selectProfile]);

  return {
    profiles,
    monitor,
    wsConnected,
    selectedProfileId,
    selectProfile,
    steps,
    stepsLoading,
    selectedStepId,
    selectStep,
    stepDetail,
    stepDetailLoading,
    selectedEventId,
    selectEvent,
    eventDetail,
    eventDetailLoading,
    autoFollow,
    setAutoFollow,
    error,
    setError,
  };
}

export type ViewerState = ReturnType<typeof useViewer>;
