# Response Alignment - commands to run on the work laptop

Run everything from the **modelbench repo root**, on the branch
`feature/response-alignment-metric`. Stop at any step that fails and paste the
output back into the chat.

Status when this was written: `metrics.py` and `scoring.py` already replaced;
test file not yet added.

---

## 0. Confirm branch and what changed

```bash
git branch --show-current
git status
git diff --stat
```

Expected: only `src/modelbench/evaluation/metrics.py` and
`src/modelbench/evaluation/scoring.py` modified.

## 1. Review the diff (important - files were replaced wholesale)

The replacement files were transcribed from photos, so comment wording may
differ from the originals. Check that ONLY the Response Alignment lines changed.

```bash
git diff src/modelbench/evaluation/metrics.py
git diff src/modelbench/evaluation/scoring.py
```

Expected changes only:

- `metrics.py`: new `ResponseAlignment` import, new `"response_alignment"` entry,
  new `selected_metrics` body (skips `opt_in` metrics when `names is None`).
- `scoring.py`: new `agentic_frame()` function, new `elif kind == "agentic":`
  branch in `score_one`, new `elif METRICS[metric_name]["kind"] == "agentic":`
  branch in `score_run`.

If other lines show up (for example a reworded comment), undo just those parts
and keep the Response Alignment parts - answer `n` to the new lines and `y` to
the unwanted ones:

```bash
git checkout -p -- src/modelbench/evaluation/metrics.py
git checkout -p -- src/modelbench/evaluation/scoring.py
```

## 2. Pegasus has the metric (if this fails, STOP)

```bash
uv run python -c "from pegasus.metrics.agentic import ResponseAlignment; print('OK', ResponseAlignment)"
```

## 3. Existing tests still pass (before adding the new test file)

```bash
uv run --with pytest python -m pytest tests -q
```

Expected: the same "N passed" as before the change.

## 4. Add the new test file

This one command creates `tests/test_response_alignment.py`:

```bash
cat > tests/test_response_alignment.py <<'EOF'
"""Response Alignment wiring - metric registry and scoring.

No LLM calls: a fake council records what it was given and returns fixed
per-judge, per-row scores in the same shape as Pegasus LLMCouncil.
"""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from modelbench.evaluation.metrics import METRICS, selected_metrics
from modelbench.evaluation.scoring import score_one, score_run

RUN_CONFIG = SimpleNamespace(judge_temperature=0.0)


class FakeCouncil:
    """Stands in for LLMCouncil: records every evaluate() call."""

    def __init__(self, row_scores):
        self.row_scores = row_scores  # {"judge-name": [score per row]}
        self.calls = []

    def evaluate(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        first_judge = next(iter(self.row_scores.values()))
        return {"score": float(np.mean(first_judge)), "council_row_scores": self.row_scores}


def golden_set(with_background=False):
    data = pd.DataFrame({"question": ["How to add a support need?", "How to close an account?"]})
    if with_background:
        data["background"] = ["Give step-by-step instructions.", None]
    return data


OUTPUTS = [{"answer": "Step 1 ..."}, {"answer": "Go to Accounts ..."}]


# --- metric registry ---------------------------------------------------------

def test_default_selection_is_unchanged():
    # The existing model-swap / prompt-swap runs must score exactly what they did before.
    assert list(selected_metrics(None)) == ["hallucination", "answer_correctness", "toxicity", "bias"]


def test_response_alignment_runs_only_when_named():
    assert "response_alignment" not in selected_metrics(None)
    assert list(selected_metrics(("response_alignment",))) == ["response_alignment"]
    assert list(selected_metrics(("response_alignment", "hallucination"))) == [
        "response_alignment",
        "hallucination",
    ]


def test_response_alignment_spec():
    spec = METRICS["response_alignment"]
    assert spec["role"] == "primary"        # gated by Gate 2 when selected
    assert spec["larger_is_better"] is True  # 0-1 alignment, higher is better
    assert spec["kind"] == "agentic"
    assert spec["delta"] == 0.05             # comparison.py reads spec["delta"]
    assert "critical_threshold" not in spec  # not a safety metric


def test_unknown_metric_still_rejected():
    with pytest.raises(KeyError, match="unknown metrics"):
        selected_metrics(("not_a_metric",))


# --- score_run (batched, used in Step 3) ---------------------------------------

def test_score_run_sends_query_and_agent_response():
    council = FakeCouncil({"judge-a": [0.8, 0.4], "judge-b": [0.6, 0.2]})

    scores = score_run({"response_alignment": council}, golden_set(), OUTPUTS, RUN_CONFIG)

    args, kwargs = council.calls[0]
    frame = args[0]  # DataFrame passed positionally, not as text=
    assert list(frame.columns) == ["query", "agent_response"]
    assert frame["query"].tolist() == golden_set()["question"].tolist()
    assert frame["agent_response"].tolist() == ["Step 1 ...", "Go to Accounts ..."]
    assert kwargs == {"temperature": 0.0}
    # One score per input: median across judges, row by row.
    np.testing.assert_allclose(scores["response_alignment"], [0.7, 0.3])


def test_score_run_sends_background_when_golden_set_has_it():
    council = FakeCouncil({"judge-a": [0.9, 0.9], "judge-b": [0.9, 0.9]})

    score_run({"response_alignment": council}, golden_set(with_background=True), OUTPUTS, RUN_CONFIG)

    frame = council.calls[0][0][0]
    assert frame["background"].tolist() == ["Give step-by-step instructions.", ""]


# --- score_one (single row, used for judge variance in Step 4) ------------------

def test_score_one_sends_one_row_frame():
    council = FakeCouncil({"judge-a": [0.7], "judge-b": [0.7]})

    score = score_one(council, "response_alignment", golden_set().iloc[0], OUTPUTS[0], RUN_CONFIG)

    frame = council.calls[0][0][0]
    assert frame.to_dict("records") == [
        {"query": "How to add a support need?", "agent_response": "Step 1 ..."}
    ]
    assert isinstance(score, float)
    assert score == pytest.approx(0.7)


def test_score_one_blank_background_becomes_empty_string():
    council = FakeCouncil({"judge-a": [0.7]})

    score_one(council, "response_alignment", golden_set(with_background=True).iloc[1], OUTPUTS[1], RUN_CONFIG)

    frame = council.calls[0][0][0]
    assert frame["background"].tolist() == [""]


# --- existing metrics must be called exactly as before ------------------------

def test_existing_hallucination_call_is_unchanged():
    council = FakeCouncil({"judge-a": [0.1, 0.2]})

    score_run({"hallucination": council}, golden_set(), OUTPUTS, RUN_CONFIG)

    args, kwargs = council.calls[0]
    assert args == ()                                  # still text=... keyword call
    assert list(kwargs["text"].columns) == ["query", "text", "context"]
EOF
```

## 5. Run the tests

```bash
# New tests only - expect "9 passed"
uv run --with pytest python -m pytest tests/test_response_alignment.py -v

# Whole suite - expect previous count + 9
uv run --with pytest python -m pytest tests -q
```

## 6. Default runs unchanged, opt-in works (no model calls)

```bash
uv run modelbench --mode quick --dry-run
uv run modelbench --mode quick --metrics response_alignment hallucination --dry-run
```

Expected `metrics:` lines:

- first: `hallucination, answer_correctness, toxicity, bias` (no `response_alignment`)
- second: `response_alignment, hallucination`

## 7. Nothing else loops over every metric

```bash
grep -rn "METRICS" src/ | grep -v 'METRICS\['
```

Paste any output into the chat before committing.

## 8. Live smoke check (4 judge calls)

Confirms the real Pegasus accepts the call and that an aligned answer scores
higher than an off-topic one.

```bash
uv run python - <<'EOF'
from dotenv import load_dotenv; load_dotenv()
import pandas as pd
from modelbench.schemas.run_config import RunConfig
from modelbench.evaluation.scoring import build_council, score_one

config = RunConfig()
council = build_council("response_alignment", config)
row = pd.Series({"question": "How to add a support need?"})
good = {"answer": "Open the customer's Support Needs tab, select Amend, then Add, fill in the details and confirm."}
bad = {"answer": "Our branches open at 9am on weekdays."}
print("aligned answer  :", score_one(council, "response_alignment", row, good, config))
print("off-topic answer:", score_one(council, "response_alignment", row, bad, config))
EOF
```

Expected: aligned about 0.8-1.0, off-topic about 0.0-0.2. An error mentioning
`temperature` means the agentic branch needs a small tweak - paste it back.

## 9. Commit and push the branch

Only after steps 1-8 pass.

```bash
git add src/modelbench/evaluation/metrics.py src/modelbench/evaluation/scoring.py tests/test_response_alignment.py
git status
git commit -m "Add Pegasus ResponseAlignment as an opt-in agentic metric

- New 'response_alignment' metric (primary, higher is better, delta 0.05),
  scored only when named via --metrics; default runs unchanged.
- scoring: 'agentic' branch sends query/agent_response(/background) to the council.
- Tests with a fake council (no LLM calls)."
git push -u origin feature/response-alignment-metric
```

## Notes for the reviewers

- `delta` 0.05 is a starting value, pending threshold calibration.
- A judge failing on a row gives that row a `NaN` score. This already applies
  to every metric and is not introduced here - suggest a separate ticket.
- Making Response Alignment the default for agent runs comes with the agent-run
  input work (Part B), not this change.
