# Response Alignment - commands to run on the work laptop

Run everything from the **modelbench repo root**, on the branch
`feature/response-alignment-metric`. Stop at any step that fails and paste the
output back into the chat.

Scope of this change (PR 1 of 2): the Response Alignment METRIC only - library
code in `src/modelbench`, its tests, one docstring line. No scripts, no
agent-specific code. Reading recorded agent runs is PR 2 (separate design).

Status: `metrics.py` and `scoring.py` already replaced. Every scoring check
below calls the real Pegasus judges through Cortex - no fake councils.

---

## 0. Confirm branch and what changed

```bash
git branch --show-current
git status
git diff --stat
```

Expected: only `src/modelbench/evaluation/metrics.py` and
`src/modelbench/evaluation/scoring.py` modified.

## 1. Review the diff (files were replaced wholesale)

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

If a reworded comment shows up as a change, undo just that part
(`y` = undo this hunk, `n` = keep it):

```bash
git checkout -p -- src/modelbench/evaluation/metrics.py
git checkout -p -- src/modelbench/evaluation/scoring.py
```

## 2. Pegasus has the metric (if this fails, STOP)

```bash
uv run python -c "from pegasus.metrics.agentic import ResponseAlignment; print('OK', ResponseAlignment)"
```

## 3. Existing tests still pass

```bash
uv run --with pytest python -m pytest tests -q
```

Expected: the same "N passed" as before the change.

## 4. Create the test file

```bash
cat > tests/test_response_alignment.py <<'EOF'
"""Response Alignment - metric registry and live scoring.

Registry tests run with every ``pytest`` (no model calls).

Live tests call the REAL Pegasus council through Cortex, so they only run when
asked for and when the Cortex credentials are available:

    MODELBENCH_LIVE=1 uv run --with pytest python -m pytest tests/test_response_alignment.py -v
"""

import os

import numpy as np
import pandas as pd
import pytest
from dotenv import load_dotenv

from modelbench.evaluation.metrics import METRICS, selected_metrics

load_dotenv()

LIVE = (
    os.getenv("MODELBENCH_LIVE") == "1"
    and bool(os.getenv("CORTEX_V2_API_KEY"))
    and bool(os.getenv("CORTEX_V2_URL"))
)
live = pytest.mark.skipif(
    not LIVE, reason="live judge calls: set MODELBENCH_LIVE=1 and the CORTEX_V2_* variables"
)

QUESTION = "How to add a support need?"
ALIGNED_ANSWER = (
    "Open the customer's profile, go to the 'Support Needs' tab and select 'Amend'. "
    "On the 'Customer support needs' screen select 'Add', fill in the details "
    "(F1 lists the available support needs), then select 'OK' to confirm."
)
OFF_TOPIC_ANSWER = "Our branches are open from 9am to 5pm on weekdays."


# --- metric registry (no model calls) -------------------------------------------

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


# --- live scoring with the real council (Cortex judges) ------------------------

@pytest.fixture(scope="module")
def council_and_config():
    from modelbench.evaluation.scoring import build_council
    from modelbench.schemas.run_config import RunConfig

    config = RunConfig()
    return build_council("response_alignment", config), config


@live
def test_live_score_one_ranks_aligned_above_off_topic(council_and_config):
    from modelbench.evaluation.scoring import score_one

    council, config = council_and_config
    row = pd.Series({"question": QUESTION})

    aligned = score_one(council, "response_alignment", row, {"answer": ALIGNED_ANSWER}, config)
    off_topic = score_one(council, "response_alignment", row, {"answer": OFF_TOPIC_ANSWER}, config)

    print(f"\naligned={aligned:.3f}  off_topic={off_topic:.3f}")
    assert 0.0 <= off_topic <= 1.0 and 0.0 <= aligned <= 1.0
    assert aligned > off_topic


@live
def test_live_score_run_gives_one_score_per_input(council_and_config):
    from modelbench.evaluation.scoring import score_run

    council, config = council_and_config
    data = pd.DataFrame({"question": [QUESTION, QUESTION]})
    outputs = [{"answer": ALIGNED_ANSWER}, {"answer": OFF_TOPIC_ANSWER}]

    scores = score_run({"response_alignment": council}, data, outputs, config)["response_alignment"]

    print(f"\nper-input scores={scores}")
    assert scores.shape == (2,)
    assert not np.isnan(scores).any()          # every judge scored every row
    assert ((scores >= 0.0) & (scores <= 1.0)).all()
    assert scores[0] > scores[1]
EOF
```

## 5. Document the optional `background` column (library users need to know)

In `src/modelbench/loaders.py`, inside the `load_dataset` docstring, find:

```
    Optional columns:
        reference_answer
        stratum
```

and add one line so it reads:

```
    Optional columns:
        reference_answer
        stratum
        background        (intended behaviour / requirements, used by response_alignment)
```

## 6. Run the tests

```bash
# Normal run - no judge calls. Expect "4 passed, 2 skipped" for this file.
uv run --with pytest python -m pytest tests/test_response_alignment.py -v

# Live run - real Cortex judges (about 6 judge calls, takes a minute or two).
# Expect "6 passed". -s prints the actual scores.
MODELBENCH_LIVE=1 uv run --with pytest python -m pytest tests/test_response_alignment.py -v -s

# Whole suite - expect previous count + 4 passed (+2 skipped)
uv run --with pytest python -m pytest tests -q
```

If a live test errors with something about `temperature`, paste it back - the
agentic branch then needs a small tweak.

## 7. Default runs unchanged, opt-in works (no model calls)

```bash
uv run modelbench --mode quick --dry-run
uv run modelbench --mode quick --metrics response_alignment hallucination --dry-run
```

Expected `metrics:` lines:

- first: `hallucination, answer_correctness, toxicity, bias` (no `response_alignment`)
- second: `response_alignment, hallucination`

## 8. Nothing else loops over every metric

```bash
grep -rn "METRICS" src/ | grep -v 'METRICS\['
```

Paste any output into the chat before committing.

## 9. Commit and push the branch

Only after steps 1-8 pass.

```bash
git add src/modelbench/evaluation/metrics.py src/modelbench/evaluation/scoring.py \
        src/modelbench/loaders.py tests/test_response_alignment.py
git status
git commit -m "Add Pegasus ResponseAlignment as an opt-in agentic metric

- New 'response_alignment' metric (primary, higher is better, delta 0.05),
  scored only when named via --metrics; default runs unchanged.
- scoring: 'agentic' branch sends query/agent_response(/background) to the council.
- loaders: document the optional 'background' golden-set column.
- Tests: registry checks + live judge checks (MODELBENCH_LIVE=1)."
git push -u origin feature/response-alignment-metric
```

## Notes for the reviewers

- `delta` 0.05 is a starting value, pending threshold calibration.
- A judge failing on a row gives that row a `NaN` score. This already applies
  to every metric and is not introduced here - suggest a separate ticket.
- Reading recorded agent runs (any agent, standard record format) is PR 2;
  agent-specific trace conversion stays outside the package.

# ROVO prompt
You are helping a QA engineer (SDET) who is new to Google Cloud Storage (GCS) and
Google Cloud Spanner build a test strategy for our knowledge preprocessing pipeline
(hive-knowledge-preprocessing), which feeds the HIVE Knowledge Agent.

Search all Confluence pages about this pipeline (design docs, ADRs, runbooks,
onboarding, incident/postmortem pages) and answer in the structure below. For every
point, cite the source page title + link. If something isn't documented, say
"NOT DOCUMENTED". Don't guess.

1. End-to-end flow: every stage from source fetch (Athena) → parsing → LLM metadata
   tagging → graph build → upload to GCS → load into Spanner → consumption by the
   Knowledge Agent. For each stage: input, output, trigger, and owner/service.
2. GCS details: bucket names per environment (dev/test/prod), folder/object naming
   convention, file formats, versioning/overwrite policy, lifecycle/retention rules,
   who writes and who reads, service accounts/IAM roles involved.
3. Spanner details: instance/database names per environment, table list with
   columns, primary keys, interleaved tables, indexes, foreign keys, and how
   JSON/graph data maps to rows. Include any DDL or schema diagrams.
4. Load semantics: full refresh vs incremental/upsert, how deletes of removed
   pages are handled, idempotency (what happens if the load runs twice),
   transactions/batching and mutation limits, and how GCS→Spanner is triggered
   (Dataflow, Cloud Function, Cloud Run job, script, scheduler?).
5. Orchestration and scheduling: how and how often the pipeline runs, dependencies
   between stages, retries, partial-failure handling, and resume/manifest behaviour.
6. How the Knowledge Agent queries Spanner: example queries, which tables/fields it
   depends on, and latency/freshness expectations.
7. Non-functional requirements: data volumes (pages, rows, file sizes), SLAs,
   freshness targets, cost limits, security/PII handling, and encryption.
8. Monitoring and observability: logs, metrics, alerts, dashboards, and data-quality
   checks that already exist.
9. Known issues, past incidents, open risks, and edge cases called out in docs.
10. Existing testing: any test plans, test environments, emulator usage, test
    data sets, or acceptance criteria already written.

End with a short "Gaps & open questions" list a tester should raise with the dev team.


# Github Prompt - 1
@workspace I'm an SDET designing tests for this repo. Describe the code; do not
modify anything. Be concise and factual, and cite file paths and function names.

PART A: Structure
1. Directory tree (2-3 levels) with a one-line purpose per folder/key file.
2. Entry points (main.py, Makefile targets, CLI args, env vars, config files)
   and how each stage is invoked.
3. External dependencies: GCP libraries (google-cloud-storage, google-cloud-spanner,
   etc.), LLM clients, and MCP tools, with versions from requirements/pyproject.

# Github Prompt - 2
@workspace PART B: GCS and Spanner code paths
1. Every function that reads/writes GCS: bucket/path construction, file formats,
   overwrite behaviour, error handling/retries.
2. Every function that touches Spanner: how the client/session is created, the DDL or
   schema definitions, insert vs insert_or_update vs replace vs DML, batch sizes,
   transaction boundaries, and how deletes/stale rows are handled.
3. The exact mapping from pipeline output (page JSON / graph.json nodes & edges)
   to Spanner tables/columns.
4. How credentials, project IDs, and environments are configured.
5. Is the Spanner emulator or a GCS fake used anywhere (tests, docker-compose)?

# Github Prompt - 3
@workspace PART C: Testability
1. Existing tests: framework, location, what they cover, fixtures/mocks used.
2. Where the pipeline validates data (Pydantic models, schema checks, manifests)
   and where it silently skips or swallows errors.
3. Idempotency/resume logic and anything that depends on ordering or timing.
4. Functions that are hard to test in isolation (hard-coded paths, global clients,
   no dependency injection) and suggest seams.
Output as a table: Area | File:Function | Behaviour | Test risk.


#Github prompt - 4
@workspace Show me, verbatim, (1) the full contents of the Liquibase changeset
20260903_0900__ka-knowledge-graph-schema.sql, and (2) the Makefile targets related
to the Spanner emulator (setup/start/migrate/stop) with the commands they run.
Also list the exact enum/status values used for page_since, page_audit, and job
(e.g., COMPLETED, RUNNING, SUCCESS, FAILED, load_type values).


#Github prompt - 5 
@workspace I'm an SDET setting up this repo to run LOCALLY on my Mac against the
Spanner emulator, so I can test the incremental pipeline safely. Do NOT modify any
files — only read the repo (Makefile, README.md, docs/, pyproject.toml, scripts/,
src/integrations/spanner/, src/core/config.py, tests/conftest.py, .env.example if
present) and give me exact, copy-paste steps. Cite the file each step comes from.

1. Prerequisites: exact tools and versions needed (Python/uv, Docker or gcloud
   emulator, Liquibase or whatever applies the DDL, gcloud CLI, certs). How to
   install/verify each on macOS.
2. Emulator: the exact Makefile targets for setup/start/migrate/stop and the
   commands they run. Which image/port, how the instance and database are created,
   and how the Liquibase changeset 20260903_0900__ka-knowledge-graph-schema.sql is
   applied. How to confirm the tables and knowledge_graph property graph exist.
3. .env for local: a complete list of variables I must set for a local run, with
   safe values that guarantee NOTHING is written to real GCP:
   SPANNER_EMULATOR_HOST, PROJECT_ID/SPANNER_INSTANCE/DATABASE_ID for the emulator,
   WRITE_TO_BUCKET, WRITE_TO_SPANNER, SAVE_LOCAL, LOCAL_OUTPUT_DIR, ROOT_PAGE_ID,
   Athena and Cortex settings. Flag any variable that, if left at its default,
   would hit real INT/PROD resources.
4. GCS locally: is there any supported way to run without real buckets (e.g.
   WRITE_TO_BUCKET=false + SAVE_LOCAL=true)? What features break when
   WRITE_TO_BUCKET=false (deletes/purge, repair_inbound_links, _load_stored_result)?
   Would the google-cloud-storage client honour STORAGE_EMULATOR_HOST
   (fake-gcs-server) given how GCSClient is built in gcloud_utils.py?
5. Running: exact commands to (a) start the API locally, (b) trigger an initial
   load for ONE specific root page ID only, (c) trigger an incremental run,
   (d) check job status. Include curl examples or the bruno/ collection names.
   Also: how to run the executor for only one root instead of all ATHENA_PAGES.
6. Querying the emulator: how to run ad-hoc SQL against it (gcloud spanner
   databases execute-sql with emulator config, or a small Python snippet using
   the repo's get_database()).
7. Reset: how to wipe the emulator data and re-apply the schema between test runs.
8. Known pitfalls: REST vs gRPC transport with the emulator, CA bundle
   (lbg-root-bundle.crt), Cortex auth (make full-pipeline), ATHENA_MCP_URL /
   SSL_VERIFY not in Settings, and anything the README warns about.

Finish with a single numbered checklist I can follow top to bottom.


## Setup prompt
@workspace Additional questions, read-only, cite files:
A. Can initial/incremental runs be scoped to a page that is NOT a top-level
   business-area root (e.g. a child "test area" page several levels deep)?
   How does subtree filtering work (tree path prefix?) and will pages outside
   that subtree be ignored entirely, including during incremental /find polling
   and archive/delete handling?
B. Does the pipeline skip or treat differently pages that are draft, unpublished,
   restricted, or deleted (page_metadata.draft_state / unpublished / deleted)?
   Where is that decided?
C. Is there any exclusion mechanism (deny-list of page IDs/paths, tag, page_type)
   that would stop the deployed INT pipeline from ingesting a specific subtree?
D. For links from a test page to pages OUTSIDE the scoped subtree, what
   target_source / is_broken / dependency_page_id values get written?



# ROVO prompting
Open the Confluence page "Incremental Update Integration Scenario Tests" (HIVE Knowledge
Agent / preprocessing pipeline). For EACH of the 16 scenarios (a–p), give me verbatim:
scenario ID and title, preconditions/setup, steps to execute, expected results (Spanner,
GCS, audit/watermark), pass/fail criteria, and any current status, owner, or notes
(e.g. passed/failed/blocked, defects raised). Present as one table per scenario. Also list
any scenarios on the page beyond these 16, and include the page's last-updated date and author.