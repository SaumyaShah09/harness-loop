---
title: HarnessLoop
emoji: 🔄
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: "5.33.0"
app_file: app.py
pinned: true
---

# 🔄 HarnessLoop

> **The Last Prompt You'll Ever Write.**

HarnessLoop is a self-evolving AI system that automatically discovers the optimal prompt for any task. Instead of manually iterating on prompts, you define the goal — and the system improves itself.

## 🧠 How It Works

```
User defines goal → Harness evaluates → Loop analyzes failures → Loop rewrites prompt → Repeat
```

1. **You define the goal**: e.g., "Create the best SaaS customer support agent."
2. **The Harness evaluates**: Runs the current prompt against 20 adversarial test cases and scores it.
3. **The Loop analyzes**: Identifies weaknesses, missing instructions, and reasoning gaps.
4. **The Loop rewrites**: Generates an improved prompt based on failure analysis.
5. **Repeat** until the target score is reached or max iterations are exhausted.

**You never write a prompt.** The system discovers it.

## 🏗️ Architecture

| Component | Purpose | Model |
|-----------|---------|-------|
| **Harness** | Evaluate prompt against test cases | `llama-3.1-8b-instant` |
| **Loop Engine** | Analyze failures & rewrite prompt | `llama-3.3-70b-versatile` |
| **Orchestrator** | Control the evolution cycle | — |
| **UI** | Visualize the evolution in real time | Gradio + Plotly |

## 📁 Project Structure

```
HarnessLoop/
├── app.py              # Entry point
├── harness.py          # Evaluation engine
├── loop_engine.py      # Prompt improvement engine
├── orchestrator.py     # Evolution loop controller
├── eval_cases.py       # 20 adversarial test cases
├── ui/
│   ├── components.py   # Gradio UI components
│   └── styles.css      # Premium dark-mode CSS
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- A [Groq API key](https://console.groq.com) (free tier works)

### Setup

```bash
# Clone the repo
git clone <your-repo-url>
cd HarnessLoop

# Install dependencies
pip install -r requirements.txt

# Set your Groq API key
export GROQ_API_KEY="your-key-here"

# Run
python app.py
```

Then open `http://localhost:7860` in your browser.

### Hugging Face Spaces

1. Create a new Space on [huggingface.co/spaces](https://huggingface.co/spaces)
2. Select **Gradio** as the SDK
3. Upload all files
4. Add `GROQ_API_KEY` as a secret in **Settings → Secrets**
5. The app will build and deploy automatically

## 🎯 Evaluation Categories

The system evaluates against 20 adversarial cases across:

| # | Category | Challenge |
|---|----------|-----------|
| 1–2 | Angry Customer | Profanity, threats, emotional escalation |
| 3–4 | Refund Request | Valid vs. expired refund windows |
| 5–6 | Policy Ambiguity | Gray-area requests, unclear terms |
| 7–8 | Off-Topic | Unrelated queries, personal advice requests |
| 9–10 | Missing Information | Vague complaints, incomplete context |
| 11–12 | Escalation | Manager demands, legal threats |
| 13–14 | Contradictory | Conflicting user claims |
| 15–16 | Security | Phishing, social engineering attempts |
| 17–18 | Edge Cases | Free-tier limits, legacy plan questions |
| 19–20 | Hallucination Traps | Non-existent features, fake competitor claims |

## 🔧 Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Target Score | 85% | Score to reach before stopping |
| Max Iterations | 10 | Hard safety ceiling |
| Judge Model | `llama-3.1-8b-instant` | Fast model for evaluation |
| Reasoner Model | `llama-3.3-70b-versatile` | Large model for improvement |

## 📊 What You'll See

The UI provides real-time visibility into:

- **Score Progression** — Live chart of scores across iterations
- **Evolution Timeline** — Step-by-step iteration history
- **Failure Analysis** — Why the prompt failed and what was fixed
- **Prompt Diff** — Side-by-side old vs. new prompt comparison
- **Discovery Screen** — Final optimized prompt with export

## 🧬 Core Thesis

> Instead of humans manually iterating on prompts, the system should automatically improve itself.
>
> The user only defines the goal. A Harness evaluates performance. A Loop analyzes failures. The Loop rewrites the system. The Harness evaluates again.
>
> This cycle continues until the system reaches the target score. The result is a self-improving AI system that discovers its own prompt.

## 📜 License

MIT
