import React, { useState, useEffect } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { getFraudHeatmap } from '../api/client';

export default function FraudHeatmap() {
  const [heatmapData, setHeatmapData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    const fetchHeatmap = async () => {
      try {
        const data = await getFraudHeatmap();
        if (active) {
          setHeatmapData(data || []);
          setError(null);
          setLoading(false);
        }
      } catch (err) {
        console.error('Failed to fetch fraud heatmap:', err);
        if (active) setError(err);
      }
    };

    fetchHeatmap();
    const interval = setInterval(fetchHeatmap, 5000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  const processedData = heatmapData.map((d) => {
    const score = d.average_anomaly_score;
    // Categorize scores into normal, suspicious, anomaly
    // In config.py: normal > 0.1, anomaly < -0.1
    return {
      timestamp: d.timestamp,
      score: score,
      normal: score >= 0.1 ? score : null,
      suspicious: score < 0.1 && score >= -0.1 ? score : null,
      anomaly: score < -0.1 ? score : null,
    };
  });

  const formatTimeBucket = (isoString) => {
    if (!isoString) return '';
    try {
      const date = new Date(isoString);
      const pad = (n) => String(n).padStart(2, '0');
      return `${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}`;
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
          minHeight: '180px',
          color: 'var(--text-secondary)',
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--bg-border)',
          borderRadius: 'var(--radius-md)',
          fontFamily: 'var(--font-body)',
          fontSize: 'var(--text-sm)',
        }}
      >
        Loading heatmap...
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
          minHeight: '180px',
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
        Error loading heatmap: {error.message ?? 'Unknown error'}
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-2)',
        padding: 'var(--space-4)',
        backgroundColor: 'var(--bg-surface)',
        border: '1px solid var(--bg-border)',
        borderRadius: 'var(--radius-md)',
        height: '100%',
        minHeight: '180px',
      }}
    >
      <h4
        style={{
          fontFamily: 'var(--font-body)',
          fontSize: 'var(--text-sm)',
          fontWeight: 'var(--weight-semibold)',
          color: 'var(--text-primary)',
          marginBottom: 'var(--space-1)',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-2)',
        }}
      >
        <span style={{ color: 'var(--risk-critical)' }}>🔥</span> Transaction Anomaly Heatmap
      </h4>

      <div style={{ flex: 1, width: '100%', minHeight: '120px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={processedData} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
            <defs>
              <linearGradient id="normalGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--chart-1)" stopOpacity={0.2} />
                <stop offset="95%" stopColor="var(--chart-1)" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="suspiciousGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--risk-medium)" stopOpacity={0.2} />
                <stop offset="95%" stopColor="var(--risk-medium)" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="anomalyGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--risk-critical)" stopOpacity={0.2} />
                <stop offset="95%" stopColor="var(--risk-critical)" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="timestamp"
              tickFormatter={formatTimeBucket}
              stroke="var(--text-muted)"
              fontSize={9}
              tickLine={false}
            />
            <YAxis
              reversed
              domain={[-0.5, 0.5]}
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
            <ReferenceLine y={0} stroke="var(--bg-border)" strokeDasharray="3 3" />
            <Area
              type="monotone"
              dataKey="normal"
              stroke="var(--chart-1)"
              fillOpacity={1}
              fill="url(#normalGrad)"
              strokeWidth={1.5}
              connectNulls
            />
            <Area
              type="monotone"
              dataKey="suspicious"
              stroke="var(--risk-medium)"
              fillOpacity={1}
              fill="url(#suspiciousGrad)"
              strokeWidth={1.5}
              connectNulls
            />
            <Area
              type="monotone"
              dataKey="anomaly"
              stroke="var(--risk-critical)"
              fillOpacity={1}
              fill="url(#anomalyGrad)"
              strokeWidth={1.5}
              connectNulls
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
