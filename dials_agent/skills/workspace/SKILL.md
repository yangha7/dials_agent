---
name: workspace
description: File access, shell commands, directory management, calculations, and command timing
---

## Shell Commands

You can run arbitrary shell commands in the working directory using the `run_shell_command` tool. Use this for:
- Listing files: `ls -la`, `ls *.expt`
- Removing files: `rm *.expt *.refl *.log` (user will be asked to confirm)
- Checking disk usage: `du -sh *`
- Viewing file contents: `cat`, `head`, `tail`, `grep`
- Any other standard Unix commands

**IMPORTANT**: Use `run_shell_command` instead of telling the user to run commands manually. The tool will execute the command directly in the working directory. For destructive commands (rm, mv), the user will be prompted to confirm.

**TIP**: When the user says "start over", "clean up", or "remove old files", you can use `run_shell_command` with `rm` to remove DIALS output files. The user can also type `reset` or `clean` in the CLI to use the built-in cleanup feature.

## File Access

You have direct access to files in the working directory:

### Reading Log Files
Use the `read_file` tool to read log files directly - do NOT ask the user to run `cat` and paste the output. Common log files:
- `dials.import.log` - import output
- `dials.find_spots.log` - spot finding output
- `dials.index.log` - indexing output
- `dials.refine.log` - refinement output
- `dials.integrate.log` - integration output
- `dials.symmetry.log` - symmetry analysis output
- `dials.scale.log` - scaling output and merging statistics
- `dials.export.log` or `dials.merge.log` - export/merge output

When the user asks about results, errors, or wants to review output, use `read_file` to read the relevant log file and analyze it directly.

### Opening HTML Reports
Use the `open_file` tool to open HTML reports in a web browser - do NOT ask the user to open them manually. Common HTML files:
- `dials.scale.html` - scaling report with detailed statistics and plots
- `dials.report.html` - general processing report (from `dials.report`)

When an HTML report is generated (e.g., after scaling), proactively offer to open it for the user.

## Workspace Management

**You CAN change the working directory** — use the `change_working_directory` tool. Do NOT tell users they need to restart or type CLI commands to change directories.

**CRITICAL DISTINCTION — Switch vs Create:**
- **"switch to", "go to", "move to", "work in"** → use `change_working_directory(path="xxx", create=false)` — do NOT create new directories
- **"create", "make", "new directory"** → use `change_working_directory(path="xxx", create=true)` — creates the directory

When switching, the tool will search the current directory AND parent directory for matches, handling typos and case sensitivity. Sibling directories (in the parent) are commonly the target when users say "switch to xxx".

Examples:
- "Switch to the round2 folder" → `change_working_directory(path="../round2")` or `change_working_directory(path="round2")` — do NOT create
- "Go to the yang directory" → `change_working_directory(path="../yang")` — do NOT create
- "Create a directory called student1" → `change_working_directory(path="student1", create=true)` — creates it
- "Make a new folder for round 2" → `change_working_directory(path="round2", create=true)` — creates it
- "Go back to the main directory" → Tell user to type `cd` (returns to base directory)

This does NOT modify the .env file — the default starting directory is preserved for the next session.

The user can also use these CLI commands directly:
- `mkdir <name>` — Create a subdirectory and switch to it
- `cd <path>` — Change directory (relative or absolute)
- `cd` — Return to the base (starting) directory
- `pwd` / `workspace` — Show current and base directory

You can also use `change_data_directory` to switch the raw data directory when the user says their data is in a different location.

You can also use `run_shell_command` to rename directories (`mv old_name new_name`).

## Command Timing

The agent automatically records the execution time for every DIALS command, including start time, end time, and duration. This data is saved to `dials_agent_timing.log` in the working directory and persists across agent restarts.

When the user asks about timing, performance, or "how long did each step take?", use the `get_timing_report` tool to retrieve the timing data. Do NOT try to figure out timing from file timestamps or log files — use the tool.

## Token Usage

When the user asks about token usage, API cost, or how much of their budget remains, use the `get_token_usage` tool. It reports the cumulative session totals (input/output/cached tokens) and, if a budget is configured, how much remains. Do NOT guess at this from anything in the conversation — the per-turn usage line the CLI prints after each response is not visible to you, so this tool is the only way to answer these questions accurately.

## Calculations and Counting

**IMPORTANT**: Do NOT do mental arithmetic or visual counting. LLMs are unreliable at math and counting.

### For arithmetic (subtraction, division, percentages):
Use the `calculate` tool:
- Oscillation range: `calculate(expression="1200 * 0.1")`
- Percentage indexed: `calculate(expression="100 * 66997 / 107640")`
- Unit cell difference: `calculate(expression="67.85 - 67.82")`
- Spots per image: `calculate(expression="107640 / 1200")`

### For counting items (files, lines, datasets):
Use `run_shell_command` with shell counting tools — do NOT try to count visually:
- Count files: `run_shell_command(command="ls *.cbf.gz | wc -l")`
- Count datasets in output: `run_shell_command(command="grep -c 'template:' dials.import.log")`
- Count lines: `run_shell_command(command="wc -l < dials_agent_timing.log")`
- Count sweeps: `run_shell_command(command="grep -c 'sweep' dials.import.log")`

## Verify Before Reporting Outliers

**CRITICAL**: Before reporting any surprising or outlier results (e.g., "one dataset has a very different number of images", "the resolution is unusually high/low", "the scan range is different"), ALWAYS:
1. Double-check the numbers using the `calculate` tool or by re-reading the relevant log/output
2. Verify you are reading the data correctly (e.g., not confusing two columns, not misreading units)
3. If the outlier involves arithmetic (e.g., "dataset X has 50 fewer images"), use `calculate` to confirm
4. Only report the finding after verification

This prevents false alarms from LLM arithmetic errors or misread data.
