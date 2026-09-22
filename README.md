# DIALS AI Agent

A natural language interface for [DIALS](https://dials.github.io/) (Diffraction Integration for Advanced Light Sources) crystallography data processing — lets users describe data-processing goals in plain English, translates them into the appropriate DIALS commands, and explains the results.

The tool itself, its full documentation, and its version history live in **[`dials_agent/`](dials_agent/README.md)**.

## Repository scope

This repository also carries material from the author's broader DIALS work that is **not** part of the released tool: `plans/` (internal design/planning notes), the root-level `docs/` (a script for fetching upstream DIALS documentation, plus general tutorial references), and `tutorial/` (DIALS workflow tutorial writeups and sample data). None of it is required to install or run the agent, and none of it is covered by the citation below — the citable software is entirely within `dials_agent/`.

## Citing this software

If you use this tool in published work, please cite it using the metadata in [`CITATION.cff`](CITATION.cff) (or the "Cite this repository" button on GitHub).

## License

BSD 3-Clause License — see [`LICENSE`](LICENSE).
