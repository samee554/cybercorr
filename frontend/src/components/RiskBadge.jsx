import React from 'react';

export default function RiskBadge({ level }) {
  const badgeStyle = {
    display: 'inline-block',
    padding: '2px var(--space-2)',
    fontSize: '10px',
    fontWeight: '700',
    textTransform: 'uppercase',
    fontFamily: 'var(--font-display)',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid',
  };

  const getTheme = () => {
    switch (level?.toUpperCase()) {
      case 'CRITICAL':
        return {
          color: 'var(--risk-critical)',
          backgroundColor: 'rgba(255, 45, 85, 0.15)',
          borderColor: 'var(--risk-critical)',
        };
      case 'HIGH':
        return {
          color: 'var(--risk-high)',
          backgroundColor: 'rgba(255, 140, 0, 0.15)',
          borderColor: 'var(--risk-high)',
        };
      case 'MEDIUM':
        return {
          color: 'var(--risk-medium)',
          backgroundColor: 'rgba(253, 214, 10, 0.15)',
          borderColor: 'var(--risk-medium)',
        };
      case 'LOW':
      default:
        return {
          color: 'var(--risk-low)',
          backgroundColor: 'rgba(90, 200, 250, 0.15)',
          borderColor: 'var(--risk-low)',
        };
    }
  };

  return <span style={{ ...badgeStyle, ...getTheme() }}>{level}</span>;
}
