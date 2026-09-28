const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export async function fetchSummary() {
  const response = await fetch(`${API_BASE_URL}/summary`);
  if (!response.ok) throw new Error('Failed to fetch summary');
  return response.json();
}

export async function fetchEvents(limit = 100, offset = 0, source?: string, satellite?: string) {
  const params = new URLSearchParams({ limit: limit.toString(), offset: offset.toString() });
  if (source) params.append('source', source);
  if (satellite) params.append('satellite', satellite);
  
  const response = await fetch(`${API_BASE_URL}/events?${params.toString()}`);
  if (!response.ok) throw new Error('Failed to fetch events');
  return response.json();
}

export async function fetchEventDetails(eventId: string) {
  const response = await fetch(`${API_BASE_URL}/events/${eventId}`);
  if (!response.ok) throw new Error('Failed to fetch event details');
  return response.json();
}

export async function fetchNotifications() {
  const response = await fetch(`${API_BASE_URL}/notifications`);
  if (!response.ok) throw new Error('Failed to fetch notifications');
  return response.json();
}

export async function fetchHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) throw new Error('Failed to fetch health');
  return response.json();
}

export async function fetchEventImagery(eventId: string) {
  const response = await fetch(`${API_BASE_URL}/events/${eventId}/imagery`);
  if (!response.ok) throw new Error('Failed to fetch imagery metadata');
  return response.json();
}

export async function checkThermalImageAvailable(eventId: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/imagery/${eventId}/thermal`, { method: 'HEAD' });
    return response.status === 200;
  } catch {
    return false;
  }
}

export async function checkInsatImageAvailable(eventId: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/imagery/${eventId}/insat`, { method: 'HEAD' });
    return response.status === 200;
  } catch {
    return false;
  }
}

export async function fetchAuthorities() {
  const response = await fetch(`${API_BASE_URL}/authorities`);
  if (!response.ok) throw new Error('Failed to fetch authorities');
  return response.json();
}

export async function forwardAlert(eventId: string, data: any) {
  const response = await fetch(`${API_BASE_URL}/alerts/${eventId}/forward`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to forward alert');
  }
  return response.json();
}

export async function fetchForwardHistory(eventId: string) {
  const response = await fetch(`${API_BASE_URL}/alerts/${eventId}/forward-history`);
  if (!response.ok) {
    // If not found, it might just mean no history yet.
    if (response.status === 404) return { event_id: eventId, total: 0, records: [] };
    throw new Error('Failed to fetch forward history');
  }
  return response.json();
}
