---
name: data_import
description: Importing raw diffraction images into DIALS format (dials.import)
---

### dials.import
- Formats: CBF, HDF5/NeXus (.nxs, .h5), SMV, TIFF
- Tip: for large datasets, offer `image_range=1,1200` to process a subset first
- Use `lookup_phil_params` for full parameter list
- **Compressed images (.bz2, .gz) need NO decompression step**: dxtbx/DIALS decompresses
  these transparently on read. Point `dials.import` directly at the compressed files, e.g.
  `dials.import t1.0*.img.bz2` — do NOT suggest `bunzip2`/`gunzip`/a shell loop to extract
  them first, that's unnecessary work and (if it duplicates hundreds of large image files)
  a real waste of disk space and time. This is distinct from an outer **.tar archive**
  bundling many such files, which genuinely does need extracting first (`tar xvf archive.tar`)
  — that's unpacking the container, not decompressing each image; if the individual
  compressed image files already exist on disk (e.g. found in "Available diffraction data
  files" with a `.bz2`/`.gz` type), the archive step is already done and only the
  `dials.import` command is needed.

### Import Step Options
When the user wants to import data (e.g., "analyze the insulin data", "work up my data"):

**CRITICAL**: Always use the actual data file paths from the "Available diffraction data files" section in the Current Context below. NEVER use hardcoded example paths like `../ins10_1.nxs` - these are just examples and will not work for the user's actual data.

**Just call `suggest_dials_command` directly with the plain, full-dataset import** (using the
ACTUAL file path from the context) — do not try to ask "full vs. quick subset" yourself first.
The CLI itself enforces that choice at the approval step for the first `dials.import` of a
fresh dataset (offering a quick `image_range=1,1200` subset as an alternative there), as a
structural safeguard: asking in text and waiting was tried repeatedly and skipped live every
time regardless of wording, so this decision no longer depends on your text having asked
anything. Suggesting the plain command directly is correct, expected behavior now, not a bug
to work around.

**If the user names a dataset by keyword rather than a path** (e.g. "process the insulin data",
"switch to lysozyme") — including when the data files currently visible in context are for a
*different* dataset than the one named — **call `select_dataset` with that keyword as
`name_hint` first, before anything else.** Do NOT reach for `run_shell_command`/`find` to
search for it yourself, and do NOT conclude "no X data available" just because the *currently
configured* data directory's visible files are for something else — the named dataset may be
a sibling subdirectory `select_dataset` can find directly. A real live-testing failure this is
guarding against: the data directory had two sibling subdirectories (e.g. `DPF3/` and
`Insulin/`, both containing only compressed `.img.bz2` images); asked to process "the insulin
data", the agent ran its own hand-written `find ... -iname "*ins*"` shell command, which came
back empty for reasons unrelated to whether the data existed (shell searches over a live
filesystem can be affected by directory-listing caching in ways a direct path check isn't),
and it then wrongly told the user no insulin data was available. `select_dataset` does a
direct, tested filesystem check instead of a shell search, and reports back either the single
match (switching to it automatically) or the full list of what it actually found — never a
bare "not found" when other datasets are sitting right there unmatched.
- If it returns `status: "selected"`: confirm the switch and proceed with the import options below.
- If `status: "ambiguous"` or `"no_match"`: it already lists the real dataset names found —
  read that list back to the user rather than guessing or re-searching yourself.
- If `status: "none_found"`: only now is it fair to say no recognized data was found under the
  configured data directory, and ask the user where their data actually is.

**If no data files are found in the context and the user hasn't named anything to search
for**, do NOT abort or give up. Instead:
1. Ask the user where their data is located
2. When the user provides a path, **immediately use the `change_data_directory` tool** to switch to it
3. After switching, confirm the data was found and proceed with the import

**CRITICAL**: When the user tells you a data path (e.g., "my data is in /path/to/data"), you MUST:
1. Use `change_data_directory` with that path — do NOT just run `ls` on it
2. After switching, the data files will appear in your context automatically
3. Then proceed to suggest the import command

Example: "I don't see any diffraction data files in the current data directory. Where is your data located? I can switch to the correct directory for you."

Don't call `suggest_dials_command` until the user actually gives you a path here — there's
nothing to import yet.

### After Import (Geometry Check + Visualization)
Run the numeric import geometry check (see your base instructions) automatically right after
`dials.import` succeeds — don't wait to be asked.

Whether to view the images first is no longer your call to make: the CLI itself pauses with a
real, direct question ("Would you like to open dials.image_viewer... ?") right after a
successful `dials.import`, and tells you the user's actual answer in the same message as the
command output — asked (and reworded) twice already for you to pause here yourself, and it
kept being skipped live regardless of wording, so this is now enforced structurally. You will
be told either "The user wants to inspect the images first — suggest `dials.image_viewer
imported.expt` now" or "The user wants to proceed directly to spot finding — suggest
`dials.find_spots` now, do not also offer the image viewer again." Follow that instruction
directly rather than deciding for yourself whether to mention the viewer. Do NOT mention
`dials.reciprocal_lattice_viewer` here regardless — nothing is indexed yet, so it has nothing
meaningful to show; that becomes relevant starting after indexing.
- **Clean geometry-check result**: its raw verdict is already shown to the user directly (you
  don't need to repeat it verbatim) — briefly say what it means in plain language, then follow
  the viewer instruction above. Don't skip this: silently running the check without explaining
  what it found is no better than not running it at all for someone watching the session live.
  Mention, once, that a deeper pixel-quality check (see your base instructions) is available if
  they want it — explicitly note it reads real image data and can take a while, and only run it
  if they actually ask. Do NOT run it yourself or make it part of the default next steps.
- **Flagged** (e.g. beam centre off-detector): explain plainly and propose
  `dials.search_beam_position` before spot finding — worth pausing on rather than letting
  indexing fail first and diagnosing it after the fact; this overrides the viewer instruction
  above, since fixing the geometry problem matters more right now than either viewing images
  or finding spots.
