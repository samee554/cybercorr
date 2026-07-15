import React, { useState, useEffect } from 'react';
import { getAlert } from '../api/client';
import RiskBadge from './RiskBadge';

export default function AlertModal({ alert, onClose, updateStatus }) {
  const [fullAlert, setFullAlert] = useState(alert);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const fetchFreshAlert = async () => {
      try {
        setLoading(true);
        const data = await getAlert(alert.alert_id);
        if (active) {
          setFullAlert(data);
        }
      } catch (err) {
        console.error('Failed to fetch detailed alert data:', err);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };
    fetchFreshAlert();

    // Set up polling for explanation generation if it's not ready yet
    let intervalId;
    if (!alert.explanation) {
      intervalId = setInterval(async () => {
        try {
          const data = await getAlert(alert.alert_id);
          if (active && data.explanation) {
            setFullAlert(data);
            clearInterval(intervalId);
          }
        } catch (err) {
          console.error('Polling error:', err);
        }
      }, 3000);
    }

    return () => {
      active = false;
      if (intervalId) clearInterval(intervalId);
    };
  }, [alert.alert_id, alert.explanation]);

  // Trap Escape key to close modal
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const handleStatusChange = async (newStatus) => {
    try {
      await updateStatus(fullAlert.alert_id, newStatus);
      setFullAlert((prev) => ({ ...prev, status: newStatus }));
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const formatTime = (isoString) => {
    if (!isoString) return '';
    try {
      const date = new Date(isoString);
      const pad = (n) => String(n).padStart(2, '0');
      return `${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}:${pad(date.getUTCSeconds())} UTC`;
    } catch (e) {
      return isoString;
    }
  };

  const formatAmount = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount || 0);
  };

  const explanation = fullAlert.explanation;

  // Calculate anomaly gauge fill (between -1 and 1)
  // -1 is critical/anomalous (100% fill), 1 is normal (0% fill)
  const rawScore = fullAlert.anomaly_score ?? 0;  // null-safe default
  const anomalySeverity = (1 - rawScore) / 2;
  const anomalyPercent = Math.max(0, Math.min(100, Math.round(anomalySeverity * 100)));

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: 'var(--space-4)',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '720px',
          maxWidth: '100%',
          maxHeight: '85vh',
          backgroundColor: 'var(--bg-elevated)',
          border: '1px solid var(--bg-border)',
          borderRadius: 'var(--radius-lg)',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
        }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        {/* Section 1: Header */}
        <header
          style={{
            padding: 'var(--space-4)',
            borderBottom: '1px solid var(--bg-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
            <RiskBadge level={fullAlert.overall_risk} />
            <span
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: 'var(--text-lg)',
                color: 'var(--text-primary)',
                fontWeight: 'var(--weight-semibold)',
              }}
            >
              {fullAlert.user_id}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
            <span style={{ fontFamily: 'var(--font-display)', fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
              {fullAlert.created_at ? new Date(fullAlert.created_at).toISOString().replace('T', ' ').slice(0, 19) + ' UTC' : ''}
            </span>
            <button
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-secondary)',
                fontSize: '20px',
                cursor: 'pointer',
                outline: 'none',
              }}
              onFocus={(e) => (e.target.style.outline = '2px solid var(--green-bright)')}
              onBlur={(e) => (e.target.style.outline = 'none')}
              aria-label="Close modal"
            >
              ✕
            </button>
          </div>
        </header>

        {/* Scrollable Body Content */}
        <div style={{ padding: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          
          {/* Section 2: AI Explanation */}
          <section>
            <h4
              style={{
                fontFamily: 'var(--font-body)',
                fontSize: 'var(--text-xs)',
                color: 'var(--text-secondary)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: 'var(--space-2)',
                borderBottom: '1px solid var(--bg-border)',
                paddingBottom: 'var(--space-1)',
              }}
            >
              AI Threat Intelligence Brief
            </h4>
            {!explanation ? (
              <div style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)', padding: 'var(--space-2) 0' }}>
                Generating AI threat brief...
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                <div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-xs)', marginBottom: 'var(--space-1)' }}>THREAT SUMMARY</div>
                  <p style={{ color: 'var(--text-primary)', fontSize: 'var(--text-sm)', lineHeight: '1.4' }}>
                    {explanation.threat_summary}
                  </p>
                </div>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
                  <div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-xs)', marginBottom: 'var(--space-1)' }}>RISK LEVEL</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                      <RiskBadge level={explanation.risk_level} />
                      <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-xs)' }}>{explanation.risk_reason}</span>
                    </div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-xs)', marginBottom: 'var(--space-1)' }}>ATTACK PATTERN</div>
                    <span style={{ color: 'var(--text-primary)', fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-semibold)' }}>
                      {explanation.attack_pattern}
                    </span>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
                  <div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-xs)', marginBottom: 'var(--space-1)' }}>RECOMMENDED ACTION</div>
                    <p style={{ color: 'var(--green-bright)', fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-medium)', lineHeight: '1.3' }}>
                      {explanation.recommended_action}
                    </p>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-xs)', marginBottom: 'var(--space-1)' }}>FALSE POSITIVE LIKELIHOOD</div>
                    <span style={{ fontFamily: 'var(--font-display)', fontSize: 'var(--text-base)', color: explanation.false_positive_likelihood > 50 ? 'var(--risk-high)' : 'var(--green-bright)' }}>
                      {explanation.false_positive_likelihood}%
                    </span>
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* Section 3: Scores */}
          <section>
            <h4
              style={{
                fontFamily: 'var(--font-body)',
                fontSize: 'var(--text-xs)',
                color: 'var(--text-secondary)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: 'var(--space-2)',
                borderBottom: '1px solid var(--bg-border)',
                paddingBottom: 'var(--space-1)',
              }}
            >
              Risk Assessment Scores
            </h4>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-8)', padding: 'var(--space-2) 0' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', flex: 1 }}>
                <span style={{ fontFamily: 'var(--font-body)', fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', minWidth: '110px' }}>
                  Anomaly Score:
                </span>
                <div style={{ flex: 1, height: '12px', backgroundColor: 'var(--bg-base)', border: '1px solid var(--bg-border)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${anomalyPercent}%`,
                      backgroundColor: rawScore < -0.2 ? 'var(--risk-critical)' : rawScore < 0.2 ? 'var(--risk-medium)' : 'var(--green-bright)',
                      transition: 'width 300ms ease-out',
                    }}
                  />
                </div>
                <span style={{ fontFamily: 'var(--font-display)', fontSize: 'var(--text-sm)', color: 'var(--text-mono)', minWidth: '45px' }}>
                  {fullAlert.anomaly_score != null ? fullAlert.anomaly_score.toFixed(2) : 'N/A'}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <span style={{ fontFamily: 'var(--font-body)', fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
                  Quantum Risk:
                </span>
                <span style={{ fontFamily: 'var(--font-display)', fontSize: 'var(--text-sm)', color: 'var(--quantum-accent)', fontWeight: 'var(--weight-bold)' }}>
                  {fullAlert.quantum_risk_score}/100
                </span>
              </div>
            </div>
          </section>

          {/* Section 4: Cyber Events */}
          <section>
            <h5
              style={{
                fontFamily: 'var(--font-body)',
                fontSize: 'var(--text-xs)',
                color: 'var(--text-secondary)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: 'var(--space-2)',
              }}
            >
              Cybersecurity Telemetry ({fullAlert.cyber_events?.length || 0})
            </h5>
            <div style={{ overflowX: 'auto', border: '1px solid var(--bg-border)', borderRadius: 'var(--radius-md)' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 'var(--text-sm)' }}>
                <thead>
                  <tr style={{ backgroundColor: 'var(--bg-base)', borderBottom: '1px solid var(--bg-border)' }}>
                    <th style={{ padding: 'var(--space-2)', color: 'var(--text-secondary)', fontWeight: 'var(--weight-medium)' }}>Timestamp</th>
                    <th style={{ padding: 'var(--space-2)', color: 'var(--text-secondary)', fontWeight: 'var(--weight-medium)' }}>Event Type</th>
                    <th style={{ padding: 'var(--space-2)', color: 'var(--text-secondary)', fontWeight: 'var(--weight-medium)' }}>Severity</th>
                    <th style={{ padding: 'var(--space-2)', color: 'var(--text-secondary)', fontWeight: 'var(--weight-medium)' }}>IP Address</th>
                  </tr>
                </thead>
                <tbody>
                  {fullAlert.cyber_events && fullAlert.cyber_events.length > 0 ? (
                    fullAlert.cyber_events.map((e, idx) => (
                      <tr key={idx} style={{ borderBottom: idx < fullAlert.cyber_events.length - 1 ? '1px solid var(--bg-border)' : 'none' }}>
                        <td style={{ padding: 'var(--space-2)', fontFamily: 'var(--font-display)', color: 'var(--text-muted)' }}>{formatTime(e.timestamp)}</td>
                        <td style={{ padding: 'var(--space-2)', color: 'var(--text-primary)' }}>{e.event_type}</td>
                        <td style={{ padding: 'var(--space-2)', fontFamily: 'var(--font-display)', color: e.severity >= 7 ? 'var(--risk-critical)' : e.severity >= 4 ? 'var(--risk-medium)' : 'var(--risk-low)' }}>
                          {e.severity}
                        </td>
                        <td style={{ padding: 'var(--space-2)', fontFamily: 'var(--font-display)', color: 'var(--text-mono)' }}>{e.ip_address}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="4" style={{ padding: 'var(--space-4)', textAlign: 'center', color: 'var(--text-muted)' }}>
                        No cybersecurity events correlated.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          {/* Section 5: Transaction Events */}
          <section>
            <h5
              style={{
                fontFamily: 'var(--font-body)',
                fontSize: 'var(--text-xs)',
                color: 'var(--text-secondary)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: 'var(--space-2)',
              }}
            >
              Transactional Behaviour ({fullAlert.transaction_events?.length || 0})
            </h5>
            <div style={{ overflowX: 'auto', border: '1px solid var(--bg-border)', borderRadius: 'var(--radius-md)' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 'var(--text-sm)' }}>
                <thead>
                  <tr style={{ backgroundColor: 'var(--bg-base)', borderBottom: '1px solid var(--bg-border)' }}>
                    <th style={{ padding: 'var(--space-2)', color: 'var(--text-secondary)', fontWeight: 'var(--weight-medium)' }}>Timestamp</th>
                    <th style={{ padding: 'var(--space-2)', color: 'var(--text-secondary)', fontWeight: 'var(--weight-medium)' }}>Tx Type</th>
                    <th style={{ padding: 'var(--space-2)', color: 'var(--text-secondary)', fontWeight: 'var(--weight-medium)' }}>Amount</th>
                    <th style={{ padding: 'var(--space-2)', color: 'var(--text-secondary)', fontWeight: 'var(--weight-medium)' }}>Destination</th>
                  </tr>
                </thead>
                <tbody>
                  {fullAlert.transaction_events && fullAlert.transaction_events.length > 0 ? (
                    fullAlert.transaction_events.map((t, idx) => (
                      <tr key={idx} style={{ borderBottom: idx < fullAlert.transaction_events.length - 1 ? '1px solid var(--bg-border)' : 'none' }}>
                        <td style={{ padding: 'var(--space-2)', fontFamily: 'var(--font-display)', color: 'var(--text-muted)' }}>{formatTime(t.timestamp)}</td>
                        <td style={{ padding: 'var(--space-2)', color: 'var(--text-primary)' }}>{t.tx_type}</td>
                        <td style={{ padding: 'var(--space-2)', fontFamily: 'var(--font-display)', color: t.amount > 10000 ? 'var(--risk-high)' : 'var(--text-primary)' }}>
                          {formatAmount(t.amount)}
                        </td>
                        <td style={{ padding: 'var(--space-2)', fontFamily: 'var(--font-display)', color: 'var(--text-mono)' }}>{t.destination}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="4" style={{ padding: 'var(--space-4)', textAlign: 'center', color: 'var(--text-muted)' }}>
                        No transactions correlated.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          {/* Section 6: Actions */}
          <footer
            style={{
              marginTop: 'var(--space-2)',
              paddingTop: 'var(--space-4)',
              borderTop: '1px solid var(--bg-border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <button
                onClick={() => handleStatusChange('investigating')}
                style={{
                  padding: 'var(--space-2) var(--space-4)',
                  backgroundColor: fullAlert.status === 'investigating' ? 'rgba(253, 214, 10, 0.2)' : 'var(--bg-base)',
                  border: '1px solid var(--bg-border)',
                  borderColor: fullAlert.status === 'investigating' ? 'var(--risk-medium)' : 'var(--bg-border)',
                  color: fullAlert.status === 'investigating' ? 'var(--risk-medium)' : 'var(--text-secondary)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: 'var(--text-sm)',
                  cursor: 'pointer',
                  fontWeight: 'var(--weight-medium)',
                  outline: 'none',
                }}
                onFocus={(e) => (e.target.style.outline = '2px solid var(--green-bright)')}
                onBlur={(e) => (e.target.style.outline = 'none')}
              >
                Mark Investigating
              </button>
              <button
                onClick={() => handleStatusChange('resolved')}
                style={{
                  padding: 'var(--space-2) var(--space-4)',
                  backgroundColor: fullAlert.status === 'resolved' ? 'rgba(0, 255, 136, 0.1)' : 'var(--bg-base)',
                  border: '1px solid var(--bg-border)',
                  borderColor: fullAlert.status === 'resolved' ? 'var(--green-bright)' : 'var(--bg-border)',
                  color: fullAlert.status === 'resolved' ? 'var(--green-bright)' : 'var(--text-secondary)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: 'var(--text-sm)',
                  cursor: 'pointer',
                  fontWeight: 'var(--weight-medium)',
                  outline: 'none',
                }}
                onFocus={(e) => (e.target.style.outline = '2px solid var(--green-bright)')}
                onBlur={(e) => (e.target.style.outline = 'none')}
              >
                Resolve
              </button>
              <button
                onClick={() => handleStatusChange('false_positive')}
                style={{
                  padding: 'var(--space-2) var(--space-4)',
                  backgroundColor: fullAlert.status === 'false_positive' ? 'rgba(255, 45, 85, 0.1)' : 'var(--bg-base)',
                  border: '1px solid var(--bg-border)',
                  borderColor: fullAlert.status === 'false_positive' ? 'var(--risk-critical)' : 'var(--bg-border)',
                  color: fullAlert.status === 'false_positive' ? 'var(--risk-critical)' : 'var(--text-secondary)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: 'var(--text-sm)',
                  cursor: 'pointer',
                  fontWeight: 'var(--weight-medium)',
                  outline: 'none',
                }}
                onFocus={(e) => (e.target.style.outline = '2px solid var(--green-bright)')}
                onBlur={(e) => (e.target.style.outline = 'none')}
              >
                False Positive
              </button>
            </div>
            <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)', fontFamily: 'var(--font-body)' }}>
              Status: <strong style={{ color: 'var(--text-primary)', textTransform: 'uppercase' }}>{fullAlert.status}</strong>
            </span>
          </footer>
        </div>
      </div>
    </div>
  );
}
