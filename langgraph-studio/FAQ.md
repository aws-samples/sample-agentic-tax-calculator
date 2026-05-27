# Agentic Tax Calculator - Demo FAQ

---

## LangGraph

**Q: Why LangGraph over other frameworks?**
We chose LangGraph because your team was already evaluating it. The good news is the core concepts - tools, orchestration, shared state, checkpointing - are framework-agnostic. If you wanted to switch to something else down the road, the tools and business logic don't change. You'd just rewire the orchestration layer.

**Q: How does LangGraph handle state between steps?**
LangGraph uses a SharedState dictionary that flows through the graph. Each workflow step reads what it needs from state, does its work, and writes results back. The orchestrator passes state between steps automatically. For persistence, it uses a checkpointer - in our case DynamoDB - so if the workflow crashes mid-calculation, it can resume from the last checkpoint.

**Q: How does the parallel execution work in LangGraph?**
After the Business step completes, the graph fans out to three steps simultaneously - Income, Expense, and Asset. LangGraph handles this natively through conditional edges that return a list of next nodes. All three must complete before the Tax step runs. This is system-level parallelism - the graph structure enforces it, not the LLM.

**Q: Is LangGraph hard to maintain?**
LangGraph has a steeper learning curve than some alternatives. The graph-based approach is powerful but adds complexity - you're defining nodes, edges, conditional routing, and state schemas. For a small team early in their AI journey, it's worth knowing that simpler options exist. One I'd mention is AWS Strands - it's a much simpler framework that does the same core things. You define tools, the agent reasons about which to call, and it handles the orchestration. The concepts are the same, the code is just less verbose. Something to evaluate as you build.

**Q: Can we use LangGraph with AgentCore Runtime?**
Yes, LangGraph works well in AgentCore Runtime. The Runtime doesn't care what framework you use - it's just hosting a container. LangGraph, Strands, CrewAI, custom code - all work. The MCP server is the interface, and the framework is an implementation detail inside.

---

## Architecture / Infrastructure

**Q: Why not just use our K8s cluster?**
You absolutely can. The code runs the same either way - one env var switches between AgentCore and K8s. The tradeoff is: AgentCore gives you managed session isolation, auto-scaling, and observability out of the box. K8s gives you control and uses your existing CI/CD pipelines. If your team has a mature K8s practice, K8s is a reasonable choice. AgentCore is the faster path if you want to skip the infrastructure work.

**Q: What happens when the token expires mid-calculation?**
The token is passed through in code - it never enters the LLM's context window. If it expires during a calculation, the specific tool call that uses it will get a clear auth error from GraphQL. The workflow will fail at that step with a specific error message, not silently return wrong data. In production, you'd add token refresh logic in the passthrough client.

**Q: How do you handle PII in the LLM context?**
PII is filtered before it reaches the LLM. The PII Pre-Filter scans for SIN numbers, bank accounts, addresses, and names. If it finds PII that can be redacted, it redacts it. If the input is mostly PII and can't be safely redacted, the request is blocked entirely. The LLM never sees raw PII. Same filter runs before storing anything in memory.

**Q: What if the tax calculation is wrong?**
Two layers of protection. First, the tax engine is deterministic - it's pure math using CRA bracket data, not LLM guessing. Same input always produces the same output. Second, there's a post-validation step that independently cross-checks the result: does profit equal revenue minus expenses? Does the federal tax fall within the expected bracket range? If anything doesn't add up, the workflow fails with a specific error instead of returning wrong numbers.

**Q: How would we add US tax?**
Same orchestration, different engine. The TaxEngineInterface defines the contract - input (revenue, expenses, jurisdiction, method) and output (tax breakdown). Canadian tax uses a deterministic engine. US tax would use an LLM-based engine because US tax rules are more complex and state-specific. You implement a new engine class, register it, and the orchestrator doesn't change. One config toggle to switch between them.

**Q: What about testing? How do we know the agent works correctly?**
For the tax engine - unit tests against known bracket data. Same input, same output, every time. For the workflow - the mock data mode lets you run the full pipeline without any external dependencies. For the LLM reasoning layer (in the LangGraph Studio version) - that's where model evals come in. You'd build a test suite of prompts and expected outcomes, run them against the agent, and measure accuracy.

**Q: Can we use a different model?**
One env var: TAX_CALC_LLM_MODEL_ID. Currently set to Claude Sonnet 4.6. Swap to any Bedrock model - Opus for higher accuracy on complex reasoning, Haiku for faster/cheaper on simple tasks. The tax math is deterministic regardless of which model you use - the model only powers the conversational layer.

---

## MCP

**Q: What is MCP exactly?**
Model Context Protocol - it's a standard way for an AI agent to discover and call tools. Think of it like a USB port for AI. Any MCP-compatible client can plug in and see what tools are available. We have 6 tools on one MCP server. Tomorrow you could point Copilot, Kiro, or a custom app at this same server and it works without changes.

**Q: Why MCP instead of just calling GraphQL directly?**
MCP gives you a standard interface that any AI client can use. If you called GraphQL directly from the agent, you'd be coupling the agent to a specific API. With MCP in between, the agent just says "call get_income" - it doesn't know or care whether that tool calls GraphQL, a REST API, or a database. When you add new data sources later, you add new MCP tools. The agent doesn't change.

**Q: Can we have multiple MCP servers?**
Yes - that's what the consolidated vs separate config toggle is for. Today all 6 tools are on one server. Flip to separate and each tool gets its own server with independent scaling and versioning. When you add bank import or US tax, those would be new MCP servers. That's when AgentCore Gateway becomes valuable - it routes tool calls to the right server automatically.

---

## Terminology Quick Reference

| Term | Meaning |
|------|---------|
| GST | Goods and Services Tax - Canada's 5% federal sales tax |
| HST | Harmonized Sales Tax - combined federal + provincial (e.g., Ontario 13%) |
| CPP | Canada Pension Plan - self-employed pay both employee and employer portions |
| EI | Employment Insurance - optional for self-employed, covers maternity/sickness |
| CRA | Canada Revenue Agency - the tax authority |
| MCP | Model Context Protocol - standard interface for AI tools |
| Cedar | Policy language used by Amazon Verified Permissions and AgentCore Policy |
