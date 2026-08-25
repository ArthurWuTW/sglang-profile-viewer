import type {
  EventDetail,
  ProfileSummary,
  StepDetail,
  StepSummary,
} from '../models/types';

const BASE = '/api';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(BASE + path);
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body && typeof body.detail === 'string') detail = body.detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  profiles: () => get<{ profiles: ProfileSummary[] }>('/profiles'),
  profile: (id: string) => get<ProfileSummary>(`/profiles/${id}`),
  steps: (id: string, stage?: string) =>
    get<{ steps: StepSummary[] }>(
      `/profiles/${id}/steps${stage ? `?stage=${encodeURIComponent(stage)}` : ''}`,
    ),
  stepDetail: (id: string, stepId: string) =>
    get<StepDetail>(`/profiles/${id}/steps/${stepId}`),
  eventDetail: (id: string, eventId: string) =>
    get<EventDetail>(`/profiles/${id}/events/${eventId}`),
};
