"""Score recorded Knowledge Agent traces with Response Alignment (real judges).

A first look at an agentic model swap: the same questions asked of the agent
with model A and with model B, each final answer judged by the Pegasus
ResponseAlignment council. This is NOT the full modelbench verdict (no noise
register, bootstrap or gates) - that comes when agent runs are wired into the
pipeline.

Folder layout:

    traces/A/*.json   agent runs with model A (baseline)
    traces/B/*.json   agent runs with model B (candidate)

Run from the repo root:

    uv run python scripts/score_agent_traces.py --traces traces
    uv run python scripts/score_agent_traces.py --traces traces --out results/ra_traces.csv
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv


def read_trace(path: Path) -> dict:
    """Pull the question, the user-facing answer and the model from one trace."""
    trace = json.loads(path.read_text(encoding="utf-8"))
    events = trace.get("raw_events", [])

    # The question is the "query" of the first event that has one.
    question = next(
        e["output"]["query"]
        for e in events
        if isinstance(e.get("output"), dict) and "query" in e["output"]
    )

    # agentOutput is a JSON string. The user sees answer + caveats + recommended
    # actions, so all of it is judged.
    agent_output = json.loads(trace["agentOutput"])
    answer = agent_output.get("answer", "")
    if agent_output.get("caveats"):
        answer += "\n\nCaveats:\n" + "\n".join(f"- {c}" for c in agent_output["caveats"])
    if agent_output.get("recommended_actions"):
        answer += "\n\nRecommended actions:\n" + "\n".join(
            f"- {a}" for a in agent_output["recommended_actions"]
        )

    models = sorted({e["modelVersion"] for e in events if e.get("modelVersion")})
    return {"file": path.name, "question": question.strip(), "answer": answer, "models": models}


def read_arm(folder: Path) -> list[dict]:
    files = sorted(folder.glob("*.json"))
    if not files:
        raise SystemExit(f"No trace files found in {folder}")
    return [read_trace(f) for f in files]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--traces", type=Path, default=Path("traces"), help="Folder with A/ and B/")
    parser.add_argument("--out", type=Path, help="Optional CSV with one row per trace")
    args = parser.parse_args()

    load_dotenv()  # Cortex credentials, same as the modelbench CLI
    logging.basicConfig(level="INFO", format="%(levelname)s  %(message)s")

    from modelbench.evaluation.scoring import build_council, score_run
    from modelbench.schemas.run_config import RunConfig

    config = RunConfig()
    council = build_council("response_alignment", config)

    rows = []
    for arm in ("A", "B"):
        traces = read_arm(args.traces / arm)

        models = sorted({m for t in traces for m in t["models"]})
        print(f"\nArm {arm}: {len(traces)} traces, model(s) {models}")
        if len(models) != 1:
            print(f"  WARNING: arm {arm} should use exactly one model")
        judged = [m for m in models if m in config.judge_models]
        if judged:
            raise SystemExit(f"Arm {arm} model {judged} is also a judge - pick different judges")

        data = pd.DataFrame({"question": [t["question"] for t in traces]})
        outputs = [{"answer": t["answer"]} for t in traces]
        scores = score_run({"response_alignment": council}, data, outputs, config)

        for trace, score in zip(traces, scores["response_alignment"]):
            rows.append(
                {
                    "arm": arm,
                    "file": trace["file"],
                    "model": ", ".join(trace["models"]),
                    "question": trace["question"],
                    "response_alignment": round(float(score), 3),
                }
            )

    table = pd.DataFrame(rows)
    pd.set_option("display.max_colwidth", 60)
    pd.set_option("display.width", 200)
    print("\nPer trace:")
    print(table.to_string(index=False))

    print("\nPer arm (mean over all traces):")
    print(table.groupby("arm")["response_alignment"].agg(["count", "mean", "min", "max"]).round(3))

    # Paired by question: average per question per arm, then B - A.
    per_question = table.pivot_table(
        index="question", columns="arm", values="response_alignment", aggfunc="mean"
    )
    if {"A", "B"} <= set(per_question.columns):
        paired = per_question.dropna(subset=["A", "B"])
        paired = paired.assign(B_minus_A=(paired["B"] - paired["A"]).round(3))
        print("\nPer question (B - A; negative means B is less aligned):")
        print(paired.round(3).to_string())
        print(f"\nMean B - A over {len(paired)} shared question(s): {paired['B_minus_A'].mean():+.3f}")
        missing = per_question.index.difference(paired.index)
        if len(missing):
            print(f"Questions answered by only one arm (not compared): {list(missing)}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(args.out, index=False)
        print(f"\nSaved {args.out}")

    print(
        "\nNote: a first look only. The ship decision needs several runs per question "
        "and the full modelbench pipeline (noise, bootstrap, gates)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
