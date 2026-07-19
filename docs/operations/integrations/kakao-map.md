# Kakao Map MCP

Kakao Map MCP supports Korea place search such as restaurants, cafes, hospitals, pharmacies, public facilities, tourist spots, shops, and nearby-place lookup. The root README contains the current detailed setup section.

## Confirmed repository facts

- The repository uses `scripts/run-kakao-map-mcp.sh` from `.mcp.json` as the wrapper entry point.
- The wrapper clones or updates the upstream `mcp-server-kakao-map` source under `~/.cache/neo/mcp-server-kakao-map` and keeps that source outside this repository.
- The available tool documented in the README is `kakao_map_place_recommender`.
- `KAKAO_API_KEY` belongs in local `.env`; actual key values must never be committed or copied into documentation.

## Use boundary

Use Korean queries first when searching Korea places. Use only locations, addresses, neighborhoods, stations, or landmarks supplied by the user; do not infer the user's location. Treat place information as lookup-time information.
