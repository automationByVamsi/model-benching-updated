## ROVO PROMPT

Act as an AI solution architect and quality engineering mentor. I have been assigned to prepare a test dataset for our lab’s Analysis Agent, but I am new to this agent. I have 8 years of UI/API test automation experience and need a clear, practical explanation.

Search Confluence for the Analysis Agent’s requirements, architecture, design decisions, API contracts, user guides, examples, evaluation plans, and known limitations. Follow relevant linked pages. If multiple agents have similar names, identify the candidates and ask me which one is relevant before combining their information.

Prepare an evidence-based explanation covering:

1. Purpose and business problem
- Why was this agent built?
- Who uses it, and what decisions or tasks does it support?
- What does “analysis” mean in this agent’s context?
- What is in scope and out of scope?
- What does a successful result look like?

2. Inputs and source data
- What triggers the agent: a user request, API call, file upload, scheduled job, or something else?
- What inputs are required or optional? Include formats, fields, constraints, and examples.
- Where does the underlying data come from?
- What preprocessing, permissions, session context, or conversation history does it require?

3. End-to-end workflow
- Explain each stage from receiving the input to returning the final output.
- Describe agents/subagents, prompts, models, tools, retrieval, calculations, and validation where documented.
- Explain how it decides which tools to call and when to stop.
- Describe failures, retries, fallbacks, and human review.

4. APIs and dependencies
- List the APIs, tools, databases, and external services it uses.
- For each, explain its purpose, inputs, outputs, and documented contract.
- Include endpoint/method details where available, without exposing credentials.

5. Outputs and expected behaviour
- Describe the final output format and any intermediate artifacts.
- Explain citations, calculations, charts, structured fields, or recommendations, if applicable.
- Explain expected behaviour for incomplete data, ambiguity, unsupported requests, and service failures.

6. Information needed to prepare a test dataset
- Identify documented use cases and representative user requests.
- Explain what each test example should contain: user input, source data, context, expected result, supporting evidence, and any other required fields.
- Explain whether correctness means an exact answer, correct facts/calculations, or satisfaction of an evaluation rubric.
- Identify existing sample datasets, benchmarks, acceptance criteria, metrics, and known defects.
- Identify required coverage: normal cases, boundary cases, negative cases, multi-turn cases, and access restrictions where applicable.
- Explain how expected answers should be established and who should validate them.

7. Gaps and open questions
- List missing or contradictory information.
- Give me the specific questions I should ask the agent owner before preparing the dataset.

Start with a plain-English overview, then explain the workflow with one documented example. Finish with a compact table of dataset-relevant findings and open questions.

Cite the Confluence page link and relevant section for each major finding. Include page dates/version/status where available. Distinguish current implemented behaviour from proposals or roadmap items. Clearly label facts, inferences, and unknowns. Do not invent details or assume this agent works like a generic AI agent.

If no documented example exists, provide an explicitly labelled illustrative example. Do not create the full test dataset yet.


## GITHUB COPILOT PROMPT:

Act as a senior AI engineer and quality engineering mentor. I have been assigned to prepare a test dataset for the Analysis Agent in this repository. I have 8 years of UI/API test automation experience, but I am new to this agent.

Inspect the repository and explain its actual implementation in depth, using clear language and concrete examples. This is a read-only investigation: do not modify files, install dependencies, or execute the agent or external API calls. Do not expose secret values.

First read any repository instructions, README files, and architecture documentation. Then trace the relevant execution path through the code. Do not stop at a README summary. If this is a monorepo or contains multiple agents, identify which implementation is the Analysis Agent and explain how you identified it.

Cover the following:

1. Purpose and implementation status
- What problem does this agent solve, according to the repository?
- What use cases are implemented?
- Which parts are active, experimental, mocked, incomplete, or deprecated?
- Distinguish documented intent from behaviour supported by the code.

2. Repository map
- Identify the entry points and important files/modules.
- Explain their responsibilities and how they connect.
- Identify the framework, model configuration, prompts, tools, schemas, and configuration files.

3. Input contract
- How is the agent invoked: API, CLI, UI, job, or another agent?
- Identify request schemas, required/optional fields, defaults, validation, and constraints.
- Explain file/data inputs, session state, conversation history, and authentication context.
- Provide a minimal valid input example derived from the code or existing fixtures.

4. End-to-end execution
- Trace one request from entry point to final response.
- For each stage, explain the input, processing, tool/API calls, state changes, and output.
- Identify what is deterministic code and what is decided or generated by an LLM.
- Explain tool selection, branching, loops, stopping conditions, retries, timeouts, and fallbacks.
- Explain retrieval, data transformations, calculations, and output validation where implemented.

5. API and tool inventory
Create a table with:
- API/tool/service name
- Calling file and function
- Purpose
- Endpoint and HTTP method, if available
- Request fields
- Response fields consumed by the agent
- Authentication mechanism, without secret values
- Failure handling

Include databases, MCP tools, model calls, and other agents where applicable. If endpoints or tool definitions are configured externally, identify the configuration reference and mark unavailable details as unknown.

6. Output contract
- Identify the final response schema and intermediate artifacts.
- Explain structured fields, text, citations, charts, files, and streaming events where applicable.
- Show a representative output from existing examples/tests. If none exists, label any constructed example as illustrative.
- Explain how errors and partial results are returned.

7. Existing tests and evaluation
- Inspect tests, fixtures, sample requests, datasets, evaluation scripts, and metric configuration.
- Explain what is already verified and what remains uncovered.
- Identify known limitations or TODOs relevant to dataset preparation.
- Explain how evaluation data is loaded and what schema the evaluation runner requires, if one exists.

8. Implications for my test dataset
Based on the implementation, explain:
- What one dataset record should contain.
- Which source data, files, tool results, and conversation context must accompany a request.
- Which behaviours can use exact assertions and which need fact-based checks or a rubric.
- How to establish expected results independently of the agent’s generated answer.
- Which scenario categories deserve coverage.
- Whether live/changing data could make expected answers unstable.
- Any configuration, environment, model, prompt, or source-data versions that must be recorded for reproducible evaluation.
- What cannot be determined from this repository and must be confirmed with the agent owner.

For every major claim, cite the file path, relevant function/class, and line range where possible. Clearly separate verified behaviour, inference, and unknowns. Do not infer business requirements solely from function names, and do not assume all files are used at runtime.

Structure your response as:
A. Plain-English overview
B. Repository map
C. One complete request walkthrough
D. Input/output contracts
E. API/tool inventory
F. Dataset preparation requirements
G. Open questions for the agent owner

Explain unfamiliar concepts when they first appear. Prioritise the active execution path and dataset-relevant details. Do not create the full test dataset or recommend code changes yet.


##ROVO BY CLAUDE
You are briefing me on the "Analysis Agent" from our Confluence. I am an SDET who has just been asked to prepare its test dataset, and I know nothing about it yet. Make me fully clear on it, starting from zero.

Search across all our Confluence content on the Analysis Agent (design docs, architecture pages, requirements, decision records, meeting notes, runbooks, evaluation/test plans). Prefer the most recent, authoritative pages. If pages conflict, or archived pages disagree with current ones, use the current one and tell me what changed. Flag anything outdated.

Explain using exactly this structure:
1. WHAT it is: one plain-English paragraph.
2. WHY it exists: the business problem it solves, who asked for it, who its users are, and what happens today without it.
3. PROBLEM STATEMENT & SCOPE: what is in scope, what is explicitly out of scope, constraints, and what "done/success" looks like (any stated KPIs, accuracy targets, latency or cost limits).
4. HOW it works: the end-to-end flow as a numbered list of stages, one plain sentence each. For every stage say what goes in, what comes out, and whether it uses an LLM, a tool/API, or plain logic.
5. ARCHITECTURE / DIAGRAMS: describe any diagrams in words: components, how data flows between them, and the one or two things each diagram is really trying to convey.
6. INTEGRATIONS: every external system, API, MCP tool, database, knowledge source or other agent it calls or depends on, and what each one is used for. Mention any upstream data pipeline it relies on.
7. INPUTS: what a request to the agent looks like (who sends it, format, required vs optional fields), with a real example if one exists.
8. OUTPUTS: what the agent returns (format, fields, confidence scores, routing/escalation decisions, error or fallback responses), with a real example if one exists.
9. MODELS & PROMPTS: which LLM(s) are used, any guardrails, and where prompts are documented.
10. TESTING & EVALUATION SO FAR: any existing test plans, evaluation criteria, metrics, golden datasets, sample queries, known failure cases, or open bugs. Say plainly if none exist.
11. STATUS & PEOPLE: current status, go-live or release dates, environments (dev/test/prod), and the owners or SMEs I should talk to.
12. KEY TERMS: mini-glossary; expand every acronym.
13. OPEN QUESTIONS: anything unclear, contradictory or missing in the documentation that I should confirm with the team.
14. SOURCES & FRESHNESS: every page used, with its last-updated date.

Rules: be concise and concrete, and prefer real examples over abstract description. If something is not documented, write "Not documented" rather than guessing. Finish all sections before asking me anything.


## GH
#codebase Act as a senior engineer onboarding an SDET who must build the test dataset for this agent. Analyse the whole repository and explain it. For EVERY claim, cite the file path (and function/class name) it comes from. If you can't find something, say "Not found in code". Don't guess.

1. PURPOSE: what this agent does, in plain English, based on the README, docs and code.
2. REPO MAP: the top-level folders/files and what each one is responsible for.
3. ENTRY POINTS: how the agent is started or invoked (API endpoint, CLI, main.py, Makefile targets, scheduled job), with the exact command or route.
4. END-TO-END FLOW: trace one request from input to final output as a numbered list of stages. For each stage give the file and function, what it receives, what it returns, and whether it calls an LLM, a tool/API, or plain logic.
5. TECH STACK: frameworks (e.g. ADK, LangChain, FastAPI), key libraries, and the Python version.

#codebase Continue the analysis. Cite file paths for everything.

1. INPUT CONTRACT: the exact request/input schema (Pydantic models, JSON schema, function signatures). List every field, its type, whether it's required, allowed values/enums, and defaults. Show one realistic example input.
2. OUTPUT CONTRACT: the exact response/output schema, same level of detail, including confidence scores, status/routing fields and error responses. Show one realistic example output.
3. EXTERNAL CALLS: a table of every external API, MCP tool, database, LLM endpoint, or other agent/service called. Columns: name | file/function | what it's used for | request/response shape | how failures and timeouts are handled.
4. LLM USAGE: every place an LLM is called: model name, where the prompt lives, whether structured output or a response schema is enforced, temperature and other settings, and any guardrails.
5. CONFIG & ENV: every environment variable and config setting, and what it controls.


#codebase Continue. Focus on the logic that decides the agent's behaviour, because I need to design test data that exercises every path. Cite file paths.

1. DECISION POINTS: every branch, threshold, routing rule, score cutoff, retry, fallback and early exit, with the exact conditions (e.g. "if score < 0.4 → FAIL").
2. VALIDATION: what input validation exists, and what happens with missing, empty, malformed, or very large inputs.
3. ERROR HANDLING: what happens when an external call fails, an LLM returns invalid output, or a timeout occurs. Is the failure surfaced, retried, or silently swallowed?
4. HARDCODED ASSUMPTIONS: magic numbers, hardcoded IDs/paths, domain-specific enums or taxonomies.
5. From all of the above, list the distinct scenario categories a test dataset should cover (happy path, each routing outcome, each failure mode, edge cases).

#codebase Continue. Cite file paths.

1. EXISTING TESTS: list the test files, what they cover, and what is clearly NOT covered.
2. EXISTING DATA: any sample inputs, fixtures, mock responses, seed data, eval datasets, or golden files in the repo: location, format, size, and what they represent.
3. EVALUATION CODE: any eval scripts, metrics, LLM-as-judge setup, or scoring logic.
4. LOGGING/TRACING: what gets logged or traced per request (useful for checking results stage by stage).
5. GAPS: your honest assessment of what is missing for a solid test dataset.


## Prompt updated
I’m preparing to evaluate an Athena preprocessing pipeline and need a simple understanding of how it works.

Please inspect the relevant repositories and Confluence pages. Do not change any files or configuration.

Explain, in plain language:

1. What starts the preprocessing pipeline?
2. What are the main steps from Athena page to stored data?
3. What metadata does the LLM extract?
4. Where is the data stored in Spanner and Cloud Storage?
5. How does the knowledge agent use this data?
6. What tests, monitoring, or validation already exist?

For every answer:

- Cite the repository file path, function, or Confluence page.
- Clearly label it as Confirmed, Inferred, or Unknown.
- Do not guess or invent missing details.
- Do not include secrets or credentials.

Keep the response concise, ideally under two pages.

End with:

- The five most important things I still need to learn.
- The five most important questions I should ask the engineering team.