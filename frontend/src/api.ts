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
