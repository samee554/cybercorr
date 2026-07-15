.PHONY: install dev demo

# ─── Install ───────────────────────────────────────────────────────────────────
# Install all Python and Node.js dependencies from scratch.
install:
	pip install -r requirements.txt
	cd frontend && npm install

# ─── Dev ───────────────────────────────────────────────────────────────────────
# Start both the FastAPI backend and the Vite frontend dev server concurrently.
# Requires: npm install -g concurrently  (or use: npx concurrently)
dev:
	cd frontend && npx concurrently \
		--names "backend,frontend" \
		--prefix-colors "cyan,magenta" \
		"cd .. && .venv/bin/uvicorn backend.main:app --reload --port 8000" \
		"npm run dev"

# ─── Demo ──────────────────────────────────────────────────────────────────────
# Print the 5-minute demo script from phases.md.
demo:
	@echo ""
	@echo "════════════════════════════════════════════════════════════════════"
	@echo "  CyberCorr — 5-Minute Demo Script"
	@echo "════════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "  0:00  Show dashboard, explain the 3 panels:"
	@echo "        - Left:   Threat Feed (real-time correlated alerts)"
	@echo "        - Center: Correlation Graph (entity relationships)"
	@echo "        - Right:  Quantum HNDL Panel + Fraud Heatmap"
	@echo ""
	@echo "  0:30  Show normal traffic flowing in — no alerts yet."
	@echo "        Point out the live WebSocket indicator (green dot, top right)."
	@echo ""
	@echo "  1:00  Inject Scenario 1 (Account Takeover):"
	@echo "        curl -s -X POST 'http://localhost:8000/simulate/inject?scenario=1'"
	@echo ""
	@echo "  1:30  Watch the correlated alert appear — demonstrate:"
	@echo "        '20 raw failed-login events collapsed into 1 high-confidence alert.'"
	@echo ""
	@echo "  2:00  Click the alert — show the AI threat brief:"
	@echo "        attack_pattern: Account Takeover via Credential Stuffing"
	@echo "        recommended_action: Block session, freeze account immediately."
	@echo "        false_positive_likelihood: ~8%"
	@echo ""
	@echo "  2:30  Switch to the Correlation Graph:"
	@echo "        Point out the new foreign IP node (185.220.101.42) — high degree."
	@echo "        'One IP connected to alice_kumar's user, device, and account transfer.'"
	@echo ""
	@echo "  3:00  Inject Scenario 2 (HNDL + Insider Threat):"
	@echo "        curl -s -X POST 'http://localhost:8000/simulate/inject?scenario=2'"
	@echo ""
	@echo "  3:30  Watch Quantum Panel light up — explain HNDL in 30 seconds:"
	@echo "        'Attackers steal encrypted data today, decrypt it when quantum"
	@echo "         computers are ready. NIST finalized post-quantum standards in 2024."
	@echo "         Banks need to detect this now. We do.'"
	@echo ""
	@echo "  4:00  Return to the alert modal — highlight false_positive_likelihood:"
	@echo "        'Traditional SIEM: 90%+ false positive rate.'"
	@echo "        'CyberCorr (because we correlate before alerting): ~8%.'"
	@echo ""
	@echo "  4:30  Architecture overview (30 seconds):"
	@echo "        Simulator → Correlator (time-window join + NetworkX graph)"
	@echo "        → Isolation Forest fraud score → Rule-based quantum score"
	@echo "        → OpenAI GPT-4o explanation → React SOC dashboard"
	@echo ""
	@echo "  5:00  Q&A ready."
	@echo ""
	@echo "════════════════════════════════════════════════════════════════════"
	@echo "  Inject commands (copy-paste ready):"
	@echo "    Scenario 1: curl -s -X POST 'http://localhost:8000/simulate/inject?scenario=1'"
	@echo "    Scenario 2: curl -s -X POST 'http://localhost:8000/simulate/inject?scenario=2'"
	@echo "    Scenario 3: curl -s -X POST 'http://localhost:8000/simulate/inject?scenario=3'"
	@echo "════════════════════════════════════════════════════════════════════"
	@echo ""
