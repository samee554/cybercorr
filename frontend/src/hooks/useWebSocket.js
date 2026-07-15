import { useEffect, useState, useRef, useCallback } from 'react';

/**
 * useWebSocket — manages a single WebSocket connection to /ws/alerts.
 *
 * Implements exponential backoff reconnection:
 *   attempt 1: 1s, attempt 2: 2s, attempt 3: 4s, attempt 4: 8s, attempt 5+: 30s (cap)
 *
 * Sets connectionStatus to 'reconnecting' between attempts so the UI can show
 * a reconnecting indicator rather than a hard disconnect.
 *
 * IMPORTANT: This hook must be called exactly once in the app (from useAlerts).
 * Never import it directly from components — that would open duplicate connections.
 */
export default function useWebSocket() {
  const [alerts, setAlerts] = useState([]);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const attemptRef = useRef(0);         // reconnect attempt counter
  const wsRef = useRef(null);
  const isMountedRef = useRef(true);    // prevent state updates after unmount

  // Compute backoff delay from attempt number
  const backoffDelay = (attempt) => {
    // attempt 1→1s, 2→2s, 3→4s, 4→8s, 5+→30s
    if (attempt <= 0) return 1000;
    return Math.min(1000 * Math.pow(2, attempt - 1), 30000);
  };

  const connect = useCallback(() => {
    if (!isMountedRef.current) return;

    const wsUrl = 'ws://localhost:8000/ws/alerts';

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!isMountedRef.current) return;
      attemptRef.current = 0;           // reset attempt counter on success
      setConnectionStatus('connected');
    };

    ws.onmessage = (event) => {
      if (!isMountedRef.current) return;
      try {
        const payload = JSON.parse(event.data);
        if (!payload.success || !payload.data) return;

        const data = payload.data;

        // Heartbeat ping — ignore
        if (data.type === 'ping') return;

        if (data.alerts && Array.isArray(data.alerts)) {
          // Initial snapshot of open alerts on connection
          setAlerts(data.alerts);
        } else if (data.alert_id) {
          // Single alert created or updated
          setAlerts((prev) => {
            const idx = prev.findIndex((a) => a.alert_id === data.alert_id);
            if (idx !== -1) {
              const updated = [...prev];
              updated[idx] = data;
              return updated;
            }
            return [data, ...prev];
          });
        }
      } catch (err) {
        console.error('[WS] Failed to parse message:', err);
      }
    };

    ws.onclose = () => {
      if (!isMountedRef.current) return;
      attemptRef.current += 1;
      const delay = backoffDelay(attemptRef.current);
      setConnectionStatus('reconnecting');

      setTimeout(() => {
        connect();
      }, delay);
    };

    ws.onerror = (error) => {
      console.error('[WS] Error:', error);
      // onclose will fire after onerror, which handles reconnect
    };
  }, []); // stable reference — no deps

  useEffect(() => {
    isMountedRef.current = true;
    connect();

    return () => {
      isMountedRef.current = false;
      if (wsRef.current) {
        // Remove onclose to prevent reconnect loop after unmount
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { alerts, connectionStatus };
}
