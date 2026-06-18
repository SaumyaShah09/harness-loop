"""
HarnessLoop — Loop Engine (Prompt Improver)
Analyzes failures and rewrites the system prompt using the larger 70b model.
"""

import os
import json
from dataclasses import dataclass, field

from typing import Optional
from groq import Groq

from harness import HarnessReport


# ── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class LoopResult:
    """Result of one improvement cycle."""
    new_prompt: str
    reasoning: str
    improvements: list[str] = field(default_factory=list)
    weaknesses_found: list[str] = field(default_factory=list)


# ── Loop Engine ──────────────────────────────────────────────────────────────

REASONER_MODEL = "llama-3.3-70b-versatile"

META_PROMPT = """You are an expert AI prompt engineer. Your job is to analyze why a customer support AI agent is failing and rewrite its system prompt to fix the failures.

## Context

You are improving a system prompt for a SaaS customer support agent. The prompt was evaluated against adversarial test cases and some cases failed.

## Current System Prompt
```
{current_prompt}
```

## Evaluation Score
{score}/100 (Target: {target_score}/100)

## Failed Cases Analysis
{failure_analysis}

## Your Task

1. **Identify Weaknesses**: What specific instructions are missing or unclear in the current prompt?
2. **Detect Patterns**: Are there categories of failures that share a root cause?
3. **Rewrite**: Create an improved system prompt that addresses ALL identified failures while maintaining existing strengths.

## Rules for the New Prompt
- Be SPECIFIC. Don't say "be professional" — say exactly HOW to handle each type of situation.
- Include explicit instructions for: escalation, refund policies, security verification, off-topic handling, missing information, and edge cases.
- Add guardrails against hallucination (never confirm features/products that don't exist).
- Add guardrails against social engineering (never share credentials or reset passwords to unverified emails).
- The prompt should be comprehensive but not excessively long (aim for 300-800 words).
- Preserve any instructions from the current prompt that are working well.

Respond ONLY with valid JSON in this exact format:
{{
    "new_prompt": "The complete rewritten system prompt...",
    "reasoning": "A 2-3 sentence explanation of the key changes made and why...",
    "improvements": ["improvement 1", "improvement 2", "..."],
    "weaknesses_found": ["weakness 1", "weakness 2", "..."]
}}"""


class LoopEngine:
    """Analyzes harness failures and rewrites the system prompt."""

    def __init__(self, api_key: Optional[str] = None, log_callback: Optional[callable] = None):
        self._api_key = api_key
        self._client = None
        self.log_callback = log_callback

    @property
    def client(self) -> Groq:
        """Lazily initialize the Groq client on first use."""
        if self._client is None:
            api_key = self._api_key or os.environ.get("GROQ_API_KEY")
            if not api_key:
                raise ValueError(
                    "Groq API Key is required. Please enter it in the UI."
                )
            self._client = Groq(api_key=api_key, max_retries=0, timeout=15.0)
        return self._client

    def _safe_chat_completion(self, model: str, messages: list, temperature: float, max_tokens: int, response_format: Optional[dict] = None, retries: int = 5) -> str:
        import re
        import time
        for attempt in range(retries):
            try:
                kwargs = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if response_format:
                    kwargs["response_format"] = response_format
                
                response = self.client.chat.completions.create(**kwargs)
                return response.choices[0].message.content or ""
            except Exception as e:
                err_msg = str(e)
                # Check for rate limit error
                if "429" in err_msg or "rate_limit" in err_msg.lower() or "rate limit" in err_msg.lower():
                    # Attempt to extract wait time from error message
                    match = re.search(r"try again in (\d+(\.\d+)?)s", err_msg.lower())
                    wait_time = float(match.group(1)) if match else 6.0
                    wait_time += 1.5  # Add buffer time
                    
                    msg = f"⚠️ Groq Rate Limit (429) hit on {model}. Waiting {wait_time:.1f}s before retrying (attempt {attempt+1}/{retries})...."
                    if self.log_callback:
                        self.log_callback(msg)
                    else:
                        print(msg)
                    time.sleep(wait_time)
                    continue
                
                # Check for fatal auth exceptions
                err_msg_lower = err_msg.lower()
                if any(term in err_msg_lower for term in ["api_key", "api key", "auth", "unauthorized", "credentials", "401", "403"]):
                    raise e
                
                # For generic temporary failures, retry after a short buffer
                if attempt < retries - 1:
                    time.sleep(2.0)
                    continue
                raise e

    def _format_failure_analysis(self, report: HarnessReport) -> str:
        """Format failure details into a readable analysis string."""
        if not report.failure_details:
            return "No failures detected."

        lines = []
        for i, detail in enumerate(report.failure_details, 1):
            lines.append(f"### Failure {i}: {detail['category']} (Case #{detail['case_id']})")
            lines.append(f"**Score**: {detail['score']}/100")
            lines.append(f"**Customer Message**: {detail['input_preview']}")
            lines.append(f"**Agent Response Preview**: {detail['agent_response_preview']}")
            if detail['failure_reasons']:
                lines.append("**Failure Reasons**:")
                for reason in detail['failure_reasons']:
                    lines.append(f"  - {reason}")
            lines.append("")

        return "\n".join(lines)

    def improve(
        self,
        current_prompt: str,
        report: HarnessReport,
        target_score: float = 85.0,
    ) -> LoopResult:
        """
        Analyze failures and generate an improved system prompt.

        Args:
            current_prompt: The current system prompt.
            report: The harness evaluation report.
            target_score: The target score to reach.

        Returns:
            LoopResult with the new prompt, reasoning, and improvements.
        """
        failure_analysis = self._format_failure_analysis(report)

        prompt_text = META_PROMPT.format(
            current_prompt=current_prompt,
            score=report.score,
            target_score=target_score,
            failure_analysis=failure_analysis,
        )

        try:
            raw = self._safe_chat_completion(
                model=REASONER_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a world-class prompt engineer. "
                            "Respond only with valid JSON."
                        ),
                    },
                    {"role": "user", "content": prompt_text},
                ],
                temperature=0.7,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )

            parsed = json.loads(raw or "{}")

            return LoopResult(
                new_prompt=parsed.get("new_prompt", current_prompt),
                reasoning=parsed.get("reasoning", "No reasoning provided."),
                improvements=parsed.get("improvements", []),
                weaknesses_found=parsed.get("weaknesses_found", []),
            )

        except json.JSONDecodeError as e:
            return LoopResult(
                new_prompt=current_prompt,
                reasoning=f"JSON parse error: {str(e)}. Keeping current prompt.",
                improvements=[],
                weaknesses_found=["Failed to parse Loop Engine response"],
            )
        except Exception as e:
            return LoopResult(
                new_prompt=current_prompt,
                reasoning=f"Loop Engine error: {str(e)}. Keeping current prompt.",
                improvements=[],
                weaknesses_found=[f"API error: {str(e)}"],
            )
