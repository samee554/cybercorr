import React, { useState } from 'react';
import useAlerts from './hooks/useAlerts';
import ThreatFeed from './components/ThreatFeed';
import CorrelationGraph from './components/CorrelationGraph';
import QuantumPanel from './components/QuantumPanel';
import FraudHeatmap from './components/FraudHeatmap';
import AlertModal from './components/AlertModal';

export default function App() {
  // Single hook — contains both alert list AND WebSocket connectionStatus.
  // Never import useWebSocket directly here; that would open a second WS connection.
  const { alerts, loading, error, updateStatus, connectionStatus } = useAlerts();
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [filterEntity, setFilterEntity] = useState(null);

  // Live statistics derived from alert list
  const activeAlertsCount = (alerts ?? []).filter(
    (a) => a.status === 'new' || a.status === 'investigating'
  ).length;

  const maxQuantumScore = (alerts ?? []).reduce(
    (max, a) => Math.max(max, a.quantum_risk_score ?? 0),
    0
  );
  const quantumStatus =
    maxQuantumScore >= 70
      ? 'CRITICAL'
      : maxQuantumScore >= 40
      ? 'HIGH'
      : maxQuantumScore >= 15
      ? 'MEDIUM'
      : 'LOW';

  const monetaryAlerts = (alerts ?? []).filter((a) => a.anomaly_score !== undefined && a.anomaly_score !== null);
  const avgAnomaly =
    monetaryAlerts.length > 0
      ? monetaryAlerts.reduce((sum, a) => sum + (a.anomaly_score ?? 0), 0) / monetaryAlerts.length
      : 0.0;
  const anomalyRate = avgAnomaly.toFixed(2);

  const getQuantumColor = (status) => {
    switch (status) {
      case 'CRITICAL':
        return 'var(--risk-critical)';
      case 'HIGH':
        return 'var(--risk-high)';
      case 'MEDIUM':
        return 'var(--risk-medium)';
      default:
        return 'var(--risk-low)';
    }
  };

  const getWsStatusColor = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'var(--green-bright)';
      case 'reconnecting':
        return 'var(--risk-medium)';
      case 'disconnected':
      default:
        return 'var(--risk-critical)';
    }
  };

  // Filter alerts by entity (node) clicked in the graph
  const filteredAlerts = filterEntity
    ? (alerts ?? []).filter(
        (a) =>
          a.user_id === filterEntity ||
          (a.cyber_events ?? []).some(
            (e) => e.ip_address === filterEntity || e.device_id === filterEntity
          ) ||
          (a.transaction_events ?? []).some(
            (t) => t.destination === filterEntity || t.device_id === filterEntity
          )
      )
    : (alerts ?? []);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        width: '100vw',
        overflow: 'hidden',
        backgroundColor: 'var(--bg-base)',
        color: 'var(--text-primary)',
        fontFamily: 'var(--font-body)',
      }}
    >
      {/* Dashboard Header */}
      <header
        style={{
          height: 'var(--header-height)',
          backgroundColor: 'var(--bg-surface)',
          borderBottom: '1px solid var(--bg-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 var(--space-4)',
          zIndex: 10,
          flexShrink: 0,
        }}
      >
        {/* Left: Wordmark & Tagline */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <span
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: 'var(--text-lg)',
              fontWeight: 'var(--weight-bold)',
              color: 'var(--green-bright)',
              letterSpacing: '1px',
            }}
          >
            CyberCorr
          </span>
          <span
            style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--text-secondary)',
              borderLeft: '1px solid var(--bg-border)',
              paddingLeft: 'var(--space-3)',
              fontFamily: 'var(--font-body)',
            }}
          >
            AI Threat Intelligence
          </span>
        </div>

        {/* Center: Live Stats */}
        <div style={{ display: 'flex', gap: 'var(--space-10)' }}>
          <div style={{ textAlign: 'center' }}>
            <div
              role="status"
              aria-label={`${activeAlertsCount} active alerts`}
              style={{
                fontSize: 'var(--text-xl)',
                fontWeight: 'var(--weight-bold)',
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-display)',
              }}
            >
              {activeAlertsCount}
            </div>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>Active Alerts</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div
              style={{
                fontSize: 'var(--text-xl)',
                fontWeight: 'var(--weight-bold)',
                color: getQuantumColor(quantumStatus),
                fontFamily: 'var(--font-display)',
              }}
            >
              {quantumStatus}
            </div>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>Quantum Status</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div
              style={{
                fontSize: 'var(--text-xl)',
                fontWeight: 'var(--weight-bold)',
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-display)',
              }}
            >
              {anomalyRate}
            </div>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>Anomaly Rate</div>
          </div>
        </div>

        {/* Right: Connection Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <span
            style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--text-secondary)',
              fontFamily: 'var(--font-body)',
            }}
          >
            {connectionStatus === 'connected' ? 'LIVE' : connectionStatus.toUpperCase()}
          </span>
          <span
            className={connectionStatus === 'connected' ? 'ws-pulse' : ''}
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: getWsStatusColor(),
              display: 'inline-block',
              transition: 'background-color 300ms ease-out',
            }}
          />
        </div>
      </header>

      {/* Main 3-Column Layout Grid */}
      <main
        style={{
          flex: 1,
          display: 'grid',
          gridTemplateColumns: '35% 40% 25%',
          padding: 'var(--space-4)',
          gap: 'var(--space-4)',
          overflow: 'hidden',
          boxSizing: 'border-box',
          minHeight: 0,
        }}
      >
        {/* Column 1: Threat Feed (35%) */}
        <section
          style={{
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            overflow: 'hidden',
            minHeight: 0,
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 'var(--space-2)',
              flexShrink: 0,
            }}
          >
            <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 'var(--weight-semibold)' }}>
              Threat Feed
            </h3>
            {filterEntity && (
              <button
                onClick={() => setFilterEntity(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--green-bright)',
                  fontSize: 'var(--text-xs)',
                  cursor: 'pointer',
                  padding: 0,
                  textDecoration: 'underline',
                }}
              >
                Clear Filter
              </button>
            )}
          </div>
          <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
            {/* ThreatFeed receives alerts directly — no internal hook calls */}
            <ThreatFeed
              onSelectAlert={setSelectedAlert}
              alerts={filteredAlerts}
              loading={loading}
              error={error}
            />
          </div>
        </section>

        {/* Column 2: Correlation Graph (40%) */}
        <section
          style={{
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            overflow: 'hidden',
            minHeight: 0,
          }}
        >
          <h3
            style={{
              fontSize: 'var(--text-lg)',
              fontWeight: 'var(--weight-semibold)',
              marginBottom: 'var(--space-2)',
              flexShrink: 0,
            }}
          >
            Correlation Graph
          </h3>
          <div style={{ flex: 1, minHeight: 0 }}>
            <CorrelationGraph onNodeClick={(node) => setFilterEntity(node.label ?? node.id)} />
          </div>
        </section>

        {/* Column 3: Panels (25%) */}
        <section
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-4)',
            height: '100%',
            overflowY: 'auto',
            minHeight: 0,
          }}
        >
          <div style={{ height: '55%', minHeight: '300px', flexShrink: 0 }}>
            <QuantumPanel />
          </div>
          <div style={{ height: '45%', minHeight: '200px', flexShrink: 0 }}>
            <FraudHeatmap />
          </div>
        </section>
      </main>

      {/* Alert Details Modal Overlay */}
      {selectedAlert && (
        <AlertModal
          alert={selectedAlert}
          onClose={() => setSelectedAlert(null)}
          updateStatus={updateStatus}
        />
      )}
    </div>
  );
}
