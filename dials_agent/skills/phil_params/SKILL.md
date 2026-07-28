---
name: phil_params
description: On-demand PHIL parameter documentation lookup for all DIALS commands
---

## PHIL Parameter Lookup

You have access to the **complete PHIL parameter documentation** for all 82 DIALS commands. When a user asks about available parameters, advanced options, or you need to find a specific parameter for troubleshooting:

1. Use the `lookup_phil_params` tool with the command name to get the full parameter listing
2. Use the `search_term` parameter to search for specific keywords within the output
3. The documentation includes help text, types, defaults, and expert levels

Example: To find all absorption-related parameters in dials.scale:
```
lookup_phil_params(command="dials.scale", search_term="absorption")
```

**IMPORTANT**: When users ask "what parameters does dials.X have?" or "what options are available for dials.X?", use the `lookup_phil_params` tool to give them accurate, complete information rather than relying on your memory alone.
