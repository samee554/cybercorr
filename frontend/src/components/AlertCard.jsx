import React, { useState, useEffect } from 'react';
import RiskBadge from './RiskBadge';

export default function AlertCard({ alert, onClick }) {
  const [relativeTime, setRelativeTime] = useState('');

  const getRelativeTime = (timestamp) => {
    if (!timestamp) return '';
    const now = new Date();
    const created = new Date(timestamp);
    const diffMs = now - created;
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin <= 0) return 'Just now';
    if (diffMin === 1) return '1 min ago';
    return `${diffMin} min ago`;
  };

  useEffect(() => {
    setRelativeTime(getRelativeTime(alert.created_at));
    const interval = setInterval(() => {
      setRelativeTime(getRelativeTime(alert.created_at));
    }, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, [alert.created_at]);

  const getRiskColor = (level) => {
    switch (level?.toUpperCase()) {
      case 'CRITICAL':
        return 'var(--risk-critical)';
      case 'HIGH':
        return 'var(--risk-high)';
      case 'MEDIUM':
        return 'var(--risk-medium)';
      case 'LOW':
      default:
        return 'var(--risk-low)';
    }
  };

  const borderLeftColor = getRiskColor(alert.overall_risk);
  const isCritical = alert.overall_risk?.toUpperCase() === 'CRITICAL';

  const cyberCount = alert.cyber_events?.length || 0;
  const txCount = alert.transaction_events?.length || 0;
  const txAmount = alert.transaction_events?.reduce((acc, t) => acc + (t.amount || 0), 0) || 0;
  const formattedAmount = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(txAmount);

  const eventSummary = (
    <>
      ⚡ {cyberCount} cyber event{cyberCount !== 1 ? 's' : ''} → {txCount} transaction{txCount !== 1 ? 's' : ''}
      {txCount > 0 ? (
        <> ( <span style={{ fontFamily: 'var(--font-display)' }}>{formattedAmount}</span> transfer)</>
      ) : ''}
    </>
  );

  const summaryText = alert.explanation?.threat_summary
    ? alert.explanation.threat_summary
    : 'Generating explanation...';

  return (
    <article
      onClick={onClick}
      className={`animate-alert-card ${isCritical ? 'animate-border-critical' : ''}`}
      style={{
        width: '100%',
        padding: 'var(--space-4)',
        backgroundColor: 'var(--bg-surface)',
        border: '1px solid var(--bg-border)',
        borderLeft: `3px solid ${borderLeftColor}`,
        borderRadius: 'var(--radius-md)',
        marginBottom: 'var(--space-2)',
        cursor: 'pointer',
        transition: 'background-color 150ms ease-out',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = 'var(--bg-elevated)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = 'var(--bg-surface)';
      }}
    >
      {/* Row 1: Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-2)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <RiskBadge level={alert.overall_risk} />
          <span
            style={{
              fontFamily: 'var(--font-display)',
              color: 'var(--text-primary)',
              fontSize: 'var(--text-sm)',
              fontWeight: 'var(--weight-semibold)',
            }}
          >
            {alert.user_id}
          </span>
        </div>
        <span style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)', fontFamily: 'var(--font-display)' }}>
          {relativeTime}
        </span>
      </div>

      {/* Row 2: Divider */}
      <hr style={{ border: 'none', borderTop: '1px solid var(--bg-border)', margin: 'var(--space-2) 0' }} />

      {/* Row 3: Event Summary */}
      <div
        style={{
          fontFamily: 'var(--font-body)',
          color: 'var(--text-primary)',
          fontSize: 'var(--text-sm)',
          margin: 'var(--space-2) 0',
        }}
      >
        {eventSummary}
      </div>

      {/* Row 4: Divider */}
      <hr style={{ border: 'none', borderTop: '1px solid var(--bg-border)', margin: 'var(--space-2) 0' }} />

      {/* Row 5: AI Explanation Excerpt */}
      <p
        style={{
          fontFamily: 'var(--font-body)',
          color: 'var(--text-secondary)',
          fontSize: 'var(--text-sm)',
          lineHeight: '1.4',
          margin: 'var(--space-2) 0',
          display: '-webkit-box',
          WebkitLineClamp: '2',
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}
      >
        {summaryText}
      </p>

      {/* Row 6: Action */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 'var(--space-2)' }}>
        <span
          style={{
            color: 'var(--green-bright)',
            fontSize: 'var(--text-xs)',
            fontWeight: 'var(--weight-semibold)',
            fontFamily: 'var(--font-body)',
          }}
        >
          View Details
        </span>
      </div>
    </article>
  );
}
