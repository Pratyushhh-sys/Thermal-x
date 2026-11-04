/**
 * frontend/src/hooks/useThermalEvents.ts
 * =======================================
 * Reusable React hook for Server-Sent Events (SSE) in SIH 2026 Thermal Source Attribution.
 *
 * Implements:
 *   - Native browser EventSource API.
 *   - Connects to ${API_BASE_URL}/events/stream using existing API configuration.
 *   - Listens for all named events:
 *       1. thermal_event
 *       2. high_risk_alert
 *       3. dashboard_update
 *       4. notification
 *       5. system_status
 *       6. heartbeat
 *   - Connection state management: CONNECTED | CONNECTING | DISCONNECTED | ERROR
 *   - Automatic reconnection with exponential backoff & cleanup on unmount
 *   - Duplicate event prevention through event IDs
 *   - Safe JSON parsing with fallback
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { API_BASE_URL } from '../api';

export type SSEConnectionState = 'CONNECTED' | 'CONNECTING' | 'DISCONNECTED' | 'ERROR';

export interface UseThermalEventsOptions {
  onThermalEvent?: (event: any) => void;
  onHighRiskAlert?: (alert: any) => void;
  onDashboardUpdate?: (update: any) => void;
  onNotification?: (notification: any) => void;
  onSystemStatus?: (status: any) => void;
  onHeartbeat?: (heartbeat: any) => void;
  enabled?: boolean;
}

export interface UseThermalEventsReturn {
  connectionStatus: SSEConnectionState;
  lastEventId: string | null;
  error: Error | null;
  reconnect: () => void;
}

const INITIAL_RETRY_DELAY_MS = 2000;
const MAX_RETRY_DELAY_MS = 30000;
const BACKOFF_FACTOR = 1.5;

export function useThermalEvents(options: UseThermalEventsOptions = {}): UseThermalEventsReturn {
  const {
    onThermalEvent,
    onHighRiskAlert,
    onDashboardUpdate,
    onNotification,
    onSystemStatus,
    onHeartbeat,
    enabled = true,
  } = options;

  const [connectionStatus, setConnectionStatus] = useState<SSEConnectionState>('DISCONNECTED');
  const [lastEventId, setLastEventId] = useState<string | null>(null);
  const [error, setError] = useState<Error | null>(null);

  // Keep callback refs fresh without causing reconnection on parent render
  const callbacksRef = useRef(options);
  useEffect(() => {
    callbacksRef.current = options;
  });

  // Track processed event IDs to prevent duplicate processing
  const processedEventIdsRef = useRef<Set<string>>(new Set());

  // Connection refs
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const retryDelayRef = useRef<number>(INITIAL_RETRY_DELAY_MS);
  const isManuallyClosedRef = useRef<boolean>(false);

  const cleanup = useCallback(() => {
    if (reconnectTimeoutRef.current !== null) {
      window.clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!enabled) return;
    cleanup();

    isManuallyClosedRef.current = false;
    setConnectionStatus('CONNECTING');
    setError(null);

    // Resolve URL: relative to current origin or API base
    const streamUrl = `${API_BASE_URL}/events/stream`;

    try {
      const es = new EventSource(streamUrl, { withCredentials: true });
      eventSourceRef.current = es;

      es.onopen = () => {
        setConnectionStatus('CONNECTED');
        setError(null);
        retryDelayRef.current = INITIAL_RETRY_DELAY_MS; // Reset backoff on success
      };

      // Helper to safely parse and invoke callback with deduplication
      const handleNamedEvent = (
        event: MessageEvent,
        callback?: (data: any) => void,
        dedupKeyPrefix?: string
      ) => {
        const rawId = event.lastEventId;
        if (rawId) {
          setLastEventId(rawId);
        }

        let parsed: any = null;
        try {
          parsed = JSON.parse(event.data);
        } catch {
          parsed = event.data;
        }

        // Check deduplication key: event id or payload id
        const uniqueId = rawId || (parsed && typeof parsed === 'object' ? parsed.id || parsed.event_id : null);
        if (uniqueId) {
          const key = dedupKeyPrefix ? `${dedupKeyPrefix}:${uniqueId}` : uniqueId;
          if (processedEventIdsRef.current.has(key)) {
            return; // Duplicate ignored
          }
          processedEventIdsRef.current.add(key);

          // Prevent unbounded memory growth
          if (processedEventIdsRef.current.size > 2000) {
            const arr = Array.from(processedEventIdsRef.current);
            processedEventIdsRef.current = new Set(arr.slice(arr.length - 1000));
          }
        }

        if (callback) {
          try {
            callback(parsed);
          } catch (err) {
            console.error('Error in SSE callback handler:', err);
          }
        }
      };

      // 1. thermal_event
      es.addEventListener('thermal_event', (e: MessageEvent) => {
        handleNamedEvent(e, callbacksRef.current.onThermalEvent, 'thermal');
      });

      // 2. high_risk_alert
      es.addEventListener('high_risk_alert', (e: MessageEvent) => {
        handleNamedEvent(e, callbacksRef.current.onHighRiskAlert, 'alert');
      });

      // 3. dashboard_update
      es.addEventListener('dashboard_update', (e: MessageEvent) => {
        handleNamedEvent(e, callbacksRef.current.onDashboardUpdate, 'dashboard');
      });

      // 4. notification
      es.addEventListener('notification', (e: MessageEvent) => {
        handleNamedEvent(e, callbacksRef.current.onNotification, 'notif');
      });

      // 5. system_status
      es.addEventListener('system_status', (e: MessageEvent) => {
        handleNamedEvent(e, callbacksRef.current.onSystemStatus);
      });

      // 6. heartbeat
      es.addEventListener('heartbeat', (e: MessageEvent) => {
        handleNamedEvent(e, callbacksRef.current.onHeartbeat);
      });

      // Fallback message listener
      es.onmessage = (e: MessageEvent) => {
        handleNamedEvent(e, callbacksRef.current.onThermalEvent);
      };

      es.onerror = (e) => {
        if (isManuallyClosedRef.current) return;

        setConnectionStatus('ERROR');
        setError(new Error('SSE connection encountered an error'));

        // If closed, schedule reconnection with exponential backoff
        if (es.readyState === EventSource.CLOSED) {
          es.close();
          eventSourceRef.current = null;
          setConnectionStatus('DISCONNECTED');

          const delay = retryDelayRef.current;
          retryDelayRef.current = Math.min(delay * BACKOFF_FACTOR, MAX_RETRY_DELAY_MS);

          reconnectTimeoutRef.current = window.setTimeout(() => {
            if (!isManuallyClosedRef.current && enabled) {
              connect();
            }
          }, delay);
        }
      };
    } catch (err) {
      setConnectionStatus('ERROR');
      setError(err instanceof Error ? err : new Error(String(err)));
    }
  }, [enabled, cleanup]);

  const reconnect = useCallback(() => {
    retryDelayRef.current = INITIAL_RETRY_DELAY_MS;
    connect();
  }, [connect]);

  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      cleanup();
      setConnectionStatus('DISCONNECTED');
    }

    return () => {
      isManuallyClosedRef.current = true;
      cleanup();
      setConnectionStatus('DISCONNECTED');
    };
  }, [enabled, connect, cleanup]);

  return {
    connectionStatus,
    lastEventId,
    error,
    reconnect,
  };
}

