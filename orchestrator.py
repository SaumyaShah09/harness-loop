"""
HarnessLoop — Orchestrator
Controls the Harness → Loop evolution cycle with state tracking.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Optional, Callable

from harness import Harness, HarnessReport
from loop_engine import LoopEngine, LoopResult


# ── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class IterationResult:
    """Result of a single evolution iteration."""
    iteration: int
    score: float
    passed_cases: int
    failed_cases: int
    total_cases: int
    prompt: str
    previous_prompt: Optional[str] = None
    reasoning: Optional[str] = None
    improvements: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    failure_details: list[dict] = field(default_factory=list)
    evaluation_time: float = 0.0
    timestamp: float = 0.0


@dataclass
class EvolutionState:
    """Full state of the evolution process."""
    goal: str = ""
    iterations: list[IterationResult] = field(default_factory=list)
    current_prompt: str = ""
    current_score: float = 0.0
    best_score: float = 0.0
    best_prompt: str = ""
    target_score: float = 85.0
    max_iterations: int = 10
    status: str = "idle"  # idle | running | evaluating | improving | target_reached | max_iterations | error
    status_message: str = ""
    current_iteration: int = 0
    eval_progress: str = ""  # e.g., "Evaluating case 5/20..."
    error: Optional[str] = None
    logs: list[str] = field(default_factory=list)


# ── Seed Prompt Generator ────────────────────────────────────────────────────

def generate_seed_prompt(goal: str) -> str:
    """Generate a deliberately minimal seed prompt from the user's goal."""
    return (
        f"You are a helpful assistant. Your goal: {goal}. "
        f"Help users with their requests."
    )


# ── Orchestrator ─────────────────────────────────────────────────────────────

class Orchestrator:
    """Controls the Harness → Loop evolution cycle."""

    def __init__(self):
        self.harness = Harness()
        self.loop_engine = LoopEngine()
        self.state = EvolutionState()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def get_state(self) -> EvolutionState:
        """Thread-safe state access."""
        with self._lock:
            return self.state

    def _update_state(self, **kwargs):
        """Thread-safe state update."""
        with self._lock:
            for key, value in kwargs.items():
                setattr(self.state, key, value)

    def _add_log(self, message: str):
        """Thread-safe logging helper."""
        timestamp = time.strftime('%H:%M:%S')
        with self._lock:
            self.state.logs.append(f"[{timestamp}] {message}")

    def start(
        self,
        goal: str,
        target_score: float = 85.0,
        max_iterations: int = 10,
        api_key: Optional[str] = None,
        on_update: Optional[Callable] = None,
    ):
        """
        Start the evolution process in a background thread.

        Args:
            goal: The user's goal description.
            target_score: Target score to reach (0-100).
            max_iterations: Maximum number of iterations.
            api_key: Optional Groq API key.
            on_update: Optional callback fired after each state change.
        """
        if self.state.status == "running":
            return

        self._stop_event.clear()
        seed_prompt = generate_seed_prompt(goal)
        
        self.harness = Harness(api_key=api_key, log_callback=self._add_log)
        self.loop_engine = LoopEngine(api_key=api_key, log_callback=self._add_log)

        self.state = EvolutionState(
            goal=goal,
            current_prompt=seed_prompt,
            target_score=target_score,
            max_iterations=max_iterations,
            status="running",
            status_message="Initializing evolution...",
        )
        self._add_log(f"🧬 Starting prompt evolution loop for goal: '{goal}'")
        self._add_log(f"🌱 Initial seed prompt generated.")

        self._thread = threading.Thread(
            target=self._run_loop,
            args=(on_update,),
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        """Stop the evolution process."""
        self._stop_event.set()
        self._update_state(
            status="idle",
            status_message="Evolution stopped by user.",
        )
        self._add_log("⏹ Evolution loop stopped by user request.")

    def _run_loop(self, on_update: Optional[Callable] = None):
        """Main evolution loop (runs in background thread)."""
        try:
            iteration = 0

            while iteration < self.state.max_iterations:
                if self._stop_event.is_set():
                    break

                iteration += 1
                self._update_state(
                    current_iteration=iteration,
                    status="evaluating",
                    status_message=f"Iteration {iteration}: Evaluating prompt...",
                    eval_progress=f"Starting evaluation (0/{20})...",
                )
                self._add_log(f"⚙️ Iteration {iteration}: Starting evaluation cycle...")

                if on_update:
                    on_update()

                # ── Step 1: Evaluate ─────────────────────────────────
                def on_case_complete(done, total, result=None):
                    self._update_state(
                        eval_progress=f"Evaluating case {done}/{total}..."
                    )
                    if result:
                        status_icon = "✅" if result.passed else "❌"
                        status_text = "Passed" if result.passed else "Failed"
                        self._add_log(
                            f"  {status_icon} [{done}/{total}] {result.category} -> {status_text} "
                            f"(Score: {result.score}/100)"
                        )
                        if result.failure_reasons:
                            self._add_log(f"    └─ Reasons: {', '.join(result.failure_reasons)}")
                    if on_update:
                        on_update()

                report: HarnessReport = self.harness.evaluate(
                    self.state.current_prompt,
                    on_case_complete=on_case_complete,
                )

                # Save previous prompt for diff
                previous_prompt = self.state.current_prompt

                self._add_log(f"📊 Iteration {iteration} Evaluation Complete. Score: {report.score:.1f}% (Passed: {report.passed_cases}/{report.total_cases})")

                # ── Step 2: Check if target reached ──────────────────
                if report.score >= self.state.target_score:
                    result = IterationResult(
                        iteration=iteration,
                        score=report.score,
                        passed_cases=report.passed_cases,
                        failed_cases=report.failed_cases,
                        total_cases=report.total_cases,
                        prompt=self.state.current_prompt,
                        previous_prompt=previous_prompt if iteration > 1 else None,
                        failure_details=report.failure_details,
                        evaluation_time=report.evaluation_time,
                        timestamp=time.time(),
                    )

                    with self._lock:
                        self.state.iterations.append(result)
                        self.state.current_score = report.score
                        if report.score > self.state.best_score:
                            self.state.best_score = report.score
                            self.state.best_prompt = self.state.current_prompt
                        self.state.status = "target_reached"
                        self.state.status_message = (
                            f"🎯 Target reached! Score: {report.score}% "
                            f"(target: {self.state.target_score}%) "
                            f"in {iteration} iteration(s)."
                        )
                    self._add_log(f"🎯 Target reached ({report.score:.1f}% >= {self.state.target_score:.1f}%). Stopping.")

                    if on_update:
                        on_update()
                    return

                # ── Step 3: Improve ──────────────────────────────────
                self._update_state(
                    status="improving",
                    status_message=(
                        f"Iteration {iteration}: Score {report.score}% — "
                        f"Analyzing {report.failed_cases} failures..."
                    ),
                )
                self._add_log(f"🧠 Iteration {iteration}: Invoking Loop Engine (prompt optimizer) to resolve {report.failed_cases} failures...")
                if on_update:
                    on_update()

                loop_result: LoopResult = self.loop_engine.improve(
                    self.state.current_prompt,
                    report,
                    target_score=self.state.target_score,
                )

                self._add_log(f"💡 Loop Engine completed reasoning: {loop_result.reasoning}")
                for imp in loop_result.improvements:
                    self._add_log(f"  └─ Improvement: {imp}")
                for weak in loop_result.weaknesses_found:
                    self._add_log(f"  └─ Weakness found: {weak}")

                # ── Step 4: Record iteration ─────────────────────────
                result = IterationResult(
                    iteration=iteration,
                    score=report.score,
                    passed_cases=report.passed_cases,
                    failed_cases=report.failed_cases,
                    total_cases=report.total_cases,
                    prompt=loop_result.new_prompt,
                    previous_prompt=self.state.current_prompt,
                    reasoning=loop_result.reasoning,
                    improvements=loop_result.improvements,
                    weaknesses=loop_result.weaknesses_found,
                    failure_details=report.failure_details,
                    evaluation_time=report.evaluation_time,
                    timestamp=time.time(),
                )

                with self._lock:
                    self.state.iterations.append(result)
                    self.state.current_prompt = loop_result.new_prompt
                    self.state.current_score = report.score
                    if report.score > self.state.best_score:
                        self.state.best_score = report.score
                        self.state.best_prompt = loop_result.new_prompt
                    self.state.status = "running"
                    self.state.status_message = (
                        f"Iteration {iteration} complete: {report.score}% → "
                        f"Improved prompt. Moving to iteration {iteration + 1}..."
                    )
                self._add_log(f"⚙️ Iteration {iteration} complete. System prompt optimized.")

                if on_update:
                    on_update()

                # Brief pause between iterations
                time.sleep(1.0)

            # ── Max iterations reached ───────────────────────────────
            if not self._stop_event.is_set():
                self._update_state(
                    status="max_iterations",
                    status_message=(
                        f"⚠️ Maximum iterations ({self.state.max_iterations}) "
                        f"reached. Best score: {self.state.best_score}%."
                    ),
                )
                self._add_log(f"⚠️ Maximum iterations ({self.state.max_iterations}) reached. Ending loop. Best score: {self.state.best_score:.1f}%")
                if on_update:
                    on_update()

        except Exception as e:
            self._update_state(
                status="error",
                status_message=f"❌ Error: {str(e)}",
                error=str(e),
            )
            self._add_log(f"❌ Error encountered: {str(e)}")
            if on_update:
                on_update()
