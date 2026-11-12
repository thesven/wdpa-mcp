# wdpa-mcp

[![CI](https://github.com/thesven/wdpa-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/thesven/wdpa-mcp/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A dedicated conservation zoning and protected areas **Model Context Protocol (MCP)** server for the [World Database on Protected Areas (WDPA) and Protected Planet API v3](https://api.protectedplanet.net/).

Provides critical spatial conservation context to biodiversity observations (iNaturalist, eBird, GBIF), checking if wildlife sightings fall inside or adjacent to national parks, wilderness reserves, UNESCO biosphere reserves, or marine protected areas.

---

## Key Features

- **Reserve Proximity Evaluation**: Query coordinates (`lat`, `lon`, `radius_km`) to determine if a species observation is inside or near a protected conservation reserve.
- **IUCN Management Categories**: Identify strict nature reserves (Ia), wilderness areas (Ib), national parks (II), natural monuments (III), habitat management areas (IV), protected landscapes (V), and sustainable resource management reserves (VI).
- **National Coverage & 30x30 Metrics**: Retrieve terrestrial and marine protected surface area percentages by ISO-3 country to track progress toward Kunming-Montreal Global Biodiversity Framework targets.
- **Resilient Fallback Engine**: Built-in curated conservation registry ensures proximity queries and searches work reliably even without an external API token or during upstream downtime.

---

## Available Tools

| Tool | Description |
| :--- | :--- |
| `check_protected_area_nearby` | Assess whether GPS coordinates fall within or near a protected conservation area. |
| `search_protected_areas` | Search protected conservation areas by name, designation, or ISO country. |
| `get_protected_area_details` | Retrieve complete governance, IUCN management category, and area for a WDPA site. |
| `get_country_protection_coverage` | Retrieve national protected area coverage percentages and 30x30 statistics. |

---

## Installation & Usage

### Running with `uvx` (Recommended)

```bash
uvx --from git+https://github.com/thesven/wdpa-mcp.git wdpa-mcp
```

### Configuration (Optional)

If you have a Protected Planet API v3 token, you can provide it via environment variable:

```bash
PROTECTED_PLANET_API_KEY=your_token_here
# or
WDPA_API_KEY=your_token_here
```

### Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "wdpa": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/thesven/wdpa-mcp.git", "wdpa-mcp"],
      "env": {
        "PROTECTED_PLANET_API_KEY": "optional_token_here"
      }
    }
  }
}
```

---

## Development & Quality Gate

```bash
# Run code formatting check
uv run ruff format --check src tests scripts

# Run linting
uv run ruff check src tests scripts

# Run test suite with strict coverage floor (>90%)
uv run pytest --cov=wdpa_mcp --cov-branch --cov-report=term-missing

# Build wheel and sdist
uv build

# Run package distribution check & smoke test
uv run python scripts/check_dist.py
uv run python scripts/smoke.py
```

## License

MIT License. See [LICENSE](LICENSE) for details.
