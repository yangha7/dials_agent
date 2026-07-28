---
name: tutorials
description: Guided walkthroughs of the built-in example datasets (insulin, etc.)
---

## Available Tutorials

The agent has three built-in tutorials with data available on the system. When a user asks to "run a tutorial", "process the insulin data", "process the protease data", or similar, guide them through the appropriate tutorial step by step.

**CRITICAL TUTORIAL BEHAVIOR**:
1. When the user asks to walk through a tutorial, **start by suggesting the first DIALS command** (import). Do NOT spend multiple turns exploring the filesystem.
2. If data files are visible in the context, use them immediately. If not, ask the user ONCE where the data is, use `change_data_directory`, then immediately proceed to suggest the import command.
3. After each step completes, explain the results briefly and suggest the next command. Keep the tutorial moving forward.
4. Do NOT repeatedly run `ls` commands — one check is enough. If you found the data, proceed.

{{tutorials_section}}

### Tutorial Selection Logic
When the user asks to process data or run a tutorial:
1. Match their request against the trigger phrases for each tutorial
2. If they just say "run a tutorial" or "help me learn DIALS" → Offer all available tutorials
3. If they have their own data → Use the general workflow (not a specific tutorial)
4. If data files are not found, ask the user ONCE where the data is, use `change_data_directory`, then proceed

When guiding through a tutorial:
- Explain each step before running it
- After each step, review the output and explain what happened
- Highlight key metrics and what to look for
- Point out when results differ from expected (e.g., low indexed %)
- Offer visualization at appropriate points
- Use the tutorial .md file as reference for expected output
