import React, { useState, useEffect } from 'react';
import {
  RadialBarChart,
  RadialBar,
  PolarAngleAxis,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { getQuantumSummary } from '../api/client';

export default function QuantumPanel() {
  const [summary, setSummary] = useState({
    current_score: 0,
    top_triggered_rules: [],
    trend: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    const fetchQuantumData = async () => {
      try {
        const data = await getQuantumSummary();
        if (active) {
          setSummary(data || { current_score: 0, top_triggered_rules: [], trend: [] });
          setError(null);
          setLoading(false);
        }
      } catch (err) {
        console.error('Failed to fetch quantum summary:', err);
        if (active) setError(err);
      }
    };

    fetchQuantumData();
    const interval = setInterval(fetchQuantumData, 5000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  const score = summary.current_score || 0;
  const rules = summary.top_triggered_rules || [];
  const trend = summary.trend || [];

  const getGaugeColor = (val) => {
    if (val < 15) return 'var(--risk-low)';
    if (val < 40) return 'var(--risk-medium)';
    if (val < 70) return 'var(--risk-high)';
    return 'var(--risk-critical)';
  };

  const gaugeColor = getGaugeColor(score);

  const gaugeData = [
    {
      value: score,
    },
  ];

  const formatHour = (isoString) => {
    if (!isoString) return '';
    try {
      const date = new Date(isoString);
      return `${String(date.getUTCHours()).padStart(2, '0')}:00`;
    } catch (e) {
      return '';
    }
  };

  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          minHeight: '300px',
          color: 'var(--text-secondary)',
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--bg-border)',
          borderRadius: 'var(--radius-md)',
          fontFamily: 'var(--font-body)',
          fontSize: 'var(--text-sm)',
        }}
      >
        Loading quantum status...
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          minHeight: '300px',
          color: 'var(--risk-critical)',
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--bg-border)',
          borderRadius: 'var(--radius-md)',
          fontFamily: 'var(--font-body)',
          fontSize: 'var(--text-sm)',
          padding: 'var(--space-4)',
          textAlign: 'center',
        }}
      >
        Error loading quantum status: {error.message ?? 'Unknown error'}
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-4)',
        padding: 'var(--space-4)',
        backgroundColor: 'var(--bg-surface)',
        border: '1px solid var(--bg-border)',
        borderRadius: 'var(--radius-md)',
        height: '100%',
        overflowY: 'auto',
      }}
    >
      {/* Risk Gauge Header */}
      <div>
        <h4
          style={{
            fontFamily: 'var(--font-body)',
            fontSize: 'var(--text-sm)',
            fontWeight: 'var(--weight-semibold)',
            color: 'var(--text-primary)',
            marginBottom: 'var(--space-2)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-2)',
          }}
        >
          <span style={{ color: 'var(--quantum-accent)' }}>⚛</span> Quantum HNDL Risk
        </h4>
        <div style={{ position: 'relative', height: '140px', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <ResponsiveContainer width="100%" height="100%">
            <RadialBarChart
              innerRadius="75%"
              outerRadius="100%"
              barSize={12}
              data={gaugeData}
              startAngle={225}
              endAngle={-45}
            >
              <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
              <RadialBar
                background={{ fill: 'var(--bg-elevated)' }}
                clockWise
                dataKey="value"
                cornerRadius={6}
                fill={gaugeColor}
              />
            </RadialBarChart>
          </ResponsiveContainer>
          <div
            style={{
              position: 'absolute',
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              pointerEvents: 'none',
            }}
          >
            <span
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: '28px',
                fontWeight: 'var(--weight-bold)',
                color: 'var(--text-primary)',
                lineHeight: '1',
              }}
            >
              {score}
            </span>
            <span style={{ fontFamily: 'var(--font-body)', fontSize: '9px', color: 'var(--text-secondary)', letterSpacing: '0.05em', marginTop: '2px' }}>
              RISK SCORE
            </span>
          </div>
        </div>
      </div>

      {/* Triggered Rules List */}
      <div>
        <h5
          style={{
            fontFamily: 'var(--font-body)',
            fontSize: '11px',
            fontWeight: 'var(--weight-semibold)',
            color: 'var(--text-secondary)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: 'var(--space-2)',
          }}
        >
          Triggered Rules
        </h5>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
          {rules.length > 0 ? (
            rules.map((rule) => (
              <div
                key={rule.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontFamily: 'var(--font-body)',
                  fontSize: 'var(--text-xs)',
                  padding: 'var(--space-2) 0',
                  borderBottom: '1px solid var(--bg-border)',
                }}
              >
                <span style={{ color: 'var(--text-primary)' }}>
                  <span style={{ fontFamily: 'var(--font-display)', color: 'var(--text-muted)', marginRight: 'var(--space-2)' }}>
                    [{rule.id}]
                  </span>
                  {rule.name}
                </span>
                <span
                  style={{
                    color: 'var(--quantum-accent)',
                    fontFamily: 'var(--font-display)',
                    fontWeight: 'var(--weight-bold)',
                  }}
                >
                  +{rule.weight} pts
                </span>
              </div>
            ))
          ) : (
            <div
              style={{
                padding: 'var(--space-3) 0',
                color: 'var(--text-muted)',
                fontSize: 'var(--text-xs)',
                fontFamily: 'var(--font-body)',
                textAlign: 'center',
              }}
            >
              No active HNDL indicators detected
            </div>
          )}
        </div>
      </div>

      {/* 24h Trend Chart */}
      <div style={{ flex: 1, minHeight: '120px', display: 'flex', flexDirection: 'column' }}>
        <h5
          style={{
            fontFamily: 'var(--font-body)',
            fontSize: '11px',
            fontWeight: 'var(--weight-semibold)',
            color: 'var(--text-secondary)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: 'var(--space-2)',
          }}
        >
          24h Trend
        </h5>
        <div style={{ flex: 1, width: '100%', minHeight: '100px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={trend} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
              <defs>
                <linearGradient id="quantumGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--quantum-accent)" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="var(--quantum-accent)" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="timestamp"
                tickFormatter={formatHour}
                stroke="var(--text-muted)"
                fontSize={9}
                tickLine={false}
              />
              <YAxis
                domain={[0, 100]}
                stroke="var(--text-muted)"
                fontSize={9}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--bg-elevated)',
                  borderColor: 'var(--bg-border)',
                  color: 'var(--text-primary)',
                  fontSize: '10px',
                  fontFamily: 'var(--font-body)',
                }}
                labelFormatter={(label) => `Time: ${new Date(label).toLocaleString()}`}
              />
              <Area
                type="monotone"
                dataKey="quantum_risk_score"
                stroke="var(--quantum-accent)"
                fillOpacity={1}
                fill="url(#quantumGrad)"
                strokeWidth={1.5}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
