"""
DIALS command definitions and metadata.

This module defines the available DIALS commands, their parameters,
and expected inputs/outputs for the AI agent.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CommandCategory(Enum):
    """Categories of DIALS commands."""
    WORKFLOW = "workflow"
    UTILITY = "utility"
    VISUALIZATION = "visualization"


@dataclass
class CommandParameter:
    """Definition of a command parameter."""
    name: str
    description: str
    param_type: str = "string"  # string, int, float, bool, path
    required: bool = False
    default: Optional[str] = None
    example: Optional[str] = None


@dataclass
class CommandDefinition:
    """Definition of a DIALS command."""
    name: str
    description: str
    category: CommandCategory
    input_files: list[str] = field(default_factory=list)
    output_files: list[str] = field(default_factory=list)
    parameters: list[CommandParameter] = field(default_factory=list)
    requires_gui: bool = False
    typical_runtime: str = "seconds"  # seconds, minutes, hours
    
    def get_basic_usage(self) -> str:
        """Get basic usage string for the command."""
        inputs = " ".join(self.input_files) if self.input_files else ""
        return f"{self.name} {inputs}".strip()


# Define all DIALS commands
DIALS_COMMANDS = {
    # Workflow commands
    "dials.import": CommandDefinition(
        name="dials.import",
        description=(
            "Import diffraction image data files into DIALS format. "
            "Reads image metadata and filenames to determine relationships between image sets. "
            "Creates an experiments (.expt) file containing beam, detector, goniometer, and scan models. "
            "Supports CBF, HDF5/NeXus (.nxs, .h5), SMV, TIFF and other formats."
        ),
        category=CommandCategory.WORKFLOW,
        input_files=["/path/to/images/*.cbf", "/path/to/data.nxs"],
        output_files=["imported.expt"],
        parameters=[
            CommandParameter(
                name="output.experiments",
                description="Output experiment file name",
                default="imported.expt",
                example="output.experiments=my_data.expt"
            ),
            CommandParameter(
                name="output.log",
                description="The log filename",
                default="dials.import.log",
            ),
            CommandParameter(
                name="output.compact",
                description="Use compact JSON representation for experiment output",
                param_type="bool",
                default="False",
            ),
            CommandParameter(
                name="identifier_type",
                description="Type of unique identifier to generate (uuid, timestamp, or None)",
                default="uuid",
                example="identifier_type=timestamp"
            ),
            CommandParameter(
                name="input.template",
                description="Image sequence template with # for frame numbers (multiple allowed)",
                example="input.template=image_1_####.cbf"
            ),
            CommandParameter(
                name="input.directory",
                description="A directory containing images to import (multiple allowed)",
                example="input.directory=/data/images/"
            ),
            CommandParameter(
                name="input.reference_geometry",
                description="Use experimental geometry from this .expt file to override image headers",
                param_type="path",
                example="input.reference_geometry=reference.expt"
            ),
            CommandParameter(
                name="input.allow_multiple_sequences",
                description="If False, raise an error if multiple sequences are found",
                param_type="bool",
                default="True",
            ),
            CommandParameter(
                name="lookup.mask",
                description="Path to a mask file to apply",
                param_type="path",
            ),
            CommandParameter(
                name="lookup.gain",
                description="Path to a gain map file",
                param_type="path",
            ),
            CommandParameter(
                name="format.dynamic_shadowing",
                description="Enable dynamic shadowing (auto/True/False)",
                default="auto",
            ),
            CommandParameter(
                name="geometry.beam.wavelength",
                description="Override beam wavelength in Angstroms",
                param_type="float",
                example="geometry.beam.wavelength=0.9795"
            ),
            CommandParameter(
                name="geometry.beam.type",
                description="Override beam type (monochromatic or polychromatic)",
                default="monochromatic",
                example="geometry.beam.type=polychromatic"
            ),
            CommandParameter(
                name="geometry.beam.probe",
                description="Override beam probe type (x-ray, electron, or neutron)",
                default="x-ray",
                example="geometry.beam.probe=electron"
            ),
            CommandParameter(
                name="geometry.detector.panel.gain",
                description="Override detector panel gain",
                param_type="float",
            ),
            CommandParameter(
                name="geometry.detector.distance",
                description="Override detector distance in mm",
                param_type="float",
                example="geometry.detector.distance=200"
            ),
            CommandParameter(
                name="geometry.detector.slow_fast_beam_centre",
                description="Override beam centre (slow, fast) in mm",
                example="geometry.detector.slow_fast_beam_centre=105.5,111.2"
            ),
            CommandParameter(
                name="geometry.goniometer.axis",
                description="Override rotation axis direction (3 floats)",
                example="geometry.goniometer.axis=1,0,0"
            ),
            CommandParameter(
                name="geometry.scan.oscillation",
                description="Override oscillation start angle and width (2 floats)",
                example="geometry.scan.oscillation=0,0.1"
            ),
            CommandParameter(
                name="geometry.scan.image_range",
                description="Override image range (start, end)",
                example="geometry.scan.image_range=1,1800"
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.find_spots": CommandDefinition(
        name="dials.find_spots",
        description=(
            "Find strong diffraction spots on images. Uses connected component labelling "
            "in 3D for rotation data. Spots are filtered by size, resolution, and intensity. "
            "Supports dispersion, dispersion_extended, and radial_profile threshold algorithms."
        ),
        category=CommandCategory.WORKFLOW,
        input_files=["imported.expt"],
        output_files=["strong.refl"],
        parameters=[
            CommandParameter(
                name="output.reflections",
                description="Output reflection file name",
                default="strong.refl",
                example="output.reflections=spots.refl"
            ),
            CommandParameter(
                name="output.shoeboxes",
                description="Save raw pixel values inside reflection shoeboxes",
                param_type="bool",
                default="True",
            ),
            CommandParameter(
                name="output.experiments",
                description="Save modified experiments (usually only with hot pixel mask)",
                default="None",
            ),
            CommandParameter(
                name="per_image_statistics",
                description="Print a table of per-image statistics",
                param_type="bool",
                default="False",
            ),
            CommandParameter(
                name="spotfinder.lookup.mask",
                description="Path to a mask file for spot finding",
                param_type="path",
            ),
            CommandParameter(
                name="spotfinder.write_hot_mask",
                description="Write a hot pixel mask",
                param_type="bool",
                default="False",
            ),
            CommandParameter(
                name="spotfinder.force_2d",
                description="Do spot finding in 2D instead of 3D",
                param_type="bool",
                default="False",
            ),
            CommandParameter(
                name="spotfinder.scan_range",
                description="Image range to search (start, end), inclusive. Multiple ranges allowed.",
                example="spotfinder.scan_range=1,100"
            ),
            CommandParameter(
                name="spotfinder.region_of_interest",
                description="Region of interest on detector (x0, x1, y0, y1)",
                example="spotfinder.region_of_interest=100,900,100,900"
            ),
            CommandParameter(
                name="spotfinder.filter.min_spot_size",
                description="Minimum spot size in pixels (Auto by default)",
                param_type="int",
                default="Auto",
            ),
            CommandParameter(
                name="spotfinder.filter.max_spot_size",
                description="Maximum spot size in pixels",
                param_type="int",
                default="1000",
            ),
            CommandParameter(
                name="spotfinder.filter.max_strong_pixel_fraction",
                description="Max fraction of pixels marked as strong before raising exception",
                param_type="float",
                default="0.25",
            ),
            CommandParameter(
                name="spotfinder.filter.d_min",
                description="High resolution limit in Angstrom for spot filtering",
                param_type="float",
                example="spotfinder.filter.d_min=2.0"
            ),
            CommandParameter(
                name="spotfinder.filter.d_max",
                description="Low resolution limit in Angstrom for spot filtering",
                param_type="float",
                example="spotfinder.filter.d_max=50"
            ),
            CommandParameter(
                name="spotfinder.filter.ice_rings.filter",
                description="Filter out spots in ice ring regions",
                param_type="bool",
                default="False",
                example="spotfinder.filter.ice_rings.filter=True"
            ),
            CommandParameter(
                name="spotfinder.filter.untrusted.rectangle",
                description="An untrusted rectangle region (x0, x1, y0, y1)",
                example="spotfinder.filter.untrusted.rectangle=0,100,0,100"
            ),
            CommandParameter(
                name="spotfinder.filter.untrusted.circle",
                description="An untrusted circle region (xc, yc, r)",
                example="spotfinder.filter.untrusted.circle=500,500,50"
            ),
            CommandParameter(
                name="spotfinder.threshold.algorithm",
                description="Threshold algorithm: dispersion, dispersion_extended, or radial_profile",
                default="dispersion_extended",
                example="spotfinder.threshold.algorithm=dispersion"
            ),
            CommandParameter(
                name="spotfinder.threshold.dispersion.gain",
                description="Detector gain for dispersion threshold",
                param_type="float",
            ),
            CommandParameter(
                name="spotfinder.threshold.dispersion.sigma_strong",
                description="Sigma threshold for strong pixels (higher = fewer spots)",
                param_type="float",
                default="3.0",
                example="spotfinder.threshold.dispersion.sigma_strong=6"
            ),
            CommandParameter(
                name="spotfinder.threshold.dispersion.sigma_background",
                description="Sigma threshold for background pixels",
                param_type="float",
                default="6.0",
            ),
            CommandParameter(
                name="spotfinder.threshold.dispersion.global_threshold",
                description="Global threshold value for pixel intensity",
                param_type="float",
                default="0",
            ),
            CommandParameter(
                name="spotfinder.threshold.dispersion.kernel_size",
                description="Size of the local area around each pixel (2*n+1 x 2*n+1)",
                example="spotfinder.threshold.dispersion.kernel_size=6,6"
            ),
            CommandParameter(
                name="spotfinder.threshold.dispersion.min_local",
                description="Minimum number of pixels for local statistics",
                param_type="int",
                default="2",
            ),
            CommandParameter(
                name="spotfinder.mp.nproc",
                description="Number of processes to use per cluster job",
                param_type="int",
                default="1",
                example="spotfinder.mp.nproc=4"
            ),
            CommandParameter(
                name="spotfinder.mp.method",
                description="Cluster method (none, drmaa, sge, lsf, pbs)",
                default="none",
            ),
        ],
        typical_runtime="minutes"
    ),
    
    "dials.index": CommandDefinition(
        name="dials.index",
        description=(
            "Index diffraction spots to determine crystal unit cell and orientation. "
            "Assigns Miller indices to each spot. Supports FFT-based (fft1d, fft3d), "
            "real_space_grid_search, and other methods. Searches for primitive lattice "
            "by default and refines in P1. If unit_cell and space_group are set, only "
            "consistent solutions are accepted."
        ),
        category=CommandCategory.WORKFLOW,
        input_files=["imported.expt", "strong.refl"],
        output_files=["indexed.expt", "indexed.refl"],
        parameters=[
            CommandParameter(
                name="output.experiments",
                description="Output experiment file name",
                default="indexed.expt"
            ),
            CommandParameter(
                name="output.reflections",
                description="Output reflection file name",
                default="indexed.refl"
            ),
            CommandParameter(
                name="output.log",
                description="Log filename",
                default="dials.index.log"
            ),
            CommandParameter(
                name="indexing.known_symmetry.unit_cell",
                description="Known unit cell parameters (a,b,c,alpha,beta,gamma)",
                example="indexing.known_symmetry.unit_cell=37,79,79,90,90,90"
            ),
            CommandParameter(
                name="indexing.known_symmetry.space_group",
                description="Known space group",
                example="indexing.known_symmetry.space_group=P212121"
            ),
            CommandParameter(
                name="indexing.method",
                description="Indexing method: fft1d, fft3d, real_space_grid_search, ffbidx, low_res_spot_match, pink_indexer",
                default="fft3d",
                example="indexing.method=fft1d"
            ),
            CommandParameter(
                name="indexing.nproc",
                description="Number of processes to use",
                param_type="int",
                default="1",
                example="indexing.nproc=4"
            ),
            CommandParameter(
                name="indexing.joint_indexing",
                description="Index multiple experiments jointly (Auto/True/False)",
                default="Auto",
                example="indexing.joint_indexing=False"
            ),
            CommandParameter(
                name="indexing.index_assignment.simple.hkl_tolerance",
                description="Tolerance for assigning Miller indices",
                param_type="float",
                default="0.3",
                example="indexing.index_assignment.simple.hkl_tolerance=0.4"
            ),
            CommandParameter(
                name="indexing.refinement_protocol.n_macro_cycles",
                description="Number of macro-cycles of refinement during indexing",
                param_type="int",
                default="5",
            ),
            CommandParameter(
                name="indexing.refinement_protocol.d_min_start",
                description="Starting resolution limit for refinement protocol",
                param_type="float",
                example="indexing.refinement_protocol.d_min_start=4.0"
            ),
            CommandParameter(
                name="indexing.refinement_protocol.d_min_final",
                description="Final resolution limit for refinement protocol",
                param_type="float",
                example="indexing.refinement_protocol.d_min_final=1.5"
            ),
            CommandParameter(
                name="indexing.max_lattices",
                description="Maximum number of lattices to find (for multi-lattice indexing)",
                param_type="int",
                default="1",
                example="indexing.max_lattices=2"
            ),
            CommandParameter(
                name="indexing.image_range",
                description="Subset of images to use for indexing",
                example="indexing.image_range=1,100"
            ),
            CommandParameter(
                name="indexing.stills.ewald_proximity_resolution_cutoff",
                description="Resolution cutoff for Ewald sphere proximity (stills only)",
                param_type="float",
                default="2.0",
            ),
            CommandParameter(
                name="refinement.parameterisation.scan_varying",
                description="Allow scan-varying refinement during indexing",
                param_type="bool",
                default="False",
            ),
            CommandParameter(
                name="refinement.parameterisation.beam.fix",
                description="Fix beam parameters: all, in_spindle_plane, out_spindle_plane, wavelength",
                default="in_spindle_plane+wavelength",
                example="refinement.parameterisation.beam.fix=all"
            ),
            CommandParameter(
                name="refinement.parameterisation.crystal.fix",
                description="Fix crystal parameters: all, cell, orientation",
                example="refinement.parameterisation.crystal.fix=cell"
            ),
            CommandParameter(
                name="refinement.parameterisation.detector.fix",
                description="Fix detector parameters: all, position, orientation, distance",
                example="refinement.parameterisation.detector.fix=all"
            ),
            CommandParameter(
                name="refinement.reflections.outlier.algorithm",
                description="Outlier rejection algorithm: null, auto, mcd, tukey, sauter_poon",
                default="auto",
            ),
        ],
        typical_runtime="minutes"
    ),
    
    "dials.refine": CommandDefinition(
        name="dials.refine",
        description=(
            "Refine diffraction geometry of experiments against indexed reflections. "
            "For rotation scans, the model may be static (same for all reflections) or "
            "scan-varying (dependent on image number). Controls fixing of beam, crystal, "
            "detector, and goniometer parameters."
        ),
        category=CommandCategory.WORKFLOW,
        input_files=["indexed.expt", "indexed.refl"],
        output_files=["refined.expt", "refined.refl"],
        parameters=[
            CommandParameter(
                name="output.experiments",
                description="Output experiment file name",
                default="refined.expt"
            ),
            CommandParameter(
                name="output.reflections",
                description="Output reflection file name",
                default="refined.refl"
            ),
            CommandParameter(
                name="output.log",
                description="Log filename",
                default="dials.refine.log"
            ),
            CommandParameter(
                name="n_static_macrocycles",
                description="Number of macro-cycles of static refinement",
                param_type="int",
                default="1",
            ),
            CommandParameter(
                name="refinement.parameterisation.scan_varying",
                description="Allow models to vary during scan (Auto/True/False). Auto enables for long scans.",
                default="Auto",
                example="refinement.parameterisation.scan_varying=True"
            ),
            CommandParameter(
                name="refinement.parameterisation.interval_width_degrees",
                description="Interval width in degrees for scan-varying parameterisation",
                param_type="float",
                example="refinement.parameterisation.interval_width_degrees=36.0"
            ),
            CommandParameter(
                name="refinement.parameterisation.beam.fix",
                description="Fix beam parameters: all, in_spindle_plane, out_spindle_plane, wavelength",
                default="in_spindle_plane+wavelength",
                example="refinement.parameterisation.beam.fix=all"
            ),
            CommandParameter(
                name="refinement.parameterisation.crystal.fix",
                description="Fix crystal parameters: all, cell, orientation",
                example="refinement.parameterisation.crystal.fix=cell"
            ),
            CommandParameter(
                name="refinement.parameterisation.detector.fix",
                description="Fix detector parameters: all, position, orientation, distance",
                example="refinement.parameterisation.detector.fix=all"
            ),
            CommandParameter(
                name="refinement.parameterisation.goniometer.fix",
                description="Fix goniometer parameters: all, in_beam_plane, out_beam_plane",
                default="all",
                example="refinement.parameterisation.goniometer.fix=in_beam_plane"
            ),
            CommandParameter(
                name="refinement.reflections.outlier.algorithm",
                description="Outlier rejection algorithm: null, auto, mcd, tukey, sauter_poon",
                default="auto",
            ),
            CommandParameter(
                name="separate_independent_sets",
                description="Separate experiment list into independent groups for refinement",
                param_type="bool",
                default="True",
            ),
        ],
        typical_runtime="minutes"
    ),
    
    "dials.integrate": CommandDefinition(
        name="dials.integrate",
        description=(
            "Integrate reflections on diffraction images. Called with experiment list "
            "from dials.index or dials.refine and strong spots for profile model calculation. "
            "Supports profile fitting and summation integration. Background algorithms include "
            "Auto, glm, gmodel, null, and simple."
        ),
        category=CommandCategory.WORKFLOW,
        input_files=["refined.expt", "refined.refl"],
        output_files=["integrated.expt", "integrated.refl"],
        parameters=[
            CommandParameter(
                name="output.experiments",
                description="Output experiment file name",
                default="integrated.expt"
            ),
            CommandParameter(
                name="output.reflections",
                description="Output reflection file name",
                default="integrated.refl"
            ),
            CommandParameter(
                name="output.log",
                description="Log filename",
                default="dials.integrate.log"
            ),
            CommandParameter(
                name="output.phil",
                description="Output phil parameters file",
                default="dials.integrate.phil"
            ),
            CommandParameter(
                name="output.report",
                description="Output integration report filename",
            ),
            CommandParameter(
                name="scan_range",
                description="Image range to integrate (start, end). Multiple ranges allowed.",
                example="scan_range=1,100"
            ),
            CommandParameter(
                name="create_profile_model",
                description="Create profile model from strong spots",
                param_type="bool",
                default="True",
            ),
            CommandParameter(
                name="integration.lookup.mask",
                description="Path to a mask file for integration",
                param_type="path",
            ),
            CommandParameter(
                name="integration.block.size",
                description="Block size for processing (auto or number)",
                default="auto",
                example="integration.block.size=10"
            ),
            CommandParameter(
                name="integration.block.units",
                description="Block size units: degrees, radians, or frames",
                default="degrees",
            ),
            CommandParameter(
                name="integration.block.max_memory_usage",
                description="Maximum fraction of memory to use",
                param_type="float",
                default="0.80",
            ),
            CommandParameter(
                name="integration.use_dynamic_mask",
                description="Use dynamic mask during integration",
                param_type="bool",
                default="True",
            ),
            CommandParameter(
                name="integration.profile.fitting",
                description="Use profile fitting for integration",
                param_type="bool",
                default="True",
                example="integration.profile.fitting=False"
            ),
            CommandParameter(
                name="integration.background.algorithm",
                description="Background algorithm: Auto, glm, gmodel, null, simple",
                default="Auto",
                example="integration.background.algorithm=glm"
            ),
            CommandParameter(
                name="integration.background.glm.model.algorithm",
                description="GLM background model: constant2d, constant3d, loglinear2d, loglinear3d",
                default="constant3d",
            ),
            CommandParameter(
                name="integration.summation.detector_gain",
                description="Detector gain for summation integration",
                param_type="float",
                default="1",
            ),
            CommandParameter(
                name="integration.mp.nproc",
                description="Number of processes to use",
                param_type="int",
                default="1",
                example="integration.mp.nproc=4"
            ),
            CommandParameter(
                name="integration.mp.method",
                description="Parallelization method: multiprocessing, drmaa, sge, lsf, pbs",
                default="multiprocessing",
            ),
            CommandParameter(
                name="integration.mp.njobs",
                description="Number of cluster jobs to use",
                param_type="int",
                default="1",
            ),
            CommandParameter(
                name="prediction.d_min",
                description="High resolution limit for prediction in Angstrom",
                param_type="float",
                example="prediction.d_min=1.5"
            ),
            CommandParameter(
                name="prediction.d_max",
                description="Low resolution limit for prediction in Angstrom",
                param_type="float",
                example="prediction.d_max=50"
            ),
        ],
        typical_runtime="minutes"
    ),
    
    "dials.symmetry": CommandDefinition(
        name="dials.symmetry",
        description=(
            "Determine Laue group symmetry using the methods of POINTLESS (Evans, 2006/2011). "
            "Scores possible Laue groups and checks systematic absences to determine space group. "
            "Best for single-crystal datasets. For multiple crystals, use dials.cosym instead."
        ),
        category=CommandCategory.WORKFLOW,
        input_files=["integrated.expt", "integrated.refl"],
        output_files=["symmetrized.expt", "symmetrized.refl"],
        parameters=[
            CommandParameter(
                name="output.experiments",
                description="Output experiment file name",
                default="symmetrized.expt"
            ),
            CommandParameter(
                name="output.reflections",
                description="Output reflection file name",
                default="symmetrized.refl"
            ),
            CommandParameter(
                name="output.log",
                description="Log filename",
                default="dials.symmetry.log"
            ),
            CommandParameter(
                name="output.html",
                description="HTML report filename",
                default="dials.symmetry.html"
            ),
            CommandParameter(
                name="output.json",
                description="JSON output filename",
                default="dials.symmetry.json"
            ),
            CommandParameter(
                name="d_min",
                description="High resolution limit (Auto by default)",
                param_type="float",
                default="Auto",
                example="d_min=2.0"
            ),
            CommandParameter(
                name="min_i_mean_over_sigma_mean",
                description="Minimum I/sigma for inclusion",
                param_type="float",
                default="4",
            ),
            CommandParameter(
                name="min_cc_half",
                description="Minimum CC1/2 for inclusion",
                param_type="float",
                default="0.6",
            ),
            CommandParameter(
                name="normalisation",
                description="Normalisation method: kernel, quasi, ml_iso, ml_aniso",
                default="ml_aniso",
            ),
            CommandParameter(
                name="laue_group",
                description="Optionally specify Laue group (auto=test all, None=use input)",
                default="auto",
                example="laue_group=P4/mmm"
            ),
            CommandParameter(
                name="change_of_basis_op",
                description="Optionally specify change of basis operator",
                example="change_of_basis_op=a,b,c"
            ),
            CommandParameter(
                name="systematic_absences.check",
                description="Check systematic absences for space group determination",
                param_type="bool",
                default="True",
            ),
            CommandParameter(
                name="systematic_absences.method",
                description="Method for systematic absence analysis: direct or fourier",
                default="direct",
            ),
            CommandParameter(
                name="lattice_symmetry_max_delta",
                description="Maximum delta for lattice symmetry determination",
                param_type="float",
                default="2.0",
            ),
            CommandParameter(
                name="best_monoclinic_beta",
                description="Prefer I2 over C2 for monoclinic if it gives less oblique cell",
                param_type="bool",
                default="True",
            ),
            CommandParameter(
                name="partiality_threshold",
                description="Use only reflections with partiality above this threshold",
                param_type="float",
                default="0.4",
            ),
        ],
        typical_runtime="minutes"
    ),
    
    "dials.cosym": CommandDefinition(
        name="dials.cosym",
        description=(
            "Determine symmetry and resolve indexing ambiguity for multiple crystals "
            "using correlation analysis in a multi-dimensional space. Essential for "
            "multi-crystal datasets and space groups with indexing ambiguity (e.g., I213)."
        ),
        category=CommandCategory.WORKFLOW,
        input_files=["integrated.expt", "integrated.refl"],
        output_files=["symmetrized.expt", "symmetrized.refl"],
        parameters=[
            CommandParameter(
                name="output.experiments",
                description="Output experiment file name",
                default="symmetrized.expt"
            ),
            CommandParameter(
                name="output.reflections",
                description="Output reflection file name",
                default="symmetrized.refl"
            ),
            CommandParameter(
                name="space_group",
                description="Target space group",
                example="space_group=I213"
            ),
            CommandParameter(
                name="d_min",
                description="High resolution limit",
                param_type="float",
                example="d_min=2.0"
            ),
            CommandParameter(
                name="lattice_group",
                description="Lattice group to use",
                example="lattice_group=I23"
            ),
            CommandParameter(
                name="best_monoclinic_beta",
                description="Prefer I2 over C2 for monoclinic if it gives less oblique cell",
                param_type="bool",
                default="True",
            ),
        ],
        typical_runtime="minutes"
    ),
    
    "dials.scale": CommandDefinition(
        name="dials.scale",
        description=(
            "Scale integrated datasets to improve internal consistency of reflection intensities. "
            "Uses a physically motivated scaling model with scale, decay (B-factor), and absorption "
            "corrections by default. Supports KB, array, dose_decay, and physical models. "
            "Outputs scaled.refl, scaled.expt, and an HTML report with merging statistics."
        ),
        category=CommandCategory.WORKFLOW,
        input_files=["symmetrized.expt", "symmetrized.refl"],
        output_files=["scaled.expt", "scaled.refl", "dials.scale.html"],
        parameters=[
            CommandParameter(
                name="output.experiments",
                description="Output experiment file name",
                default="scaled.expt"
            ),
            CommandParameter(
                name="output.reflections",
                description="Output reflection file name",
                default="scaled.refl"
            ),
            CommandParameter(
                name="output.log",
                description="Log filename",
                default="dials.scale.log"
            ),
            CommandParameter(
                name="output.html",
                description="HTML report filename with merging statistics and plots",
                default="dials.scale.html"
            ),
            CommandParameter(
                name="output.unmerged_mtz",
                description="Output unmerged MTZ file directly from scaling",
                example="output.unmerged_mtz=scaled_unmerged.mtz"
            ),
            CommandParameter(
                name="output.merged_mtz",
                description="Output merged MTZ file directly from scaling",
                example="output.merged_mtz=scaled_merged.mtz"
            ),
            CommandParameter(
                name="model",
                description="Scaling model: KB, array, dose_decay, or physical",
                default="physical",
                example="model=KB"
            ),
            CommandParameter(
                name="anomalous",
                description="Separate anomalous pairs for scaling (for SAD/MAD phasing)",
                param_type="bool",
                default="False",
                example="anomalous=True"
            ),
            CommandParameter(
                name="d_min",
                description="High resolution cutoff in Angstrom",
                param_type="float",
                example="d_min=1.8"
            ),
            CommandParameter(
                name="d_max",
                description="Low resolution cutoff in Angstrom",
                param_type="float",
                example="d_max=50"
            ),
            CommandParameter(
                name="physical.absorption_correction",
                description="Apply spherical harmonic absorption correction (auto=True if oscillation>60)",
                default="auto",
                example="physical.absorption_correction=False"
            ),
            CommandParameter(
                name="physical.absorption_level",
                description="Expected absorption level: low (~1%), medium (~5%), high (>25%)",
                example="physical.absorption_level=medium"
            ),
            CommandParameter(
                name="physical.decay_correction",
                description="Apply decay (B-factor) correction",
                param_type="bool",
                default="True",
            ),
            CommandParameter(
                name="physical.scale_interval",
                description="Rotation interval between scale model parameters (auto by default)",
                param_type="float",
                default="auto",
                example="physical.scale_interval=10.0"
            ),
            CommandParameter(
                name="physical.lmax",
                description="Number of spherical harmonics for absorption (2-6 recommended)",
                param_type="int",
                default="auto",
                example="physical.lmax=6"
            ),
            CommandParameter(
                name="overwrite_existing_models",
                description="Overwrite existing scaling models (for re-scaling)",
                param_type="bool",
                default="False",
                example="overwrite_existing_models=True"
            ),
            CommandParameter(
                name="reflection_selection.method",
                description="Method for selecting reflections: quasi_random, intensity_ranges, use_all, random",
                default="quasi_random",
            ),
            CommandParameter(
                name="reflection_selection.best_unit_cell",
                description="Best unit cell to use for merging statistics",
                example="reflection_selection.best_unit_cell=67.5,67.5,67.5,90,90,90"
            ),
            CommandParameter(
                name="filtering.method",
                description="Filtering method: None or deltacchalf",
                example="filtering.method=deltacchalf"
            ),
            CommandParameter(
                name="filtering.deltacchalf.max_cycles",
                description="Maximum number of filtering cycles",
                param_type="int",
                default="6",
            ),
            CommandParameter(
                name="filtering.deltacchalf.stdcutoff",
                description="Standard deviation cutoff for delta CC1/2 filtering",
                param_type="float",
                default="4.0",
            ),
            CommandParameter(
                name="scaling_options.check_consistent_indexing",
                description="Check for consistent indexing between datasets",
                param_type="bool",
                default="False",
                example="scaling_options.check_consistent_indexing=True"
            ),
        ],
        typical_runtime="minutes"
    ),
    
    "dials.export": CommandDefinition(
        name="dials.export",
        description=(
            "Export DIALS processing results in various formats. Supports MTZ (for CCP4/Phenix), "
            "NXS (NeXus/NXmx), mmCIF, XDS_ASCII, SADABS, MOSFLM, XDS, SHELX, and PETS formats. "
            "For scaled data, intensity=scale is set implicitly."
        ),
        category=CommandCategory.WORKFLOW,
        input_files=["scaled.expt", "scaled.refl"],
        output_files=["scaled.mtz"],
        parameters=[
            CommandParameter(
                name="format",
                description="Output format: mtz, sadabs, nxs, mmcif, mosflm, xds, xds_ascii, json, shelx, pets",
                default="mtz",
                example="format=nxs"
            ),
            CommandParameter(
                name="intensity",
                description="Intensity type to export: auto, profile, sum, scale",
                default="auto",
                example="intensity=scale"
            ),
            CommandParameter(
                name="mtz.hklout",
                description="Output MTZ filename (auto generates name from input)",
                default="auto",
                example="mtz.hklout=output.mtz"
            ),
            CommandParameter(
                name="mtz.combine_partials",
                description="Combine partial reflections in MTZ output",
                param_type="bool",
                default="True",
            ),
            CommandParameter(
                name="mtz.partiality_threshold",
                description="Partiality threshold for including reflections in MTZ",
                param_type="float",
                default="0.4",
            ),
            CommandParameter(
                name="mtz.min_isigi",
                description="Minimum I/sigma for MTZ output",
                param_type="float",
                default="-5",
            ),
            CommandParameter(
                name="mtz.filter_ice_rings",
                description="Filter ice ring reflections from MTZ output",
                param_type="bool",
                default="False",
                example="mtz.filter_ice_rings=True"
            ),
            CommandParameter(
                name="mtz.d_min",
                description="High resolution limit for MTZ output",
                param_type="float",
                example="mtz.d_min=1.5"
            ),
            CommandParameter(
                name="mtz.best_unit_cell",
                description="Best unit cell to use in MTZ output",
                example="mtz.best_unit_cell=67.5,67.5,67.5,90,90,90"
            ),
            CommandParameter(
                name="mtz.crystal_name",
                description="Crystal name in MTZ file",
                default="XTAL",
            ),
            CommandParameter(
                name="mtz.project_name",
                description="Project name in MTZ file",
                default="DIALS",
            ),
            CommandParameter(
                name="nxs.hklout",
                description="Output NeXus filename",
                default="integrated.nxs",
                example="nxs.hklout=output.nxs"
            ),
            CommandParameter(
                name="mmcif.hklout",
                description="Output mmCIF filename",
                default="auto",
                example="mmcif.hklout=output.mmcif"
            ),
            CommandParameter(
                name="mmcif.compress",
                description="Compression for mmCIF: gz, bz2, xz",
                example="mmcif.compress=gz"
            ),
            CommandParameter(
                name="shelx.hklout",
                description="Output SHELX HKL filename",
                default="dials.hkl",
            ),
            CommandParameter(
                name="shelx.ins",
                description="Output SHELX instruction filename",
                default="dials.ins",
            ),
            CommandParameter(
                name="shelx.composition",
                description="Expected composition for SHELX instruction file",
                default="CH",
                example="shelx.composition=C3H7NO2S"
            ),
        ],
        typical_runtime="seconds"
    ),
    
    # Utility commands
    "dials.show": CommandDefinition(
        name="dials.show",
        description=(
            "Display information about experiment and reflection files. "
            "Shows beam, detector, goniometer, scan, and crystal models. "
            "Can also show reflection data, flags, and image statistics."
        ),
        category=CommandCategory.UTILITY,
        input_files=["*.expt", "*.refl"],
        output_files=[],
        parameters=[
            CommandParameter(
                name="show_scan_varying",
                description="Show crystal model at each scan point",
                param_type="bool",
                default="False",
            ),
            CommandParameter(
                name="show_shared_models",
                description="Show which models are linked to which experiments",
                param_type="bool",
                default="False",
            ),
            CommandParameter(
                name="show_all_reflection_data",
                description="Print individual reflections",
                param_type="bool",
                default="False",
            ),
            CommandParameter(
                name="show_intensities",
                description="Show reflection intensities",
                param_type="bool",
                default="False",
            ),
            CommandParameter(
                name="show_centroids",
                description="Show reflection centroids",
                param_type="bool",
                default="False",
            ),
            CommandParameter(
                name="show_profile_fit",
                description="Show profile fitting information",
                param_type="bool",
                default="False",
            ),
            CommandParameter(
                name="show_flags",
                description="Show summary table of reflection flags",
                param_type="bool",
                default="False",
            ),
            CommandParameter(
                name="show_identifiers",
                description="Show experiment identifiers map",
                param_type="bool",
                default="False",
            ),
            CommandParameter(
                name="max_reflections",
                description="Limit the number of reflections in output",
                param_type="int",
            ),
            CommandParameter(
                name="image_statistics.show_raw",
                description="Show statistics on raw image values",
                param_type="bool",
                default="False",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.report": CommandDefinition(
        name="dials.report",
        description=(
            "Generate an HTML report with analysis plots and statistics. "
            "Works with output from any DIALS processing step."
        ),
        category=CommandCategory.UTILITY,
        input_files=["*.expt", "*.refl"],
        output_files=["dials.report.html"],
        parameters=[
            CommandParameter(
                name="output.html",
                description="Output HTML filename",
                default="dials.report.html"
            ),
            CommandParameter(
                name="output.json",
                description="Optional JSON file with plot data",
            ),
            CommandParameter(
                name="output.external_dependencies",
                description="How to handle external dependencies: remote, local, or embed",
                default="remote",
            ),
            CommandParameter(
                name="pixels_per_bin",
                description="Pixels per bin for detector plots",
                param_type="int",
                default="40",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.refine_bravais_settings": CommandDefinition(
        name="dials.refine_bravais_settings",
        description=(
            "Refine all Bravais settings consistent with the primitive unit cell. "
            "Prints a table with metric fit, RMSD, refined unit cell, and change of basis operator "
            "for each setting. Generates bravais_setting_N.expt files for each setting."
        ),
        category=CommandCategory.UTILITY,
        input_files=["indexed.expt", "indexed.refl"],
        output_files=["bravais_summary.json", "bravais_setting_*.expt"],
        parameters=[
            CommandParameter(
                name="lepage_max_delta",
                description="Maximum delta for Le Page algorithm",
                param_type="float",
                default="5",
            ),
            CommandParameter(
                name="nproc",
                description="Number of processes (Auto by default)",
                default="Auto",
                example="nproc=4"
            ),
            CommandParameter(
                name="best_monoclinic_beta",
                description="Prefer I2 over C2 for monoclinic if less oblique cell",
                param_type="bool",
                default="True",
            ),
            CommandParameter(
                name="crystal_id",
                description="ID of crystal to refine (for multi-crystal experiments)",
                param_type="int",
            ),
            CommandParameter(
                name="output.directory",
                description="Output directory for bravais_setting_*.expt files",
                default=".",
            ),
            CommandParameter(
                name="output.prefix",
                description="Prefix for output files",
            ),
            CommandParameter(
                name="refinement.parameterisation.beam.fix",
                description="Fix beam parameters: all, in_spindle_plane, out_spindle_plane, wavelength",
                default="in_spindle_plane+wavelength",
            ),
            CommandParameter(
                name="refinement.parameterisation.detector.fix",
                description="Fix detector parameters: all, position, orientation, distance",
                example="refinement.parameterisation.detector.fix=all"
            ),
        ],
        typical_runtime="minutes"
    ),
    
    "dials.reindex": CommandDefinition(
        name="dials.reindex",
        description=(
            "Re-index an experiment/reflection file from one setting to another. "
            "Change of basis operator can be in h,k,l or a,b,c or x,y,z conventions. "
            "Can also reindex to match a reference dataset for resolving indexing ambiguity."
        ),
        category=CommandCategory.UTILITY,
        input_files=["*.expt", "*.refl"],
        output_files=["reindexed.expt", "reindexed.refl"],
        parameters=[
            CommandParameter(
                name="change_of_basis_op",
                description="Change of basis operator (in h,k,l or a,b,c or x,y,z)",
                default="a,b,c",
                example="change_of_basis_op=b+c,a+c,a+b"
            ),
            CommandParameter(
                name="hkl_offset",
                description="HKL offset to apply (3 integers)",
                example="hkl_offset=0,0,1"
            ),
            CommandParameter(
                name="space_group",
                description="Space group to apply AFTER the change of basis operator",
                example="space_group=P212121"
            ),
            CommandParameter(
                name="reference.experiments",
                description="Reference experiment for determining change of basis operator",
                param_type="path",
                example="reference.experiments=reference.expt"
            ),
            CommandParameter(
                name="reference.reflections",
                description="Reference reflections for consistent reindexing",
                param_type="path",
                example="reference.reflections=reference.refl"
            ),
            CommandParameter(
                name="output.experiments",
                description="Output experiment filename",
                default="reindexed.expt",
            ),
            CommandParameter(
                name="output.reflections",
                description="Output reflection filename",
                default="reindexed.refl",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.detect_blanks": CommandDefinition(
        name="dials.detect_blanks",
        description="Identify blank or damaged images in the dataset.",
        category=CommandCategory.UTILITY,
        input_files=["imported.expt", "strong.refl"],
        output_files=[],
        parameters=[
            CommandParameter(
                name="phi_step",
                description="Phi step for analysis",
                param_type="float",
                default="2.0"
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.estimate_resolution": CommandDefinition(
        name="dials.estimate_resolution",
        description=(
            "Estimate resolution limit by fitting curves to merging statistics in resolution bins. "
            "Supports cc_half (default), isigma, misigma, i_mean_over_sigma_mean, cc_ref, "
            "completeness, and rmerge metrics. Can also accept unmerged MTZ files as input."
        ),
        category=CommandCategory.UTILITY,
        input_files=["scaled.expt", "scaled.refl"],
        output_files=["dials.estimate_resolution.html"],
        parameters=[
            CommandParameter(
                name="resolution.cc_half",
                description="Minimum CC1/2 in outer shell (default metric, set to None to disable)",
                param_type="float",
                default="0.3",
                example="resolution.cc_half=0.1"
            ),
            CommandParameter(
                name="resolution.cc_half_method",
                description="CC1/2 calculation method: half_dataset or sigma_tau",
                default="half_dataset",
            ),
            CommandParameter(
                name="resolution.cc_half_fit",
                description="CC1/2 fitting function: polynomial or tanh",
                default="tanh",
            ),
            CommandParameter(
                name="resolution.isigma",
                description="Minimum unmerged <I/sigI> in outer shell (set value to enable)",
                param_type="float",
                example="resolution.isigma=0.25"
            ),
            CommandParameter(
                name="resolution.misigma",
                description="Minimum merged <I/sigI> in outer shell (set value to enable)",
                param_type="float",
                example="resolution.misigma=1.0"
            ),
            CommandParameter(
                name="resolution.completeness",
                description="Minimum completeness in outer shell (set value to enable)",
                param_type="float",
                example="resolution.completeness=0.5"
            ),
            CommandParameter(
                name="resolution.rmerge",
                description="Maximum Rmerge in outer shell (set value to enable)",
                param_type="float",
                example="resolution.rmerge=0.5"
            ),
            CommandParameter(
                name="resolution.cc_ref",
                description="Minimum CC vs reference dataset in outer shell",
                param_type="float",
                default="0.1",
            ),
            CommandParameter(
                name="resolution.reference",
                description="Reference dataset (MTZ file) for cc_ref calculation",
                param_type="path",
                example="resolution.reference=reference.mtz"
            ),
            CommandParameter(
                name="resolution.nbins",
                description="Maximum number of resolution bins",
                param_type="int",
                default="50",
            ),
            CommandParameter(
                name="resolution.reflections_per_bin",
                description="Minimum number of reflections per bin",
                param_type="int",
                default="10",
            ),
            CommandParameter(
                name="resolution.batch_range",
                description="Batch range to use for estimation",
                example="resolution.batch_range=1,100"
            ),
            CommandParameter(
                name="resolution.anomalous",
                description="Keep anomalous pairs separate in statistics",
                param_type="bool",
                default="False",
            ),
            CommandParameter(
                name="output.html",
                description="HTML report filename",
                default="dials.estimate_resolution.html",
            ),
            CommandParameter(
                name="output.json",
                description="JSON output filename",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.merge": CommandDefinition(
        name="dials.merge",
        description="Merge scaled data and output MTZ file with merged intensities.",
        category=CommandCategory.UTILITY,
        input_files=["scaled.expt", "scaled.refl"],
        output_files=["merged.mtz"],
        parameters=[
            CommandParameter(
                name="output.mtz",
                description="Output merged MTZ filename",
                default="merged.mtz"
            ),
            CommandParameter(
                name="d_min",
                description="High resolution cutoff",
                param_type="float",
                example="d_min=1.8"
            ),
            CommandParameter(
                name="d_max",
                description="Low resolution cutoff",
                param_type="float",
            ),
            CommandParameter(
                name="anomalous",
                description="Merge anomalous data separately",
                param_type="bool",
                default="False",
                example="anomalous=True"
            ),
            CommandParameter(
                name="best_unit_cell",
                description="Best unit cell to use",
                example="best_unit_cell=67.5,67.5,67.5,90,90,90"
            ),
            CommandParameter(
                name="n_bins",
                description="Number of resolution bins for statistics",
                param_type="int",
                default="20",
            ),
            CommandParameter(
                name="partiality_threshold",
                description="Partiality threshold for including reflections",
                param_type="float",
                default="0.4",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.split_experiments": CommandDefinition(
        name="dials.split_experiments",
        description="Split an experiment list into separate files.",
        category=CommandCategory.UTILITY,
        input_files=["*.expt", "*.refl"],
        output_files=["split_*.expt", "split_*.refl"],
        parameters=[],
        typical_runtime="seconds"
    ),
    
    "dials.combine_experiments": CommandDefinition(
        name="dials.combine_experiments",
        description=(
            "Combine multiple experiment and reflection files into one. "
            "Reference models can be chosen from any input to replace all others. "
            "Supports clustering and subsetting of experiments."
        ),
        category=CommandCategory.UTILITY,
        input_files=["*.expt", "*.refl"],
        output_files=["combined.expt", "combined.refl"],
        parameters=[
            CommandParameter(
                name="output.experiments_filename",
                description="Output experiments filename",
                default="combined.expt",
            ),
            CommandParameter(
                name="output.reflections_filename",
                description="Output reflections filename",
                default="combined.refl",
            ),
            CommandParameter(
                name="output.n_subset",
                description="Select a random subset of N experiments",
                param_type="int",
            ),
            CommandParameter(
                name="output.n_subset_method",
                description="Method for subsetting: random, n_refl, significance_filter",
                default="random",
            ),
            CommandParameter(
                name="reference_from_experiment.beam",
                description="Use beam model from this experiment index as reference",
                param_type="int",
                example="reference_from_experiment.beam=0"
            ),
            CommandParameter(
                name="reference_from_experiment.detector",
                description="Use detector model from this experiment index as reference",
                param_type="int",
                example="reference_from_experiment.detector=0"
            ),
            CommandParameter(
                name="reference_from_experiment.goniometer",
                description="Use goniometer model from this experiment index as reference",
                param_type="int",
            ),
            CommandParameter(
                name="reference_from_experiment.crystal",
                description="Use crystal model from this experiment index as reference",
                param_type="int",
            ),
            CommandParameter(
                name="clustering.use",
                description="Use unit cell clustering to group experiments",
                param_type="bool",
                default="False",
            ),
            CommandParameter(
                name="clustering.threshold",
                description="Clustering threshold",
                param_type="float",
                default="1000",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.generate_mask": CommandDefinition(
        name="dials.generate_mask",
        description=(
            "Generate pixel mask to exclude invalid pixels during spot finding and integration. "
            "Supports masking by detector trusted range, simple shapes (rectangle, circle, polygon), "
            "resolution ranges, and ice rings. Masks can be combined."
        ),
        category=CommandCategory.UTILITY,
        input_files=["*.expt"],
        output_files=["pixels.mask"],
        parameters=[
            CommandParameter(
                name="output.mask",
                description="Output mask filename",
                default="pixels.mask",
            ),
            CommandParameter(
                name="output.experiments",
                description="Save modified experiments with mask applied",
                example="output.experiments=masked.expt"
            ),
            CommandParameter(
                name="border",
                description="Border around edge of image to mask (pixels)",
                param_type="int",
                default="0",
                example="border=5"
            ),
            CommandParameter(
                name="d_min",
                description="High resolution limit for mask (Angstrom)",
                param_type="float",
                example="d_min=2.0"
            ),
            CommandParameter(
                name="d_max",
                description="Low resolution limit for mask (Angstrom)",
                param_type="float",
                example="d_max=20.0"
            ),
            CommandParameter(
                name="resolution_range",
                description="Untrusted resolution range (multiple allowed)",
                example="resolution_range=3.4,3.5"
            ),
            CommandParameter(
                name="untrusted.panel",
                description="Mask entire panel by panel number",
                param_type="int",
            ),
            CommandParameter(
                name="untrusted.rectangle",
                description="Untrusted rectangle region (x0, x1, y0, y1)",
                example="untrusted.rectangle=50,100,50,100"
            ),
            CommandParameter(
                name="untrusted.circle",
                description="Untrusted circle region (xc, yc, r)",
                example="untrusted.circle=200,200,100"
            ),
            CommandParameter(
                name="untrusted.polygon",
                description="Untrusted polygon (fast,slow pixel coordinates of corners)",
            ),
            CommandParameter(
                name="untrusted.pixel",
                description="Single untrusted pixel (y, x)",
                example="untrusted.pixel=100,200"
            ),
            CommandParameter(
                name="ice_rings.filter",
                description="Mask ice ring regions",
                param_type="bool",
                default="False",
                example="ice_rings.filter=True"
            ),
            CommandParameter(
                name="ice_rings.width",
                description="Width of ice ring mask (in 1/d^2)",
                param_type="float",
                default="0.002",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.apply_mask": CommandDefinition(
        name="dials.apply_mask",
        description="Apply a pixel mask to an experiment file.",
        category=CommandCategory.UTILITY,
        input_files=["*.expt", "pixels.mask"],
        output_files=["masked.expt"],
        parameters=[
            CommandParameter(
                name="output.experiments",
                description="Output experiment filename",
                default="masked.expt",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.filter_reflections": CommandDefinition(
        name="dials.filter_reflections",
        description=(
            "Filter reflections based on flags, resolution, partiality, and other criteria. "
            "Supports boolean flag expressions using &, |, ~ operators. "
            "If no filters are set, prints a table of flag values."
        ),
        category=CommandCategory.UTILITY,
        input_files=["*.refl"],
        output_files=["filtered.refl"],
        parameters=[
            CommandParameter(
                name="output.reflections",
                description="Output reflection filename",
                default="filtered.refl",
            ),
            CommandParameter(
                name="flag_expression",
                description="Boolean expression to select by flags (e.g., 'integrated & ~reference_spot')",
                example='flag_expression=used_in_refinement'
            ),
            CommandParameter(
                name="id",
                description="Select reflections by experiment IDs",
                example="id=0,1"
            ),
            CommandParameter(
                name="panel",
                description="Select reflections by panel numbers",
                param_type="int",
            ),
            CommandParameter(
                name="d_min",
                description="High resolution limit (Angstrom)",
                param_type="float",
                example="d_min=2.5"
            ),
            CommandParameter(
                name="d_max",
                description="Low resolution limit (Angstrom)",
                param_type="float",
                example="d_max=20"
            ),
            CommandParameter(
                name="partiality.min",
                description="Minimum partiality for inclusion",
                param_type="float",
            ),
            CommandParameter(
                name="partiality.max",
                description="Maximum partiality for inclusion",
                param_type="float",
            ),
            CommandParameter(
                name="select_good_intensities",
                description="Select only fully integrated and trustworthy intensities",
                param_type="bool",
                default="False",
            ),
            CommandParameter(
                name="ice_rings.filter",
                description="Filter reflections in ice ring regions",
                param_type="bool",
                default="False",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.search_beam_position": CommandDefinition(
        name="dials.search_beam_position",
        description=(
            "Find beam centre from diffraction images. Default method uses spot finding results "
            "(Sauter et al., 2004). Alternative projection methods (midpoint, maximum, inversion) "
            "only require an imported experiment."
        ),
        category=CommandCategory.UTILITY,
        input_files=["imported.expt", "strong.refl"],
        output_files=["optimised.expt"],
        parameters=[
            CommandParameter(
                name="method",
                description="Beam search method: default, midpoint, maximum, inversion",
                default="default",
                example="method=midpoint"
            ),
            CommandParameter(
                name="output.experiments",
                description="Output experiment filename",
                default="optimised.expt",
            ),
            CommandParameter(
                name="default.nproc",
                description="Number of processes for default method",
                default="Auto",
            ),
            CommandParameter(
                name="default.max_cell",
                description="Maximum cell dimension for default method",
                param_type="float",
            ),
            CommandParameter(
                name="default.image_range",
                description="Image range to use for beam search",
                example="default.image_range=1,100"
            ),
            CommandParameter(
                name="default.max_reflections",
                description="Maximum reflections to use",
                param_type="int",
                default="10000",
            ),
            CommandParameter(
                name="default.mm_search_scope",
                description="Search scope in mm",
                param_type="float",
                default="4.0",
            ),
            CommandParameter(
                name="default.n_macro_cycles",
                description="Number of macro-cycles",
                param_type="int",
                default="1",
            ),
            CommandParameter(
                name="default.d_min",
                description="High resolution limit for beam search",
                param_type="float",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.check_indexing_symmetry": CommandDefinition(
        name="dials.check_indexing_symmetry",
        description="Check the indexing symmetry of indexed reflections.",
        category=CommandCategory.UTILITY,
        input_files=["indexed.expt", "indexed.refl"],
        output_files=[],
        parameters=[
            CommandParameter(
                name="d_min",
                description="High resolution limit",
                param_type="float",
            ),
            CommandParameter(
                name="d_max",
                description="Low resolution limit",
                param_type="float",
            ),
            CommandParameter(
                name="grid_search_scope",
                description="Scope of grid search for checking misindexing",
                param_type="int",
                default="0",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.spot_counts_per_image": CommandDefinition(
        name="dials.spot_counts_per_image",
        description="Print spot counts per image for quality assessment.",
        category=CommandCategory.UTILITY,
        input_files=["*.refl"],
        output_files=[],
        parameters=[],
        typical_runtime="seconds"
    ),
    
    "dials.two_theta_refine": CommandDefinition(
        name="dials.two_theta_refine",
        description=(
            "Refine unit cell parameters using 2-theta angles from integrated data. "
            "Provides more accurate unit cell parameters than standard refinement."
        ),
        category=CommandCategory.UTILITY,
        input_files=["integrated.expt", "integrated.refl"],
        output_files=["refined_cell.expt"],
        parameters=[
            CommandParameter(
                name="output.experiments",
                description="Output experiment filename",
                default="refined_cell.expt",
            ),
            CommandParameter(
                name="output.log",
                description="Log filename",
                default="dials.two_theta_refine.log",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.estimate_gain": CommandDefinition(
        name="dials.estimate_gain",
        description="Estimate the detector gain from the images.",
        category=CommandCategory.UTILITY,
        input_files=["*.expt"],
        output_files=[],
        parameters=[
            CommandParameter(
                name="kernel_size",
                description="Size of the kernel for gain estimation",
                param_type="int",
                default="10",
            ),
            CommandParameter(
                name="max_images",
                description="Maximum number of images to use",
                param_type="int",
                default="1",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.predict": CommandDefinition(
        name="dials.predict",
        description="Predict reflection positions from an experiment model.",
        category=CommandCategory.UTILITY,
        input_files=["*.expt"],
        output_files=["predicted.refl"],
        parameters=[
            CommandParameter(
                name="output.reflections",
                description="Output reflection filename",
                default="predicted.refl",
            ),
            CommandParameter(
                name="d_min",
                description="High resolution limit (Angstrom)",
                param_type="float",
            ),
            CommandParameter(
                name="d_max",
                description="Low resolution limit (Angstrom)",
                param_type="float",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.align_crystal": CommandDefinition(
        name="dials.align_crystal",
        description=(
            "Calculate goniometer settings to align crystal axes with the beam or rotation axis. "
            "Useful for planning data collection strategy."
        ),
        category=CommandCategory.UTILITY,
        input_files=["*.expt"],
        output_files=[],
        parameters=[
            CommandParameter(
                name="align.crystal.vector",
                description="Crystal vector to align (e.g., a*, b*, c*)",
                example="align.crystal.vector=0,0,1"
            ),
            CommandParameter(
                name="align.frame",
                description="Frame to align to: laboratory or reciprocal",
                default="laboratory",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.anvil_correction": CommandDefinition(
        name="dials.anvil_correction",
        description=(
            "Apply anvil absorption correction for diamond anvil cell (DAC) experiments. "
            "Corrects for absorption by the diamond anvils."
        ),
        category=CommandCategory.UTILITY,
        input_files=["integrated.expt", "integrated.refl"],
        output_files=["corrected.refl"],
        parameters=[
            CommandParameter(
                name="output.reflections",
                description="Output reflection filename",
                default="corrected.refl",
            ),
            CommandParameter(
                name="anvil.thickness",
                description="Thickness of the anvil in mm",
                param_type="float",
                example="anvil.thickness=1.5925"
            ),
            CommandParameter(
                name="anvil.density",
                description="Density of the anvil material in g/cm^3",
                param_type="float",
                default="3.51",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.missing_reflections": CommandDefinition(
        name="dials.missing_reflections",
        description="Identify missing reflections in the dataset for completeness analysis.",
        category=CommandCategory.UTILITY,
        input_files=["*.expt", "*.refl"],
        output_files=[],
        parameters=[
            CommandParameter(
                name="d_min",
                description="High resolution limit",
                param_type="float",
            ),
            CommandParameter(
                name="d_max",
                description="Low resolution limit",
                param_type="float",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.import_xds": CommandDefinition(
        name="dials.import_xds",
        description="Import XDS processing results (XPARM.XDS, INTEGRATE.HKL, XDS_ASCII.HKL) into DIALS format.",
        category=CommandCategory.UTILITY,
        input_files=["XPARM.XDS", "INTEGRATE.HKL"],
        output_files=["imported.expt", "imported.refl"],
        parameters=[
            CommandParameter(
                name="output.experiments",
                description="Output experiment filename",
                default="imported.expt",
            ),
            CommandParameter(
                name="output.reflections",
                description="Output reflection filename",
                default="imported.refl",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.plot_scan_varying_model": CommandDefinition(
        name="dials.plot_scan_varying_model",
        description="Plot scan-varying crystal model parameters as a function of image number.",
        category=CommandCategory.UTILITY,
        input_files=["*.expt"],
        output_files=["scan_varying_model.png"],
        parameters=[
            CommandParameter(
                name="output",
                description="Output plot filename",
                default="scan_varying_model.png",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.stereographic_projection": CommandDefinition(
        name="dials.stereographic_projection",
        description="Generate stereographic projections of crystal orientations.",
        category=CommandCategory.UTILITY,
        input_files=["*.expt"],
        output_files=["stereographic_projection.png"],
        parameters=[
            CommandParameter(
                name="hkl",
                description="Miller indices for projection",
                example="hkl=1,0,0"
            ),
            CommandParameter(
                name="frame",
                description="Frame for projection: laboratory or crystal",
                default="laboratory",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.create_profile_model": CommandDefinition(
        name="dials.create_profile_model",
        description="Create a profile model from strong spots for use in integration.",
        category=CommandCategory.UTILITY,
        input_files=["*.expt", "*.refl"],
        output_files=["models_with_profiles.expt"],
        parameters=[
            CommandParameter(
                name="output",
                description="Output experiment filename",
                default="models_with_profiles.expt",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.merge_cbf": CommandDefinition(
        name="dials.merge_cbf",
        description="Merge multiple CBF files into a single image (e.g., for summing frames).",
        category=CommandCategory.UTILITY,
        input_files=["*.cbf"],
        output_files=["sum.cbf"],
        parameters=[
            CommandParameter(
                name="output.filename",
                description="Output CBF filename",
                default="sum.cbf",
            ),
            CommandParameter(
                name="merge_n_images",
                description="Number of images to merge",
                param_type="int",
                default="2",
            ),
        ],
        typical_runtime="seconds"
    ),
    
    # Visualization commands
    "dials.image_viewer": CommandDefinition(
        name="dials.image_viewer",
        description="Interactive viewer for diffraction images with spot overlay.",
        category=CommandCategory.VISUALIZATION,
        input_files=["*.expt"],
        output_files=[],
        parameters=[],
        requires_gui=True,
        typical_runtime="seconds"
    ),
    
    "dials.reciprocal_lattice_viewer": CommandDefinition(
        name="dials.reciprocal_lattice_viewer",
        description="3D viewer for reciprocal space showing indexed reflections.",
        category=CommandCategory.VISUALIZATION,
        input_files=["indexed.expt", "indexed.refl"],
        output_files=[],
        parameters=[],
        requires_gui=True,
        typical_runtime="seconds"
    ),
}


def get_command(name: str) -> Optional[CommandDefinition]:
    """
    Get a command definition by name.
    
    Args:
        name: Command name (e.g., 'dials.import')
        
    Returns:
        CommandDefinition or None if not found
    """
    return DIALS_COMMANDS.get(name)


def get_commands_by_category(category: CommandCategory) -> dict[str, CommandDefinition]:
    """
    Get all commands in a category.
    
    Args:
        category: The command category
        
    Returns:
        Dictionary of command name to definition
    """
    return {
        name: cmd for name, cmd in DIALS_COMMANDS.items()
        if cmd.category == category
    }


def get_workflow_commands() -> list[str]:
    """Get the ordered list of workflow commands."""
    return [
        "dials.import",
        "dials.find_spots",
        "dials.index",
        "dials.refine",
        "dials.integrate",
        "dials.symmetry",
        "dials.scale",
        "dials.export"
    ]


def validate_command(command_str: str) -> tuple[bool, str]:
    """
    Validate a DIALS command string.
    
    Args:
        command_str: The command string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    parts = command_str.strip().split()
    if not parts:
        return False, "Empty command"
    
    cmd_name = parts[0]
    
    # Check if it's a known DIALS command
    if not cmd_name.startswith("dials."):
        return False, f"Not a DIALS command: {cmd_name}"
    
    if cmd_name not in DIALS_COMMANDS:
        # Allow unknown dials.* commands but warn
        return True, f"Warning: Unknown DIALS command '{cmd_name}'"
    
    return True, ""


def get_next_workflow_command(current_files: list[str]) -> Optional[str]:
    """
    Suggest the next workflow command based on existing files.
    
    Args:
        current_files: List of files in the working directory
        
    Returns:
        Suggested next command or None if workflow is complete
    """
    file_set = set(current_files)
    
    # Check workflow progression
    if "scaled.mtz" in file_set:
        return None  # Workflow complete
    
    if "scaled.expt" in file_set and "scaled.refl" in file_set:
        return "dials.export"
    
    if "symmetrized.expt" in file_set and "symmetrized.refl" in file_set:
        return "dials.scale"
    
    if "integrated.expt" in file_set and "integrated.refl" in file_set:
        return "dials.symmetry"
    
    if "refined.expt" in file_set and "refined.refl" in file_set:
        return "dials.integrate"
    
    if "indexed.expt" in file_set and "indexed.refl" in file_set:
        return "dials.refine"
    
    if "imported.expt" in file_set and "strong.refl" in file_set:
        return "dials.index"
    
    if "imported.expt" in file_set:
        return "dials.image_viewer"
    
    return "dials.import"
