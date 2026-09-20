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

**Ask which option first (using the ACTUAL file path from the context), then STOP — no tool
call this turn.** Present the two options in your text response and wait for the user's
answer; only call `suggest_dials_command` on the *next* turn, for the one option they chose.
See "Offering Options to Users" in your base instructions.

```
I found your data at <data_file>. Would you like to:

1. **Full dataset:** `dials.import <data_file>` — processes all images.
2. **Quick test:** `dials.import <data_file> image_range=1,1200` — first 1200 images, faster,
   good for learning/testing.

Reply with 1 or 2, or tell me exactly what you'd like to run instead.
```

Do not also call `suggest_dials_command` in this same response — that was tried twice live and
both times produced a confusing turn with an unresolved question sitting next to a
command already queued for y/n approval, regardless of whether the command was framed as a
plain suggestion or as a "default" with the other option mentioned in passing. Ask, and
actually wait for the answer, exactly like any other clarifying question.

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

### After Import (Visualization)
Ask: "Would you like to inspect the diffraction images before proceeding to spot finding?"
- **Yes**: Suggest `dials.image_viewer imported.expt` - allows checking beam center, detector distance, image quality
- **No**: Proceed to spot finding
