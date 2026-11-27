---
name: slugshot-research-operations
description: Run Slugshot's research data collection end to end from a short instruction ("collect today's research", "research Spanish Roblox content", "refresh our watchlists", "research Creative Center", "execute this research brief from ChatGPT"). Picks the collectors, runs them, handles errors and quotas, validates, bundles for ChatGPT and reports. Use for any research collection, import or export task in this workspace.
---

# Slugshot research operations

Use the [command reference](../../../docs/COMMANDS.md) and the [data and provider rules](../../../docs/research-data.md). Use the [analysis skill](../slugshot-research-analysis/SKILL.md) when the request turns to interpretation.

| Request | Command |
|---|---|
| Today's research | `ss research collect --profile daily` |
| Spanish Roblox content | `ss research collect --profile spanish` |
| Refresh watched items | `ss research collect --profile refresh` |
| Bundle existing data | `ss research bundle` |
| Check status | `ss research status` and `ss research runs` |

1. Map a brief to available sources. Record gaps in scope and metric coverage.
2. Put saved YouTube queries, watchlists and families in `config/research/`. Compile changed families with `ss research families --compile`. Use one rotating retrieval market per query where configured.
3. Collect within the provider budget. Keep independent sources running when one is blocked. Use the run log to report failures and retries.
4. For Creative Center, run `ss observe cc-session`. A person reads each page and copies its contents. Validate the parsed ranks and counts against the paste. For Apify and other TikTok routes, use the [data guide](../../../docs/research-data.md#7-tiktok-collection-routes).
5. Run `ss research bundle`, check the intake report and identify scope, row counts, limitations and the bundle path. Give the owner the current corrected bundle for handoff.
