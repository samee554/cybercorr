import { useEffect, useState, useCallback } from 'react';
import { getAlerts, updateAlertStatus } from '../api/client';
import useWebSocket from './useWebSocket';

/**
 * useAlerts — single source of truth for all alert state.
 *
 * Fetches initial alerts via HTTP, then keeps them live via the
 * shared WebSocket hook. Exposes connectionStatus so callers
 * don't need to import useWebSocket separately (which would open
 * a second WebSocket connection).
 */
export default function useAlerts() {
  // Single WebSocket connection — never call useWebSocket anywhere else
  const { alerts: wsAlerts, connectionStatus } = useWebSocket();
  const [initialAlerts, setInitialAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch initial alerts on mount
  useEffect(() => {
    let active = true;
    const fetchAlerts = async () => {
      try {
        setLoading(true);
        const result = await getAlerts();
        if (active) {
          setInitialAlerts(result?.alerts ?? []);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(err);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    fetchAlerts();
    return () => {
      active = false;
    };
  }, []);

  // Merge: WebSocket alerts take priority (they're the most up-to-date)
  const mergedAlerts = [];
  const alertMap = new Map();

  // 1. Process WebSocket alerts first (so they win on dedup)
  (wsAlerts ?? []).forEach((alert) => {
    if (alert && alert.alert_id && !alertMap.has(alert.alert_id)) {
      alertMap.set(alert.alert_id, alert);
      mergedAlerts.push(alert);
    }
  });

  // 2. Fill in with initial HTTP alerts (backfill only)
  (initialAlerts ?? []).forEach((alert) => {
    if (alert && alert.alert_id && !alertMap.has(alert.alert_id)) {
      alertMap.set(alert.alert_id, alert);
      mergedAlerts.push(alert);
    }
  });

  // Sort newest first
  mergedAlerts.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

  // Update status — optimistic local update + server call
  const updateStatus = useCallback(async (id, status) => {
    try {
      await updateAlertStatus(id, status);
      setInitialAlerts((prev) =>
        prev.map((alert) => (alert.alert_id === id ? { ...alert, status } : alert))
      );
    } catch (err) {
      console.error('Failed to update alert status:', err);
      throw err;
    }
  }, []);

  return {
    alerts: mergedAlerts,
    loading,
    error,
    updateStatus,
    connectionStatus,  // exposed so App.jsx doesn't need a second WS hook
  };
}
