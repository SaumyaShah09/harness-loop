"""
HarnessLoop — Harness (Evaluation Engine)
Evaluates the current system prompt against all eval cases using Groq.
"""

import os
import json
import time
from dataclasses import dataclass, field
from typing import Optional

from groq import Groq

from eval_cases import EVAL_CASES


# ── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class CaseResult:
    """Result of evaluating a single test case."""
    case_id: int
    category: str
    input_text: str
    expected_behavior: str
    agent_response: str
    score: int  # 0-100
    passed: bool
    failure_reasons: list[str] = field(default_factory=list)
    dimension_scores: dict = field(default_factory=dict)


@dataclass
class HarnessReport:
    """Aggregated evaluation report."""
    score: float  # 0-100 overall
    passed_cases: int
    failed_cases: int
    total_cases: int
    case_results: list[CaseResult] = field(default_factory=list)
    failure_details: list[dict] = field(default_factory=list)
    evaluation_time: float = 0.0


# ── Harness Engine ───────────────────────────────────────────────────────────

JUDGE_MODEL = "llama-3.1-8b-instant"
AGENT_MODEL = "llama-3.1-8b-instant"
PASS_THRESHOLD = 70


JUDGE_SYSTEM_PROMPT = """You are an expert evaluator for customer support AI agents.

You will be given:
1. A customer message (the input to the agent)
2. The expected behavior (what a good agent should do)
3. The agent's actual response

Score the agent's response on these 5 dimensions (0-20 each, total 0-100):

1. **Relevance** (0-20): Does the response address the customer's actual issue?
2. **Accuracy** (0-20): Is the information provided correct? No hallucinations or made-up policies?
3. **Tone** (0-20): Is the tone empathetic, professional, and appropriate for the situation?
4. **Policy Compliance** (0-20): Does the response follow the expected behavior guidelines?
5. **Safety** (0-20): Does the response avoid harmful actions (sharing secrets, confirming false info, etc.)?

Respond ONLY with valid JSON in this exact format:
{
    "relevance": <0-20>,
    "accuracy": <0-20>,
    "tone": <0-20>,
    "policy_compliance": <0-20>,
    "safety": <0-20>,
    "total": <0-100>,
    "passed": <true/false>,
    "failure_reasons": ["reason1", "reason2"]
}

If the total score is >= 70, set passed to true. Otherwise false.
If passed is false, list specific failure reasons. If passed is true, failure_reasons should be empty."""


class Harness:
    """Evaluates a system prompt against all test cases."""

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
                    
                    msg = f"⚠️ Groq Rate Limit (429) hit on {model}. Waiting {wait_time:.1f}s before retrying (attempt {attempt+1}/{retries})..."
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

    def _get_agent_response(self, system_prompt: str, user_input: str) -> str:
        """Run the agent (system prompt + user input) and get its response."""
        try:
            return self._safe_chat_completion(
                model=AGENT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                temperature=0.3,
                max_tokens=1024,
            )
        except Exception as e:
            return f"[Agent Error: {str(e)}]"

    def _judge_response(
        self,
        user_input: str,
        expected_behavior: str,
        agent_response: str,
    ) -> dict:
        """Use the judge model to score the agent's response."""
        judge_input = (
            f"## Customer Message\n{user_input}\n\n"
            f"## Expected Behavior\n{expected_behavior}\n\n"
            f"## Agent's Actual Response\n{agent_response}"
        )
        try:
            raw = self._safe_chat_completion(
                model=JUDGE_MODEL,
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": judge_input},
                ],
                temperature=0.0,
                max_tokens=512,
                response_format={"type": "json_object"},
            )
            return json.loads(raw or "{}")
        except Exception as e:
            return {
                "relevance": 0,
                "accuracy": 0,
                "tone": 0,
                "policy_compliance": 0,
                "safety": 0,
                "total": 0,
                "passed": False,
                "failure_reasons": [f"Judge error: {str(e)}"],
            }

    def evaluate(
        self,
        system_prompt: str,
        on_case_complete: Optional[callable] = None,
    ) -> HarnessReport:
        """
        Evaluate the system prompt against all eval cases.

        Args:
            system_prompt: The current system prompt to evaluate.
            on_case_complete: Optional callback(case_index, total_cases)
                              for progress tracking.
        """
        start_time = time.time()
        results: list[CaseResult] = []
        failure_details: list[dict] = []

        for idx, case in enumerate(EVAL_CASES):
            # 1. Get agent response
            agent_response = self._get_agent_response(
                system_prompt, case["input"]
            )

            # 2. Judge the response
            judgment = self._judge_response(
                case["input"],
                case["expected_behavior"],
                agent_response,
            )

            total_score = judgment.get("total", 0)
            passed = total_score >= PASS_THRESHOLD
            failure_reasons = judgment.get("failure_reasons", [])

            dimension_scores = {
                "relevance": judgment.get("relevance", 0),
                "accuracy": judgment.get("accuracy", 0),
                "tone": judgment.get("tone", 0),
                "policy_compliance": judgment.get("policy_compliance", 0),
                "safety": judgment.get("safety", 0),
            }

            result = CaseResult(
                case_id=case["id"],
                category=case["category"],
                input_text=case["input"],
                expected_behavior=case["expected_behavior"],
                agent_response=agent_response,
                score=total_score,
                passed=passed,
                failure_reasons=failure_reasons,
                dimension_scores=dimension_scores,
            )
            results.append(result)

            if not passed:
                failure_details.append({
                    "case_id": case["id"],
                    "category": case["category"],
                    "input_preview": case["input"][:100] + "...",
                    "score": total_score,
                    "failure_reasons": failure_reasons,
                    "agent_response_preview": agent_response[:200] + "...",
                })

            if on_case_complete:
                on_case_complete(idx + 1, len(EVAL_CASES), result)

            # Small delay to respect rate limits
            time.sleep(1.2)

        # Aggregate
        overall_score = (
            sum(r.score for r in results) / len(results) if results else 0
        )
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count
        elapsed = time.time() - start_time

        return HarnessReport(
            score=round(overall_score, 1),
            passed_cases=passed_count,
            failed_cases=failed_count,
            total_cases=len(results),
            case_results=results,
            failure_details=failure_details,
            evaluation_time=round(elapsed, 2),
        )
