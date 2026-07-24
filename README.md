
I like building the unglamorous parts of AI systems — the orchestration, the
evaluation harnesses, and the guardrails that keep autonomous agents from doing
something dumb. Most of my time goes into making agent infrastructure reliable
enough to actually trust.

I run a small homelab cluster where I prototype this end to end: multi-node model
serving, agent fleets that open their own pull requests, and the CI/CD + safety
tooling wrapped around them.

**A few things I've built**
- **[gh-workflows](https://github.com/Ait0u5hi/gh-workflows)** — a reusable CI/CD + security-scanning workflow library I share across my repos, so every project gets the same linting, dependency scanning, and release automation for free.
- **[hermes-plugin-workspace-guard](https://github.com/Ait0u5hi/hermes-plugin-workspace-guard)** — a safety plugin that sandboxes autonomous agents to their own git worktree, so a misbehaving agent can't scribble over the main checkout.
- **[hermes-agent](https://github.com/Ait0u5hi/hermes-agent)** — the agent framework those plugins plug into.

**Currently into:** LLM agents, evaluation & benchmarking, DevSecOps, and squeezing real work out of homelab-scale ML infra.
