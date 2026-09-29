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