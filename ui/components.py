"""
HarnessLoop — UI Components
Premium Gradio Blocks interface with live updates, charts, and diff viewer.
"""

import os
import json
import time
import difflib
import gradio as gr
import plotly.graph_objects as go
from pathlib import Path

from orchestrator import Orchestrator, EvolutionState

# ── Shared State ─────────────────────────────────────────────────────────────

orchestrator = Orchestrator()

CSS_PATH = Path(__file__).parent / "styles.css"
IS_HF_SPACE = "SPACE_ID" in os.environ
HAS_GROQ_SECRET = bool(os.environ.get("GROQ_API_KEY"))

THEME_HEAD = """
<script>
(function () {
    const key = 'harnessloop-theme';
    
    function getPreferredTheme() {
        let saved = null;
        try {
            saved = localStorage.getItem(key);
        } catch (e) {}
        if (saved === 'light' || saved === 'dark') return saved;
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    window.applyTheme = function(theme) {
        console.log("Applying theme:", theme);
        try {
            document.documentElement.setAttribute('data-theme', theme);
            document.documentElement.classList.toggle('dark', theme === 'dark');
            if (document.body) {
                document.body.classList.toggle('dark', theme === 'dark');
            }
            try {
                localStorage.setItem(key, theme);
            } catch (e) {}
            
            // Update buttons in DOM
            updateButtons(theme);

            // Update URL search params
            const url = new URL(window.location);
            if (url.searchParams.get('__theme') !== theme) {
                url.searchParams.set('__theme', theme);
                window.history.replaceState({}, '', url);
            }
        } catch (e) {
            console.error("Error applying theme:", e);
        }
    };

    function updateButtons(theme) {
        document.querySelectorAll('.theme-toggle-btn').forEach(btn => {
            const choice = btn.getAttribute('data-theme-choice');
            const active = choice === theme;
            btn.classList.toggle('active', active);
            btn.setAttribute('aria-pressed', active ? 'true' : 'false');
        });
    }

    // Initialize early
    const initialTheme = getPreferredTheme();
    document.documentElement.setAttribute('data-theme', initialTheme);
    document.documentElement.classList.toggle('dark', initialTheme === 'dark');
    
    // Inject __theme query param so Gradio's Svelte frontend initializes with the correct theme
    try {
        const url = new URL(window.location);
        if (url.searchParams.get('__theme') !== initialTheme) {
            url.searchParams.set('__theme', initialTheme);
            window.history.replaceState({}, '', url);
        }
    } catch (e) {}

    // Use MutationObserver to update button states when Svelte renders the buttons
    try {
        const observer = new MutationObserver(() => {
            updateButtons(getPreferredTheme());
        });
        observer.observe(document.documentElement, { childList: true, subtree: true });
    } catch (e) {}

    // Prevent Gradio from shrink-wrapping tabs to form width on wide screens
    let layoutTimer = null;
    function stretchLayout() {
        clearTimeout(layoutTimer);
        layoutTimer = setTimeout(() => {
            document.querySelectorAll(
                '.main.fillable, .wrap, main.contain, .edu-tabs, .edu-tabs .tabitem, .edu-tabs .tabitem > .column, .edu-container, .playground-container'
            ).forEach((el) => {
                el.style.width = '100%';
                el.style.maxWidth = 'none';
                el.style.alignSelf = 'stretch';
            });
            document.querySelectorAll('.block.auto-margin').forEach((el) => {
                el.style.marginLeft = '0';
                el.style.marginRight = '0';
                el.style.width = '100%';
                el.style.maxWidth = 'none';
            });
        }, 50);
    }

    window.addEventListener('resize', stretchLayout);
    document.addEventListener('click', (event) => {
        if (event.target.closest('.tab-nav button, [role="tab"]')) {
            stretchLayout();
        }
    });
    window.addEventListener('load', stretchLayout);
    stretchLayout();
})();
</script>
"""

THEME_JS = """
console.log("HarnessLoop theme handler initialized.");
"""

HEADER_HTML = """
<div class="app-header">
    <div class="app-header-text">
        <h1 class="header-title">HarnessLoop</h1>
        <p class="header-subtitle">Self-evolving prompt optimization</p>
    </div>
    <div class="theme-toggle" id="theme-toggle" role="group" aria-label="Color theme">
        <button type="button" class="theme-toggle-btn" data-theme-choice="light"
                aria-label="Light mode" aria-pressed="false" onclick="window.applyTheme('light')">
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="12" cy="12" r="4"/>
                <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>
            </svg>
        </button>
        <button type="button" class="theme-toggle-btn" data-theme-choice="dark"
                aria-label="Dark mode" aria-pressed="false" onclick="window.applyTheme('dark')">
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
        </button>
    </div>
</div>
"""


HARNESS_EDU_HTML = """
<div class="edu-container">
    <div class="edu-hero">
        <span class="edu-module-badge">Module 1</span>
        <h2 class="edu-title">Harness Engineering</h2>
        <p class="edu-subtitle">Measure Before You Improve</p>
    </div>
    
    <div class="edu-grid">
        <div class="edu-column">
            <div class="edu-card">
                <h3>Short Description</h3>
                <p>Harness Engineering is the practice of building a testing and evaluation system around an AI application. Instead of guessing whether prompts or agents are good, we create repeatable tests and score their performance.</p>
            </div>
            
            <div class="edu-card">
                <h3>Why It Matters</h3>
                <p class="edu-highlight-text">Most AI systems fail because people only test them manually.</p>
                <p>Harness Engineering helps teams:</p>
                <ul class="edu-list">
                    <li><span class="check-icon">✅</span> <strong>Measure quality</strong> consistently</li>
                    <li><span class="check-icon">✅</span> <strong>Compare</strong> prompt versions</li>
                    <li><span class="check-icon">✅</span> <strong>Detect regressions</strong> automatically</li>
                    <li><span class="check-icon">✅</span> <strong>Track improvements</strong> over time</li>
                    <li><span class="check-icon">✅</span> <strong>Deploy</strong> with confidence</li>
                </ul>
            </div>
            
            <div class="edu-card accent-card">
                <h3>Key Takeaway</h3>
                <p class="takeaway-text"><strong>Harness Engineering does not improve the AI itself.</strong></p>
                <p>It creates the system that measures whether improvements are actually working.</p>
            </div>
        </div>
        
        <div class="edu-column">
            <div class="edu-card">
                <h3>How It Works</h3>
                
                <div class="edu-step">
                    <div class="step-num">Step 1</div>
                    <div class="step-content">
                        <strong>Define Goal</strong>
                        <div class="step-desc">Customer Support Bot (Target Accuracy: 85%)</div>
                    </div>
                </div>
                
                <div class="edu-step">
                    <div class="step-num">Step 2</div>
                    <div class="step-content">
                        <strong>Create Test Cases</strong>
                        <table class="edu-table">
                            <thead>
                                <tr>
                                    <th>Input</th>
                                    <th>Expected Output</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr><td>Refund request</td><td>Refund policy</td></tr>
                                <tr><td>Order status</td><td>Tracking details</td></tr>
                                <tr><td>Product issue</td><td>Troubleshooting steps</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <div class="edu-step">
                    <div class="step-num">Step 3</div>
                    <div class="step-content">
                        <strong>Run Evaluation</strong>
                        <div class="eval-versions">
                            <span class="eval-ver score-low">Prompt V1: 68%</span>
                            <span class="eval-ver score-mid">Prompt V2: 79%</span>
                            <span class="eval-ver score-high">Prompt V3: 87%</span>
                        </div>
                    </div>
                </div>
                
                <div class="edu-step">
                    <div class="step-num">Step 4</div>
                    <div class="step-content">
                        <strong>Analyze & Evolve (System Prompt Update)</strong>
                        <p>The harness detects specific prompt failures (like hallucinations, missing information, or wrong formatting). To fix these, the system automatically rewrites and refines the underlying <strong>System Prompt</strong> to incorporate specific rules patching those exact gaps.</p>
                        <div class="prompt-evolution-mini">
                            <div class="mini-prompt old-mini">
                                <span class="mini-tag">V1 Prompt</span>
                                <code>"You are a helpful customer support agent..."</code>
                            </div>
                            <div class="mini-arrow">➔</div>
                            <div class="mini-prompt new-mini">
                                <span class="mini-tag">V2 Prompt (Patched)</span>
                                <code>"You are a helpful support agent. Always verify order IDs..."</code>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="edu-card">
                <h3>Real World Example</h3>
                <p>Think of Harness Engineering like a software testing suite:</p>
                <div class="comparison-box">
                    <div class="comparison-item">
                        <span class="comp-label">Software</span>
                        <span class="comp-val">Unit Tests</span>
                    </div>
                    <div class="comparison-arrow">↔️</div>
                    <div class="comparison-item">
                        <span class="comp-label">AI System</span>
                        <span class="comp-val">Evaluation Harness</span>
                    </div>
                </div>
                <p style="margin-top: 12px; font-style: italic; text-align: center;">Without tests, you're guessing. With a harness, you're measuring.</p>
            </div>
        </div>
    </div>
</div>
"""

LOOP_EDU_HTML = """
<div class="edu-container">
    <div class="edu-hero">
        <span class="edu-module-badge">Module 2</span>
        <h2 class="edu-title">Loop Engineering</h2>
        <p class="edu-subtitle">Improve Until The Goal Is Reached</p>
    </div>
    
    <div class="edu-grid">
        <div class="edu-column">
            <div class="edu-card">
                <h3>Short Description</h3>
                <p>Loop Engineering is the process of repeatedly evaluating, analyzing, and improving an AI system until it achieves a desired outcome.</p>
                <div class="flow-comparison">
                    <div class="flow-type">
                        <strong>Traditional Prompting</strong>
                        <div class="flow-steps">Prompt ➔ Response</div>
                    </div>
                    <div class="flow-type active-flow">
                        <strong>Loop Engineering (Feedback Loop)</strong>
                        <div class="flow-steps">Prompt ➔ Evaluate ➔ Analyze ➔ Rewrite ➔ Repeat</div>
                    </div>
                </div>
            </div>
            
            <div class="edu-card">
                <h3>Why It Matters</h3>
                <p class="edu-highlight-text">Most AI applications stop after generating an answer.</p>
                <p>Modern agent systems:</p>
                <ul class="edu-list">
                    <li><span class="check-icon">✅</span> <strong>Reflect</strong> on mistakes</li>
                    <li><span class="check-icon">✅</span> <strong>Retry</strong> failures</li>
                    <li><span class="check-icon">✅</span> <strong>Improve prompts</strong> automatically</li>
                    <li><span class="check-icon">✅</span> <strong>Use evaluation feedback</strong></li>
                    <li><span class="check-icon">✅</span> <strong>Continue</strong> until objectives are met</li>
                </ul>
            </div>

            <div class="edu-card">
                <h3>Harness vs Loop</h3>
                <table class="comparison-table">
                    <thead>
                        <tr>
                            <th>Harness Engineering</th>
                            <th>Loop Engineering</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Measures quality</td>
                            <td>Improves quality</td>
                        </tr>
                        <tr>
                            <td>Creates evaluation framework</td>
                            <td>Uses evaluation results</td>
                        </tr>
                        <tr>
                            <td>Finds problems</td>
                            <td>Fixes problems</td>
                        </tr>
                        <tr>
                            <td>Testing system</td>
                            <td>Improvement system</td>
                        </tr>
                        <tr>
                            <td>Reports score</td>
                            <td>Raises score</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="edu-column">
            <div class="edu-card">
                <h3>Simple Example</h3>
                <div class="run-timeline">
                    <div class="timeline-step goal-step">
                        <span class="step-badge">Goal</span>
                        <span>Target Accuracy = 85%</span>
                    </div>
                    <div class="timeline-step">
                        <span class="step-badge initial">Initial</span>
                        <span>Accuracy = 62%</span>
                    </div>
                    <div class="timeline-step loop-step">
                        <span class="step-badge loop">Loop 1</span>
                        <span>Analyze Errors ➔ Modify Prompt ➔ Run Eval ➔ <strong>73%</strong></span>
                    </div>
                    <div class="timeline-step loop-step">
                        <span class="step-badge loop">Loop 2</span>
                        <span>Analyze Errors ➔ Improve Prompt ➔ Run Eval ➔ <strong>86%</strong></span>
                    </div>
                    <div class="timeline-step success-step">
                        <span class="step-badge success">End</span>
                        <span>Goal Reached. Loop Stops.</span>
                    </div>
                </div>
            </div>
            
            <div class="edu-card">
                <h3>Visual Representation</h3>
                <div class="ascii-diagram">
                    <pre>
      ┌──────────────┐
      │  Run Model   │
      └──────┬───────┘
             │
             ▼
   ┌► ┌──────────────┐
   │  │   Evaluate   │
   │  └──────┬───────┘
   │         │
   │         ▼
   │  ┌──────────────┐
   │  │    Good?     │
   │  └──────┬───────┘
   │         │ No
   │         ▼
   │  ┌──────────────┐
   │  │   Improve    │
   │  └──────┬───────┘
   │         │
   └─────────┘
                    </pre>
                </div>
            </div>
            
            <div class="edu-card accent-card">
                <h3>Key Takeaway</h3>
                <p class="takeaway-text"><strong>Harness Engineering tells you where you are.</strong></p>
                <p class="takeaway-text"><strong>Loop Engineering helps you get where you want to be.</strong></p>
            </div>
        </div>
    </div>
</div>
"""

PLAYGROUND_HERO_HTML = """
<div class="edu-hero">
    <span class="edu-module-badge">Module 3</span>
    <h2 class="edu-title">Playground</h2>
    <p class="edu-subtitle">Run the self-evolving prompt optimization loop</p>
</div>
"""


# ── Helper Functions ─────────────────────────────────────────────────────────

def get_score_class(score: float) -> str:
    if score >= 75:
        return "high"
    elif score >= 50:
        return "mid"
    return "low"


def get_score_color(score: float) -> str:
    if score == 0:
        return "#5a5a6e"  # Neutral gray for "not started"
    elif score >= 75:
        return "#10b981"
    elif score >= 50:
        return "#f59e0b"
    return "#ef4444"


def get_status_label(status: str) -> str:
    return {
        "idle": "Idle",
        "running": "Running",
        "evaluating": "Evaluating",
        "improving": "Improving",
        "target_reached": "Complete",
        "max_iterations": "Stopped",
        "error": "Error",
    }.get(status, status.replace("_", " ").title())


def get_status_class(status: str) -> str:
    if status in ("running", "evaluating", "improving"):
        return "status-running"
    elif status == "target_reached":
        return "status-complete"
    elif status in ("max_iterations", "idle"):
        return "status-stopped"
    return "status-error"


# ── Metric Card Builder ─────────────────────────────────────────────────────

def build_metric_html(value: str, label: str, color: str = "#818cf8") -> str:
    return f"""
    <div class="metric-card" style="text-align: center;">
        <div class="metric-value" style="color: {color};">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """


def build_logs_html(state: EvolutionState) -> str:
    """Build a scrolling terminal-like log view."""
    if not state.logs:
        return '<div class="log-panel text-muted">No activity yet. Start an evolution run to see logs.</div>'

    log_lines = []
    for line in state.logs:
        escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if "Error" in escaped or "error" in escaped.lower():
            log_lines.append(f'<div style="color: var(--danger); margin-bottom: 4px;">{escaped}</div>')
        elif "---" in escaped:
            log_lines.append(f'<div style="color: var(--text-primary); margin-bottom: 4px; font-weight: 500;">{escaped}</div>')
        else:
            log_lines.append(f'<div class="text-secondary" style="margin-bottom: 4px;">{escaped}</div>')

    return f'<div class="log-panel">{"".join(log_lines)}</div>'


# ── Chart Builder ────────────────────────────────────────────────────────────

def build_score_chart(state: EvolutionState) -> go.Figure:
    """Build a Plotly line chart of score progression."""
    fig = go.Figure()

    if state.iterations:
        iterations = [r.iteration for r in state.iterations]
        scores = [r.score for r in state.iterations]

        # Gradient fill area
        fig.add_trace(go.Scatter(
            x=iterations,
            y=scores,
            mode='lines',
            fill='tozeroy',
            fillcolor='rgba(113, 113, 122, 0.06)',
            line=dict(color='rgba(113, 113, 122, 0.3)', width=1.5, shape='spline'),
            showlegend=False,
            hoverinfo='skip',
        ))

        fig.add_trace(go.Scatter(
            x=iterations,
            y=scores,
            mode='lines+markers',
            line=dict(color='#52525b', width=2, shape='spline'),
            marker=dict(
                size=8,
                color=[get_score_color(s) for s in scores],
                line=dict(width=1.5, color='#fafafa'),
                symbol='circle',
            ),
            name='Score',
            hovertemplate='Iteration %{x}<br>Score: %{y:.1f}%<extra></extra>',
        ))

        fig.add_hline(
            y=state.target_score,
            line_dash="dash",
            line_color="rgba(113, 113, 122, 0.5)",
            line_width=1,
            annotation_text=f"Target: {state.target_score}%",
            annotation_position="top right",
            annotation_font=dict(color="#71717a", size=11),
        )
    else:
        # Empty state placeholder
        fig.add_annotation(
            text="Waiting for evolution to begin...",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(color="#a1a1aa", size=13),
        )

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, sans-serif", color="#71717a", size=12),
        margin=dict(l=50, r=20, t=20, b=50),
        height=220,
        xaxis=dict(
            title="Iteration",
            gridcolor='rgba(113, 113, 122, 0.12)',
            zeroline=False,
            dtick=1,
            title_font=dict(color="#a1a1aa"),
        ),
        yaxis=dict(
            title="Score (%)",
            gridcolor='rgba(113, 113, 122, 0.12)',
            zeroline=False,
            range=[0, 105],
            title_font=dict(color="#a1a1aa"),
        ),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor='#18181b',
            bordercolor='#3f3f46',
            font=dict(color='#fafafa'),
        ),
    )

    return fig


# ── Timeline Builder ────────────────────────────────────────────────────────

def build_timeline_html(state: EvolutionState) -> str:
    """Build the evolution timeline HTML."""
    if not state.iterations:
        if state.status in ("running", "evaluating", "improving"):
            return """
            <div class="empty-state">
                <div class="shimmer" style="height: 52px; border-radius: 8px; margin-bottom: 10px;"></div>
                <div class="shimmer" style="height: 52px; border-radius: 8px; opacity: 0.6;"></div>
                <p style="margin-top: 14px;">Preparing first evaluation...</p>
            </div>
            """
        return """
        <div class="empty-state">
            <p>Enter a goal and press <strong>Start Evolution</strong> to begin.</p>
        </div>
        """

    html = '<div class="timeline-container">'
    for r in state.iterations:
        score_cls = get_score_class(r.score)
        item_cls = "completed" if r.score >= state.target_score else "active"
        delay = (r.iteration - 1) * 0.15

        html += f"""
        <div class="timeline-item {item_cls}" style="animation-delay: {delay}s;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span class="text-primary" style="font-weight: 500; font-size: 0.9rem;">
                    Iteration {r.iteration}
                </span>
                <span class="score-badge score-badge-{score_cls}">
                    {r.score:.0f}%
                </span>
            </div>
            <div class="text-muted" style="display: flex; gap: 14px; font-size: 0.8rem;">
                <span>{r.passed_cases} passed</span>
                <span>{r.failed_cases} failed</span>
                <span>{r.evaluation_time:.1f}s</span>
            </div>
        """
        if r.reasoning:
            html += f"""
            <div class="text-secondary" style="margin-top: 8px; padding: 8px 12px;
                        background: var(--bg-tertiary); border-radius: 6px;
                        font-size: 0.8125rem; line-height: 1.5;">
                {r.reasoning}
            </div>
            """
        html += "</div>"

    # Active status indicator
    if state.status in ("running", "evaluating", "improving"):
        html += f"""
        <div class="timeline-item active" style="border-style: dashed;">
            <div class="status-running" style="font-size: 0.875rem;">
                {state.status_message}
            </div>
            <div class="text-muted" style="font-size: 0.8rem; margin-top: 4px;">
                {state.eval_progress}
            </div>
        </div>
        """

    html += "</div>"
    return html


# ── Reasoning Panel ─────────────────────────────────────────────────────────

def build_reasoning_html(state: EvolutionState) -> str:
    """Build the failure analysis and improvements panel."""
    if not state.iterations:
        return '<div class="empty-state"><p>Analysis will appear here after each evaluation.</p></div>'

    latest = state.iterations[-1]
    html = ""

    if latest.weaknesses:
        html += '<div class="section-title">Weaknesses</div>'
        for w in latest.weaknesses:
            html += f'<div class="reasoning-item">{w}</div>'

    if latest.improvements:
        html += '<div class="section-title" style="margin-top: 20px;">Improvements</div>'
        for imp in latest.improvements:
            html += f'<div class="improvement-item">{imp}</div>'

    if latest.failure_details:
        html += f"""
        <div class="section-title" style="margin-top: 20px;">
            Failed Cases ({len(latest.failure_details)})
        </div>
        """
        for detail in latest.failure_details[:5]:
            reasons_html = "".join(
                f"<li>{r}</li>" for r in detail.get("failure_reasons", [])
            )
            html += f"""
            <div style="padding: 10px 14px; margin-bottom: 6px;
                        background: var(--bg-tertiary); border: 1px solid var(--border-subtle);
                        border-radius: 6px; font-size: 0.8125rem;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span class="text-primary" style="font-weight: 500;">
                        #{detail['case_id']} — {detail['category']}
                    </span>
                    <span class="score-badge score-badge-{get_score_class(detail['score'])}">
                        {detail['score']}/100
                    </span>
                </div>
                <ul class="text-secondary" style="margin: 4px 0 0 16px; padding: 0;">
                    {reasons_html}
                </ul>
            </div>
            """

    if not html:
        html = '<div class="empty-state"><p>No failures detected — performance looks good.</p></div>'

    return html


# ── Prompt Diff Viewer ──────────────────────────────────────────────────────

def build_prompt_diff(state: EvolutionState) -> tuple[str, str]:
    """Return (old_prompt_html, new_prompt_html) for side-by-side view."""
    if not state.iterations:
        placeholder = '<div class="empty-state"><p>Prompt evolution will appear here.</p></div>'
        return placeholder, placeholder

    latest = state.iterations[-1]
    old_prompt = latest.previous_prompt or "(initial seed prompt)"
    new_prompt = latest.prompt

    # Build diff-highlighted HTML for the new prompt
    old_lines = old_prompt.splitlines()
    new_lines = new_prompt.splitlines()

    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=''))

    if len(diff) > 2:
        diff_html = ""
        for line in diff[2:]:  # Skip --- and +++ headers
            escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if line.startswith('+'):
                diff_html += f'<div class="diff-added">{escaped}</div>'
            elif line.startswith('-'):
                diff_html += f'<div class="diff-removed">{escaped}</div>'
            elif line.startswith('@@'):
                diff_html += f'<div class="text-muted" style="font-size: 0.75rem; padding: 4px 8px;">{escaped}</div>'
            else:
                diff_html += f'<div class="text-secondary" style="padding: 2px 8px; font-family: \'JetBrains Mono\', monospace; font-size: 0.8125rem;">{escaped}</div>'
    else:
        diff_html = '<div class="empty-state" style="padding: 20px;">No changes detected.</div>'

    old_html = f'<div class="prompt-viewer">{old_prompt.replace(chr(10), "<br>")}</div>'
    new_html = f'<div class="prompt-viewer" style="padding: 0; overflow: hidden;"><div style="max-height: 400px; overflow-y: auto; padding: 16px;">{diff_html}</div></div>'

    return old_html, new_html


# ── Discovery Screen ────────────────────────────────────────────────────────

def build_discovery_html(state: EvolutionState) -> str:
    """Build the final discovery screen."""
    if state.status not in ("target_reached", "max_iterations"):
        if state.status in ("running", "evaluating", "improving"):
            return """
            <div class="empty-state">
                <div class="status-running" style="margin-bottom: 6px;">Evolution in progress</div>
                <p>The system is optimizing the prompt.</p>
            </div>
            """
        return '<div class="empty-state"><p>Start an evolution to see results.</p></div>'

    is_target = state.status == "target_reached"
    title = "Target achieved" if is_target else "Maximum iterations reached"
    subtitle = (
        "Optimal prompt discovered."
        if is_target
        else f"Best score: {state.best_score:.0f}%"
    )

    # Gather improvements summary
    all_improvements = []
    for r in state.iterations:
        all_improvements.extend(r.improvements)
    improvements_html = "".join(
        f'<div class="improvement-item">{imp}</div>'
        for imp in all_improvements[-8:]  # Last 8
    )

    return f"""
    <div class="discovery-banner">
        <div class="text-primary" style="font-size: 1.125rem; font-weight: 600; margin-bottom: 4px;">{title}</div>
        <div class="text-secondary" style="margin-bottom: 20px;">{subtitle}</div>

        <div class="discovery-score">{state.best_score:.0f}%</div>
        <div class="text-muted" style="font-size: 0.8125rem; margin-bottom: 24px;">
            Final score · {len(state.iterations)} iteration(s)
        </div>

        <div style="text-align: left; margin-top: 20px;">
            <div class="section-title">Discovered prompt</div>
            <div class="prompt-viewer" style="margin-bottom: 16px;">{state.best_prompt}</div>
        </div>

        {f'''
        <div style="text-align: left; margin-top: 16px;">
            <div class="section-title">Key improvements</div>
            {improvements_html}
        </div>
        ''' if improvements_html else ''}
    </div>
    """


# ── Export Function ─────────────────────────────────────────────────────────

def export_results(state: EvolutionState) -> str:
    """Export evolution results as JSON string."""
    if not state.iterations:
        return "No evolution data to export."

    export_data = {
        "goal": state.goal,
        "final_score": state.best_score,
        "target_score": state.target_score,
        "total_iterations": len(state.iterations),
        "status": state.status,
        "best_prompt": state.best_prompt,
        "evolution_history": [
            {
                "iteration": r.iteration,
                "score": r.score,
                "passed": r.passed_cases,
                "failed": r.failed_cases,
                "reasoning": r.reasoning,
                "improvements": r.improvements,
                "weaknesses": r.weaknesses,
                "prompt": r.prompt,
            }
            for r in state.iterations
        ],
    }
    return json.dumps(export_data, indent=2)


# ── Event Handlers ──────────────────────────────────────────────────────────

def start_evolution(goal: str, target_score: float, api_key: str):
    """Start the evolution process."""
    if not goal.strip():
        return "Please enter a goal."

    if not api_key.strip() and not os.environ.get("GROQ_API_KEY"):
        if IS_HF_SPACE:
            return "Add GROQ_API_KEY in Space Settings → Repository secrets, then restart the Space."
        return "Please enter a Groq API key."

    target = float(target_score) if target_score else 85.0
    target = max(50, min(100, target))

    orchestrator.start(
        goal=goal.strip(),
        target_score=target,
        max_iterations=10,
        api_key=api_key.strip() or None,
    )
    return f"Evolution started: {goal.strip()}"


def stop_evolution():
    """Stop the evolution process."""
    orchestrator.stop()
    return "Evolution stopped."


def refresh_ui():
    """Refresh all UI components from orchestrator state."""
    state = orchestrator.get_state()

    # Metrics
    score_color = get_score_color(state.current_score)
    score_html = build_metric_html(
        f"{state.current_score:.0f}%", "Current Score", score_color
    )
    iteration_html = build_metric_html(
        str(state.current_iteration), "Iteration", "#818cf8"
    )
    best_color = get_score_color(state.best_score)
    best_html = build_metric_html(
        f"{state.best_score:.0f}%", "Best Score", best_color
    )
    target_html = build_metric_html(
        f"{state.target_score:.0f}%", "Target Score", "#6366f1"
    )

    status_label = get_status_label(state.status)
    status_cls = get_status_class(state.status)
    status_html = f"""
    <div class="metric-card" style="text-align: center;">
        <div class="metric-value {status_cls}" style="font-size: 1.25rem; font-family: Inter, sans-serif; font-weight: 500;">{status_label}</div>
        <div class="metric-label">Status</div>
    </div>
    """

    # Chart
    chart = build_score_chart(state)

    # Timeline
    timeline = build_timeline_html(state)

    # Reasoning
    reasoning = build_reasoning_html(state)

    # Prompt diff
    old_prompt, new_prompt = build_prompt_diff(state)

    # Discovery
    discovery = build_discovery_html(state)

    # Status message
    status_msg = state.status_message or "Ready."

    logs_html = build_logs_html(state)

    return (
        score_html,
        iteration_html,
        best_html,
        target_html,
        status_html,
        chart,
        timeline,
        reasoning,
        old_prompt,
        new_prompt,
        discovery,
        status_msg,
        logs_html,
    )


def do_export():
    """Export results."""
    state = orchestrator.get_state()
    return export_results(state)


# ── Build Gradio UI ─────────────────────────────────────────────────────────

def create_ui() -> tuple:
    """Build and return the Gradio Blocks interface + assets."""

    css = CSS_PATH.read_text() if CSS_PATH.exists() else ""

    with gr.Blocks(
        title="HarnessLoop — Self-Evolving AI",
        fill_width=True,
    ) as demo:

        gr.HTML(HEADER_HTML)

        with gr.Tabs(elem_classes=["edu-tabs"]):
            with gr.Tab("Harness Engineering"):
                gr.HTML(value=HARNESS_EDU_HTML)
            with gr.Tab("Loop Engineering"):
                gr.HTML(value=LOOP_EDU_HTML)
            with gr.Tab("Playground", elem_id="playground-tab"):
                with gr.Column(
                    elem_classes=["edu-container", "playground-container"],
                    min_width=0,
                    scale=1,
                ):
                    gr.HTML(PLAYGROUND_HERO_HTML)

                    with gr.Row(elem_classes=["playground-grid"]):
                        with gr.Column(
                            scale=1,
                            min_width=0,
                            elem_classes=["edu-column", "playground-column"],
                        ):
                            with gr.Column(elem_classes=["playground-panel"]):
                                gr.HTML('<h3 class="playground-card-title">Configuration</h3>')

                                goal_input = gr.Textbox(
                                    label="Goal",
                                    placeholder='e.g. "Create the best SaaS customer support agent"',
                                    lines=1,
                                    max_lines=3,
                                    elem_classes=["goal-input"],
                                )

                                with gr.Row():
                                    with gr.Column(scale=3, min_width=0, visible=not (IS_HF_SPACE and HAS_GROQ_SECRET)):
                                        api_key_input = gr.Textbox(
                                            label="Groq API key",
                                            placeholder="gsk_...",
                                            type="password",
                                            value="" if IS_HF_SPACE else os.environ.get("GROQ_API_KEY", ""),
                                            elem_classes=["goal-input"],
                                        )
                                    with gr.Column(scale=1, min_width=120):
                                        target_input = gr.Number(
                                            label="Target score",
                                            value=85,
                                            minimum=50,
                                            maximum=100,
                                            step=5,
                                            elem_classes=["goal-input"],
                                        )

                                with gr.Row():
                                    start_btn = gr.Button(
                                        "Start evolution",
                                        elem_classes=["start-btn"],
                                        scale=3,
                                    )
                                    stop_btn = gr.Button(
                                        "Stop",
                                        elem_classes=["stop-btn"],
                                        scale=1,
                                    )

                                with gr.Accordion("Activity log", open=False):
                                    logs_panel = gr.HTML(build_logs_html(EvolutionState()))

                                status_bar = gr.Markdown(
                                    "Ready. Enter a goal and press Start evolution.",
                                    elem_id="status-bar",
                                )

                        with gr.Column(
                            scale=1,
                            min_width=0,
                            elem_classes=["edu-column", "playground-column"],
                        ):
                            with gr.Column(elem_classes=["playground-panel", "playground-metrics"]):
                                gr.HTML('<h3 class="playground-card-title">Metrics</h3>')

                                with gr.Row(equal_height=True):
                                    score_card = gr.HTML(build_metric_html("0%", "Current score", "#a1a1aa"))
                                    iteration_card = gr.HTML(build_metric_html("0", "Iteration", "#a1a1aa"))
                                    best_card = gr.HTML(build_metric_html("0%", "Best score", "#a1a1aa"))
                                    target_card = gr.HTML(build_metric_html("85%", "Target", "#71717a"))
                                    status_card = gr.HTML(build_metric_html("—", "Status", "#a1a1aa"))

                            with gr.Tabs(elem_classes=["playground-tabs"]):
                                with gr.Tab("Evolution"):
                                    with gr.Row():
                                        with gr.Column(scale=3, min_width=0):
                                            gr.HTML('<div class="section-title">Score progression</div>')
                                            score_chart = gr.Plot(
                                                value=build_score_chart(EvolutionState()),
                                            )
                                        with gr.Column(scale=2, min_width=0):
                                            gr.HTML('<div class="section-title">Timeline</div>')
                                            timeline_panel = gr.HTML(
                                                build_timeline_html(EvolutionState()),
                                            )

                                with gr.Tab("Analysis"):
                                    reasoning_panel = gr.HTML(
                                        build_reasoning_html(EvolutionState()),
                                    )

                                with gr.Tab("Prompt evolution"):
                                    with gr.Row():
                                        with gr.Column(min_width=0):
                                            gr.HTML('<div class="section-title">Previous prompt</div>')
                                            old_prompt_panel = gr.HTML(
                                                '<div class="prompt-viewer text-muted">Awaiting first iteration...</div>'
                                            )
                                        with gr.Column(min_width=0):
                                            gr.HTML('<div class="section-title">Improved prompt</div>')
                                            new_prompt_panel = gr.HTML(
                                                '<div class="prompt-viewer text-muted">Awaiting first iteration...</div>'
                                            )

                                with gr.Tab("Discovery"):
                                    discovery_panel = gr.HTML(
                                        build_discovery_html(EvolutionState()),
                                    )
                                    with gr.Row():
                                        export_btn = gr.Button(
                                            "Export results",
                                            elem_classes=["export-btn"],
                                        )
                                    export_output = gr.Code(
                                        label="Exported JSON",
                                        language="json",
                                        visible=True,
                                    )

                # ── Event Wiring ────────────────────────────────────────

                # Start button
                start_btn.click(
                    fn=start_evolution,
                    inputs=[goal_input, target_input, api_key_input],
                    outputs=[status_bar],
                )

                # Stop button
                stop_btn.click(
                    fn=stop_evolution,
                    inputs=[],
                    outputs=[status_bar],
                )

                # Export button
                export_btn.click(
                    fn=do_export,
                    inputs=[],
                    outputs=[export_output],
                )

                # Auto-refresh timer (every 2 seconds)
                timer = gr.Timer(value=2)
                timer.tick(
                    fn=refresh_ui,
                    inputs=[],
                    outputs=[
                        score_card,
                        iteration_card,
                        best_card,
                        target_card,
                        status_card,
                        score_chart,
                        timeline_panel,
                        reasoning_panel,
                        old_prompt_panel,
                        new_prompt_panel,
                        discovery_panel,
                        status_bar,
                        logs_panel,
                    ],
                )

    return demo, css, THEME_JS, THEME_HEAD
