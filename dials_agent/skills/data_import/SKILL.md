---
name: data_import
description: Importing raw diffraction images into DIALS format (dials.import)
---

### dials.import
- Formats: CBF, HDF5/NeXus (.nxs, .h5), SMV, TIFF
- Tip: for large datasets, offer `image_range=1,1200` to process a subset first
- Use `lookup_phil_params` for full parameter list

### Import Step Options
When the user wants to import data (e.g., "analyze the insulin data", "work up my data"):

**CRITICAL**: Always use the actual data file paths from the "Available diffraction data files" section in the Current Context below. NEVER use hardcoded example paths like `../ins10_1.nxs` - these are just examples and will not work for the user's actual data.

Present these options in your response (using the ACTUAL file path from the context):
1. **Full dataset**: `dials.import <actual_file_path>` - processes all images (recommended for final processing)
2. **Quick test with subset**: `dials.import <actual_file_path> image_range=1,1200` - processes first 1200 images (faster, good for learning/testing)

Example response format (replace `<data_file>` with the actual path from context):
```
I can help you process your data! I found the following data file: <data_file>

Would you like to:

**Option 1 - Full dataset:**
`dials.import <data_file>`
This processes all images. Best for final data processing.

**Option 2 - Quick test (recommended for learning):**
`dials.import <data_file> image_range=1,1200`
This processes only the first 1200 images, which is much faster and good for testing the workflow.

Which option would you prefer?
```

**If no data files are found in the context**, do NOT abort or give up. Instead:
1. Ask the user where their data is located
2. When the user provides a path, **immediately use the `change_data_directory` tool** to switch to it
3. After switching, confirm the data was found and proceed with the import

**CRITICAL**: When the user tells you a data path (e.g., "my data is in /path/to/data"), you MUST:
1. Use `change_data_directory` with that path — do NOT just run `ls` on it
2. After switching, the data files will appear in your context automatically
3. Then proceed to suggest the import command

Example: "I don't see any diffraction data files in the current data directory. Where is your data located? I can switch to the correct directory for you."

Wait for the user to choose before using the suggest_dials_command tool.

### After Import (Visualization)
Ask: "Would you like to inspect the diffraction images before proceeding to spot finding?"
- **Yes**: Suggest `dials.image_viewer imported.expt` - allows checking beam center, detector distance, image quality
- **No**: Proceed to spot finding
