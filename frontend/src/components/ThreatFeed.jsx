import React from 'react';
import AlertCard from './AlertCard';

/**
 * ThreatFeed — renders a scrollable list of AlertCard components.
 *
 * All data is passed via props from App.jsx which owns useAlerts().
 * This component does NOT call any hooks internally — no risk of
 * duplicate WebSocket connections.
 */
export default function ThreatFeed({ onSelectAlert, alerts, loading, error }) {
  const safeAlerts = Array.isArray(alerts) ? alerts : [];

  if (loading && safeAlerts.length === 0) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          padding: 'var(--space-8)',
          color: 'var(--text-secondary)',
          fontFamily: 'var(--font-body)',
        }}
      >
        Loading threat feed...
      </div>
    );
  }

  if (error && safeAlerts.length === 0) {
    return (
      <div
        style={{
          padding: 'var(--space-4)',
          color: 'var(--risk-critical)',
          fontFamily: 'var(--font-body)',
          fontSize: 'var(--text-sm)',
        }}
      >
        Error loading alerts: {error?.message ?? 'Unknown error'}
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflowY: 'auto',
        paddingRight: 'var(--space-1)',
      }}
    >
      {safeAlerts.length === 0 ? (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            minHeight: '300px',
            color: 'var(--text-secondary)',
            border: '1px dashed var(--bg-border)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-6)',
            textAlign: 'center',
          }}
        >
          <span style={{ fontSize: '24px', marginBottom: 'var(--space-2)' }}>📡</span>
          <span style={{ fontFamily: 'var(--font-body)', fontSize: 'var(--text-sm)' }}>
            Monitoring... no correlated threats detected
          </span>
        </div>
      ) : (
        safeAlerts.map((alert) => (
          <AlertCard
            key={alert.alert_id}
            alert={alert}
            onClick={() => onSelectAlert(alert)}
          />
        ))
      )}
    </div>
  );
}
