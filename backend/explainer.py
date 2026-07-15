"""AI-driven threat intelligence explanation generator using Groq."""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone

from groq import Groq

from backend.config import AI_MAX_TOKENS, AI_MODEL, MAX_CONCURRENT_AI_CALLS
from backend.models import AlertExplanation, CorrelatedAlert

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a senior bank security analyst AI assistant. You analyze correlated "
    "cybersecurity and fraud alerts and produce clear, actionable threat intelligence "
    "briefs for security analysts. Be specific, concise, and direct. Avoid jargon "
    "where possible. Always output valid JSON and nothing else — no preamble, "
    "no markdown backticks."
)


def get_template_fallback(alert: CorrelatedAlert) -> AlertExplanation:
    """Build a static fallback explanation from alert details without calling the LLM API."""
    cyber_types = ", ".join(set(e.event_type for e in alert.cyber_events))
    tx_count = len(alert.transaction_events)

    if alert.quantum_risk_score >= 70:
        risk_reason = f"Critical quantum HNDL threat detected with rules weight of {alert.quantum_risk_score}."
        recommended_action = "Initiate quantum security incident response and isolate compromised keys."
        attack_pattern = "Harvest Now, Decrypt Later (HNDL)"
        false_positive_likelihood = 5
    elif alert.overall_risk in ("CRITICAL", "HIGH"):
        risk_reason = f"High correlation score of {alert.correlation_score:.2f} with transaction anomaly score of {alert.anomaly_score:.2f}."
        recommended_action = "Suspend user account immediately and call user to verify recent transactions."
        attack_pattern = "Account Takeover (ATO)"
        false_positive_likelihood = 15
    elif alert.overall_risk == "MEDIUM":
        risk_reason = f"Moderate security alignment found with correlation score {alert.correlation_score:.2f}."
        recommended_action = "Review recent login events and flag account for monitoring."
        attack_pattern = "Credential Abuse"
        false_positive_likelihood = 40
    else:
        risk_reason = "Low score correlation indicating normal operational telemetry."
        recommended_action = "No action required. Maintain normal monitoring."
        attack_pattern = "Unclassified Activity"
        false_positive_likelihood = 80

    threat_summary = (
        f"Correlated security alert for user {alert.user_id} involving cyber events ({cyber_types}) "
        f"and {tx_count} transaction events."
    )

    return AlertExplanation(
        threat_summary=threat_summary,
        risk_level=alert.overall_risk,
        risk_reason=risk_reason,
        attack_pattern=attack_pattern,
        recommended_action=recommended_action,
        false_positive_likelihood=false_positive_likelihood,
        generated_at=datetime.now(timezone.utc),
    )


def build_user_prompt(alert: CorrelatedAlert) -> str:
    """Build the prompt describing the alert details for the user role message."""
    cyber_by_type = {}
    for e in alert.cyber_events:
        cyber_by_type.setdefault(e.event_type, []).append(e.ip_address)

    cyber_lines = []
    for etype, ips in cyber_by_type.items():
        unique_ips = ", ".join(set(ips))
        cyber_lines.append(f"- {len(ips)}x {etype} from IP(s): {unique_ips}")
    cyber_summary = "\n".join(cyber_lines) if cyber_lines else "No cyber events."

    tx_lines = []
    for t in alert.transaction_events:
        tx_lines.append(f"- {t.tx_type}: ${t.amount:.2f} to {t.destination} at {t.timestamp.isoformat()}")
    tx_summary = "\n".join(tx_lines) if tx_lines else "No transactions."

    return (
        f"Analyze this correlated security alert and return a JSON object.\n\n"
        f"User: {alert.user_id}\n"
        f"Cyber Events (last 5 min):\n"
        f"{cyber_summary}\n\n"
        f"Transactions (last 5 min):\n"
        f"{tx_summary}\n\n"
        f"ML Anomaly Score: {alert.anomaly_score} (range: -1 anomaly to +1 normal)\n"
        f"Quantum Risk Score: {alert.quantum_risk_score}/100\n\n"
        f"Return this exact JSON structure:\n"
        f"{{\n"
        f'  "threat_summary": "<2 sentences, plain English>",\n'
        f'  "risk_level": "<CRITICAL|HIGH|MEDIUM|LOW>",\n'
        f'  "risk_reason": "<one sentence explaining risk level>",\n'
        f'  "attack_pattern": "<name of attack pattern this resembles>",\n'
        f'  "recommended_action": "<specific action for analyst right now>",\n'
        f'  "false_positive_likelihood": <integer 0-100>\n'
        f"}}\n"
    )


class Explainer:
    """Generates LLM-based threat intelligence explanations for security alerts using Groq."""

    def __init__(self) -> None:
        """Initialize the Explainer cache, semaphore, and Groq client."""
        self._cache: dict[str, AlertExplanation] = {}
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_AI_CALLS)

        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            self.client = Groq(api_key=api_key)
            logger.info("Groq Explainer initialized with API key.")
        else:
            self.client = None
            logger.warning("GROQ_API_KEY environment variable not found. Explainer will default to fallback templates.")

    async def explain(self, alert: CorrelatedAlert) -> AlertExplanation:
        """Generate an alert explanation, using cache or calling Groq with fallback on failure."""
        if alert.alert_id in self._cache:
            logger.info(f"Returning cached explanation for alert {alert.alert_id}")
            return self._cache[alert.alert_id]

        if not self.client:
            logger.info(f"No Groq client configured. Generating fallback template for alert {alert.alert_id}.")
            explanation = get_template_fallback(alert)
            self._cache[alert.alert_id] = explanation
            return explanation

        async with self._semaphore:
            try:
                user_prompt = build_user_prompt(alert)

                logger.info(f"Calling Groq API for alert {alert.alert_id} using model {AI_MODEL}...")

                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=AI_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=AI_MAX_TOKENS,
                    temperature=0,
                )

                result_text = response.choices[0].message.content or ""
                parsed_json = self._parse_json_defensive(result_text)

                explanation = AlertExplanation(
                    threat_summary=parsed_json.get("threat_summary", ""),
                    risk_level=parsed_json.get("risk_level", alert.overall_risk),
                    risk_reason=parsed_json.get("risk_reason", ""),
                    attack_pattern=parsed_json.get("attack_pattern", ""),
                    recommended_action=parsed_json.get("recommended_action", ""),
                    false_positive_likelihood=int(parsed_json.get("false_positive_likelihood", 50)),
                    generated_at=datetime.now(timezone.utc),
                )

                self._cache[alert.alert_id] = explanation
                logger.info(f"Successfully generated Groq explanation for alert {alert.alert_id}.")
                return explanation

            except Exception as exc:
                logger.error(f"Groq API error for alert {alert.alert_id}: {exc}")

        # Fallback to local template explanation on failure
        explanation = get_template_fallback(alert)
        self._cache[alert.alert_id] = explanation
        return explanation

    def _parse_json_defensive(self, text: str) -> dict[str, object]:
        """Parse JSON response defensively, stripping any backticks and finding the outer brackets."""
        cleaned = text.strip()
        # Remove markdown backticks block if present
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if len(lines) >= 2:
                # Remove starting ```json or ```
                if lines[0].startswith("```"):
                    lines = lines[1:]
                # Remove ending ```
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError(f"No JSON object found in response: {text[:100]}")

        return json.loads(cleaned[start:end])


EXPLAINER = Explainer()
