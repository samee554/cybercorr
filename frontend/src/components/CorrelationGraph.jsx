import React, { useEffect, useState, useRef, useMemo, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { getGraph } from '../api/client';

export default function CorrelationGraph({ onNodeClick }) {
  const containerRef = useRef(null);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 800 });

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (let entry of entries) {
        const { width, height } = entry.contentRect;
        setDimensions({ width: width || 800, height: height || 800 });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    let active = true;
    const fetchGraph = async () => {
      try {
        const data = await getGraph();
        if (active) {
          setGraphData(data || { nodes: [], links: [] });
          setError(null);
          setLoading(false);
        }
      } catch (err) {
        console.error('Failed to fetch graph data:', err);
        if (active) setError(err);
      }
    };

    fetchGraph();
    const interval = setInterval(fetchGraph, 5000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  // Resolve CSS variable colors once for Canvas 2D API (which cannot parse var() strings)
  const resolvedColors = useMemo(() => {
    const cs = window.getComputedStyle(document.documentElement);
    return {
      user:     cs.getPropertyValue('--chart-2').trim(),
      ip:       cs.getPropertyValue('--chart-4').trim(),
      device:   cs.getPropertyValue('--chart-1').trim(),
      link:     cs.getPropertyValue('--bg-border').trim(),
      bgBase:   cs.getPropertyValue('--bg-base').trim(),
      textPri:  cs.getPropertyValue('--text-primary').trim(),
    };
  }, []);

  // Compute node degrees — memoized to avoid recompute on every render
  const degrees = useMemo(() => {
    const d = {};
    (graphData.links || []).forEach((link) => {
      const s = typeof link.source === 'object' ? link.source?.id : link.source;
      const t = typeof link.target === 'object' ? link.target?.id : link.target;
      if (s) d[s] = (d[s] || 0) + 1;
      if (t) d[t] = (d[t] || 0) + 1;
    });
    return d;
  }, [graphData.links]);

  const handleNodeClick = useCallback((node) => {
    if (onNodeClick) onNodeClick(node);
  }, [onNodeClick]);

  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          minHeight: '800px',
          color: 'var(--text-secondary)',
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--bg-border)',
          borderRadius: 'var(--radius-md)',
          fontFamily: 'var(--font-body)',
          fontSize: 'var(--text-sm)',
        }}
      >
        Loading entity graph...
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
          minHeight: '800px',
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
        Error loading graph: {error.message ?? 'Unknown error'}
      </div>
    );
  }

  if (graphData.nodes.length === 0) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          minHeight: '800px',
          color: 'var(--text-secondary)',
          border: '1px dashed var(--bg-border)',
          borderRadius: 'var(--radius-md)',
          padding: 'var(--space-6)',
        }}
      >
        <div
          style={{
            width: '100px',
            height: '100px',
            borderRadius: '50%',
            border: '2px dashed var(--bg-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: 'var(--space-4)',
          }}
        >
          <span style={{ fontSize: '32px' }}>🕸️</span>
        </div>
        <span style={{ fontFamily: 'var(--font-body)', fontSize: 'var(--text-sm)', textAlign: 'center' }}>
          Monitoring network... no entity graph yet
        </span>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        height: '100%',
        minHeight: '800px',
        backgroundColor: 'var(--bg-surface)',
        border: '1px solid var(--bg-border)',
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      <ForceGraph2D
        width={dimensions.width}
        height={dimensions.height}
        graphData={graphData}
        backgroundColor="transparent"
        linkColor={() => resolvedColors.link}
        linkWidth={1}
        nodeCanvasObject={(node, ctx, globalScale) => {
          // Guard against undefined coordinates during force layout warmup
          if (node.x == null || node.y == null) return;

          const degree = degrees[node.id] || 0;
          let size = 10;
          let color = resolvedColors.ip;

          if (node.type === 'user') {
            size = Math.min(30, 12 + degree * 2);
            color = resolvedColors.user;
          } else if (node.type === 'device') {
            size = 10;
            color = resolvedColors.device;
          }

          ctx.beginPath();
          if (node.type === 'user') {
            ctx.arc(node.x, node.y, size / 2, 0, 2 * Math.PI, false);
          } else if (node.type === 'device') {
            ctx.rect(node.x - size / 2, node.y - size / 2, size, size);
          } else {
            // Diamond for IP
            ctx.moveTo(node.x, node.y - size / 2);
            ctx.lineTo(node.x + size / 2, node.y);
            ctx.lineTo(node.x, node.y + size / 2);
            ctx.lineTo(node.x - size / 2, node.y);
            ctx.closePath();
          }

          ctx.fillStyle = color;
          ctx.fill();

          ctx.strokeStyle = resolvedColors.bgBase;
          ctx.lineWidth = 1;
          ctx.stroke();

          // Draw label when zoomed in enough
          if (globalScale > 1.2) {
            const label = node.label || node.id;
            const fontSize = Math.max(4, 9 / globalScale);
            ctx.font = `${fontSize}px 'JetBrains Mono', monospace`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = resolvedColors.textPri;
            ctx.fillText(label, node.x, node.y + size / 2 + 7 / globalScale);
          }
        }}
        onNodeClick={handleNodeClick}
        cooldownTicks={100}
      />
      {/* Legend */}
      <div
        style={{
          position: 'absolute',
          bottom: 'var(--space-2)',
          left: 'var(--space-2)',
          backgroundColor: 'var(--bg-base)',
          opacity: 0.9,
          padding: 'var(--space-2)',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid var(--bg-border)',
          pointerEvents: 'none',
          fontSize: 'var(--text-xs)',
          fontFamily: 'var(--font-body)',
          color: 'var(--text-secondary)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-1)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--chart-2)' }} />
          <span>User</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <span style={{ display: 'inline-block', width: '8px', height: '8px', transform: 'rotate(45deg)', backgroundColor: 'var(--chart-4)' }} />
          <span>IP</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <span style={{ display: 'inline-block', width: '8px', height: '8px', backgroundColor: 'var(--chart-1)' }} />
          <span>Device</span>
        </div>
      </div>
    </div>
  );
}
