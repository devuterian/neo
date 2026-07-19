# daiso-mcp

`daiso-mcp` is used for Korea local retail, stock, store, nearby place, fuel, convenience-store, supermarket, Olive Young, Daiso, and cinema lookups. The root README contains the current detailed command examples.

## Confirmed repository facts

- Codex or MCP hosts can read the root `.mcp.json` remote server configuration.
- The documented remote MCP endpoint is `https://mcp.aka.page`.
- Local CLI checks use `npx --yes daiso ... --json` without adding npm dependencies to this repository.
- No separate API key is documented for the basic Daiso MCP workflow.

## Use boundary

Retail stock, prices, places, fuel prices, cinema schedules, and seats are time-sensitive. Report them as lookup-time results and do not assume they remain current.
