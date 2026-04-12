"""
DIALS output parser.

This module parses the output from DIALS commands to extract key metrics
and provide human-readable summaries.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from .executor import CommandResult


@dataclass
class ParsedMetrics:
    """Parsed metrics from DIALS output."""
    command: str
    success: bool
    summary: str
    metrics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class OutputParser:
    """
    Parses DIALS command output to extract metrics and generate summaries.
    """
    
    def parse(self, result: CommandResult) -> ParsedMetrics:
        """
        Parse the output from a command execution.
        
        Args:
            result: CommandResult from executor
            
        Returns:
            ParsedMetrics with extracted information
        """
        # Determine which parser to use based on command
        command_name = result.command.split()[0] if result.command else ""
        
        parser_map = {
            "dials.import": self._parse_import,
            "dials.find_spots": self._parse_find_spots,
            "dials.index": self._parse_index,
            "dials.refine": self._parse_refine,
            "dials.integrate": self._parse_integrate,
            "dials.symmetry": self._parse_symmetry,
            "dials.cosym": self._parse_cosym,
            "dials.scale": self._parse_scale,
            "dials.export": self._parse_export,
            "dials.show": self._parse_show,
        }
        
        parser = parser_map.get(command_name, self._parse_generic)
        return parser(result)
    
    def _extract_warnings(self, output: str) -> list[str]:
        """Extract warning messages from output."""
        warnings = []
        for line in output.split('\n'):
            if 'warning' in line.lower() or 'WARNING' in line:
                warnings.append(line.strip())
        return warnings
    
    def _extract_errors(self, output: str) -> list[str]:
        """Extract error messages from output."""
        errors = []
        combined = output
        for line in combined.split('\n'):
            if 'error' in line.lower() or 'ERROR' in line or 'Exception' in line:
                errors.append(line.strip())
        return errors
    
    def _parse_import(self, result: CommandResult) -> ParsedMetrics:
        """Parse dials.import output."""
        output = result.stdout + result.stderr
        metrics = {}
        
        # Extract number of images
        match = re.search(r'(\d+)\s+images', output, re.IGNORECASE)
        if match:
            metrics['num_images'] = int(match.group(1))
        
        # Extract number of sequences/sweeps
        match = re.search(r'(\d+)\s+(?:sequence|sweep)', output, re.IGNORECASE)
        if match:
            metrics['num_sequences'] = int(match.group(1))
        
        # Extract detector info
        match = re.search(r'Detector:\s*(.+)', output)
        if match:
            metrics['detector'] = match.group(1).strip()
        
        # Extract wavelength
        match = re.search(r'wavelength[:\s]+(\d+\.?\d*)', output, re.IGNORECASE)
        if match:
            metrics['wavelength'] = float(match.group(1))
        
        # Generate summary
        if result.success:
            parts = []
            if 'num_images' in metrics:
                parts.append(f"{metrics['num_images']} images")
            if 'num_sequences' in metrics:
                parts.append(f"{metrics['num_sequences']} sequence(s)")
            summary = f"Successfully imported {', '.join(parts) if parts else 'data'}."
            if result.output_files:
                summary += f" Created: {', '.join(result.output_files)}"
        else:
            summary = "Import failed. Check file paths and image format."
        
        return ParsedMetrics(
            command=result.command,
            success=result.success,
            summary=summary,
            metrics=metrics,
            warnings=self._extract_warnings(output),
            errors=self._extract_errors(output) if not result.success else []
        )
    
    def _parse_find_spots(self, result: CommandResult) -> ParsedMetrics:
        """Parse dials.find_spots output."""
        output = result.stdout + result.stderr
        metrics = {}
        
        # Extract total spots
        match = re.search(r'Found\s+(\d+)\s+(?:strong\s+)?spots?', output, re.IGNORECASE)
        if match:
            metrics['total_spots'] = int(match.group(1))
        
        # Alternative pattern
        if 'total_spots' not in metrics:
            match = re.search(r'(\d+)\s+spots?\s+found', output, re.IGNORECASE)
            if match:
                metrics['total_spots'] = int(match.group(1))
        
        # Extract spots per image statistics
        match = re.search(r'Spots per image:\s*min=(\d+),\s*max=(\d+),\s*mean=(\d+\.?\d*)', output)
        if match:
            metrics['spots_per_image_min'] = int(match.group(1))
            metrics['spots_per_image_max'] = int(match.group(2))
            metrics['spots_per_image_mean'] = float(match.group(3))
        
        # Generate summary
        if result.success:
            if 'total_spots' in metrics:
                summary = f"Found {metrics['total_spots']:,} strong spots."
                if 'spots_per_image_mean' in metrics:
                    summary += f" Average {metrics['spots_per_image_mean']:.0f} spots per image."
                
                # Quality assessment
                total = metrics['total_spots']
                if total < 1000:
                    summary += " ⚠️ Low spot count - may have difficulty indexing."
                elif total > 100000:
                    summary += " ⚠️ Very high spot count - consider increasing threshold."
            else:
                summary = "Spot finding completed."
            
            if result.output_files:
                summary += f" Created: {', '.join(result.output_files)}"
        else:
            summary = "Spot finding failed."
        
        suggestions = []
        if metrics.get('total_spots', 0) < 1000:
            suggestions.append("Try lowering sigma_strong threshold to find more spots")
        elif metrics.get('total_spots', 0) > 100000:
            suggestions.append("Try increasing sigma_strong threshold to reduce spot count")
        
        return ParsedMetrics(
            command=result.command,
            success=result.success,
            summary=summary,
            metrics=metrics,
            warnings=self._extract_warnings(output),
            errors=self._extract_errors(output) if not result.success else [],
            suggestions=suggestions
        )
    
    def _parse_index(self, result: CommandResult) -> ParsedMetrics:
        """Parse dials.index output."""
        output = result.stdout + result.stderr
        metrics = {}
        
        # Extract unit cell
        match = re.search(
            r'Unit cell:\s*\(?\s*(\d+\.?\d*)[,\s]+(\d+\.?\d*)[,\s]+(\d+\.?\d*)[,\s]+(\d+\.?\d*)[,\s]+(\d+\.?\d*)[,\s]+(\d+\.?\d*)',
            output
        )
        if match:
            metrics['unit_cell'] = {
                'a': float(match.group(1)),
                'b': float(match.group(2)),
                'c': float(match.group(3)),
                'alpha': float(match.group(4)),
                'beta': float(match.group(5)),
                'gamma': float(match.group(6))
            }
        
        # Extract space group
        match = re.search(r'Space group:\s*(\S+)', output)
        if match:
            metrics['space_group'] = match.group(1)
        
        # Extract indexed percentage
        match = re.search(r'(\d+\.?\d*)\s*%\s*(?:of\s+)?(?:reflections?\s+)?indexed', output, re.IGNORECASE)
        if match:
            metrics['indexed_percentage'] = float(match.group(1))
        
        # Alternative: extract indexed/total counts
        match = re.search(r'Indexed\s+(\d+)\s+(?:reflections?\s+)?out of\s+(\d+)', output, re.IGNORECASE)
        if match:
            indexed = int(match.group(1))
            total = int(match.group(2))
            metrics['indexed_count'] = indexed
            metrics['total_spots'] = total
            if 'indexed_percentage' not in metrics:
                metrics['indexed_percentage'] = (indexed / total * 100) if total > 0 else 0
        
        # Extract RMS deviation
        match = re.search(r'RMS\s+(?:deviation|residual)[:\s]+(\d+\.?\d*)', output, re.IGNORECASE)
        if match:
            metrics['rms_deviation'] = float(match.group(1))
        
        # Extract number of lattices
        match = re.search(r'(\d+)\s+(?:lattice|crystal)', output, re.IGNORECASE)
        if match:
            metrics['num_lattices'] = int(match.group(1))
        
        # Generate summary
        if result.success:
            parts = []
            if 'space_group' in metrics:
                parts.append(f"Space group: {metrics['space_group']}")
            if 'unit_cell' in metrics:
                uc = metrics['unit_cell']
                parts.append(f"Unit cell: {uc['a']:.1f}, {uc['b']:.1f}, {uc['c']:.1f} Å")
            if 'indexed_percentage' in metrics:
                parts.append(f"{metrics['indexed_percentage']:.1f}% indexed")
            if 'rms_deviation' in metrics:
                parts.append(f"RMS: {metrics['rms_deviation']:.3f}")
            
            summary = "Indexing successful. " + "; ".join(parts) if parts else "Indexing completed."
            
            if result.output_files:
                summary += f" Created: {', '.join(result.output_files)}"
        else:
            summary = "Indexing failed. No solution found."
        
        # Suggestions
        suggestions = []
        if not result.success:
            suggestions.extend([
                "Try a different indexing method: indexing.method=fft1d",
                "If you know the unit cell, provide it: unit_cell=a,b,c,alpha,beta,gamma",
                "Check for multiple lattices: max_lattices=2"
            ])
        elif metrics.get('indexed_percentage', 100) < 70:
            suggestions.append("Low indexed percentage - consider checking for multiple lattices")
        
        return ParsedMetrics(
            command=result.command,
            success=result.success,
            summary=summary,
            metrics=metrics,
            warnings=self._extract_warnings(output),
            errors=self._extract_errors(output) if not result.success else [],
            suggestions=suggestions
        )
    
    def _parse_refine(self, result: CommandResult) -> ParsedMetrics:
        """Parse dials.refine output."""
        output = result.stdout + result.stderr
        metrics = {}
        
        # Extract final RMS
        match = re.search(r'Final\s+RMS[:\s]+(\d+\.?\d*)', output, re.IGNORECASE)
        if match:
            metrics['final_rms'] = float(match.group(1))
        
        # Extract RMS in x and y
        match = re.search(r'RMS\s+\(x,\s*y\)[:\s]+\((\d+\.?\d*),\s*(\d+\.?\d*)\)', output)
        if match:
            metrics['rms_x'] = float(match.group(1))
            metrics['rms_y'] = float(match.group(2))
        
        # Extract refined unit cell
        match = re.search(
            r'Refined\s+unit\s+cell[:\s]+\(?\s*(\d+\.?\d*)[,\s]+(\d+\.?\d*)[,\s]+(\d+\.?\d*)',
            output, re.IGNORECASE
        )
        if match:
            metrics['refined_unit_cell'] = {
                'a': float(match.group(1)),
                'b': float(match.group(2)),
                'c': float(match.group(3))
            }
        
        # Generate summary
        if result.success:
            parts = []
            if 'final_rms' in metrics:
                parts.append(f"Final RMS: {metrics['final_rms']:.4f}")
            if 'rms_x' in metrics and 'rms_y' in metrics:
                parts.append(f"RMS (x,y): ({metrics['rms_x']:.4f}, {metrics['rms_y']:.4f})")
            
            summary = "Refinement successful. " + "; ".join(parts) if parts else "Refinement completed."
            
            if result.output_files:
                summary += f" Created: {', '.join(result.output_files)}"
        else:
            summary = "Refinement failed."
        
        suggestions = []
        if metrics.get('final_rms', 0) > 0.5:
            suggestions.append("High RMS - consider checking detector geometry or beam center")
        
        return ParsedMetrics(
            command=result.command,
            success=result.success,
            summary=summary,
            metrics=metrics,
            warnings=self._extract_warnings(output),
            errors=self._extract_errors(output) if not result.success else [],
            suggestions=suggestions
        )
    
    def _parse_integrate(self, result: CommandResult) -> ParsedMetrics:
        """Parse dials.integrate output."""
        output = result.stdout + result.stderr
        metrics = {}
        
        # Extract integrated reflections count
        match = re.search(r'(\d+)\s+(?:reflections?\s+)?integrated', output, re.IGNORECASE)
        if match:
            metrics['integrated_count'] = int(match.group(1))
        
        # Extract resolution
        match = re.search(r'Resolution[:\s]+(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', output, re.IGNORECASE)
        if match:
            metrics['resolution_low'] = float(match.group(1))
            metrics['resolution_high'] = float(match.group(2))
        
        # Extract I/sigma
        match = re.search(r'<I/sigma>[:\s]+(\d+\.?\d*)', output, re.IGNORECASE)
        if match:
            metrics['mean_i_sigma'] = float(match.group(1))
        
        # Generate summary
        if result.success:
            parts = []
            if 'integrated_count' in metrics:
                parts.append(f"{metrics['integrated_count']:,} reflections integrated")
            if 'resolution_high' in metrics:
                parts.append(f"Resolution: {metrics['resolution_high']:.2f} Å")
            if 'mean_i_sigma' in metrics:
                parts.append(f"<I/σ>: {metrics['mean_i_sigma']:.1f}")
            
            summary = "Integration successful. " + "; ".join(parts) if parts else "Integration completed."
            
            if result.output_files:
                summary += f" Created: {', '.join(result.output_files)}"
        else:
            summary = "Integration failed."
        
        return ParsedMetrics(
            command=result.command,
            success=result.success,
            summary=summary,
            metrics=metrics,
            warnings=self._extract_warnings(output),
            errors=self._extract_errors(output) if not result.success else []
        )
    
    def _parse_symmetry(self, result: CommandResult) -> ParsedMetrics:
        """Parse dials.symmetry output."""
        output = result.stdout + result.stderr
        metrics = {}
        
        # Extract best space group
        match = re.search(r'Best\s+(?:space\s+)?group[:\s]+(\S+)', output, re.IGNORECASE)
        if match:
            metrics['space_group'] = match.group(1)
        
        # Extract Patterson group
        match = re.search(r'Patterson\s+group[:\s]+(\S+)', output, re.IGNORECASE)
        if match:
            metrics['patterson_group'] = match.group(1)
        
        # Extract confidence
        match = re.search(r'Confidence[:\s]+(\d+\.?\d*)', output, re.IGNORECASE)
        if match:
            metrics['confidence'] = float(match.group(1))
        
        # Generate summary
        if result.success:
            parts = []
            if 'space_group' in metrics:
                parts.append(f"Space group: {metrics['space_group']}")
            if 'confidence' in metrics:
                parts.append(f"Confidence: {metrics['confidence']:.1f}%")
            
            summary = "Symmetry determination successful. " + "; ".join(parts) if parts else "Symmetry analysis completed."
            
            if result.output_files:
                summary += f" Created: {', '.join(result.output_files)}"
        else:
            summary = "Symmetry determination failed."
        
        return ParsedMetrics(
            command=result.command,
            success=result.success,
            summary=summary,
            metrics=metrics,
            warnings=self._extract_warnings(output),
            errors=self._extract_errors(output) if not result.success else []
        )
    
    def _parse_cosym(self, result: CommandResult) -> ParsedMetrics:
        """Parse dials.cosym output."""
        output = result.stdout + result.stderr
        metrics = {}
        
        # Extract space group
        match = re.search(r'(?:Best|Determined)\s+space\s+group[:\s]+(\S+)', output, re.IGNORECASE)
        if match:
            metrics['space_group'] = match.group(1)
        
        # Extract reindexing operations
        match = re.search(r'(\d+)\s+(?:datasets?\s+)?reindexed', output, re.IGNORECASE)
        if match:
            metrics['reindexed_count'] = int(match.group(1))
        
        # Generate summary
        if result.success:
            parts = []
            if 'space_group' in metrics:
                parts.append(f"Space group: {metrics['space_group']}")
            if 'reindexed_count' in metrics:
                parts.append(f"{metrics['reindexed_count']} datasets reindexed")
            
            summary = "Cosym analysis successful. " + "; ".join(parts) if parts else "Cosym completed."
            
            if result.output_files:
                summary += f" Created: {', '.join(result.output_files)}"
        else:
            summary = "Cosym analysis failed."
        
        return ParsedMetrics(
            command=result.command,
            success=result.success,
            summary=summary,
            metrics=metrics,
            warnings=self._extract_warnings(output),
            errors=self._extract_errors(output) if not result.success else []
        )
    
    def _parse_scale(self, result: CommandResult) -> ParsedMetrics:
        """Parse dials.scale output."""
        output = result.stdout + result.stderr
        metrics = {}
        
        # Extract Rmerge
        match = re.search(r'R(?:merge|meas)[:\s]+(\d+\.?\d*)\s*%?', output, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            metrics['rmerge'] = value if value < 1 else value / 100  # Handle percentage
        
        # Extract CC1/2
        match = re.search(r'CC1/2[:\s]+(\d+\.?\d*)', output, re.IGNORECASE)
        if match:
            metrics['cc_half'] = float(match.group(1))
        
        # Extract completeness
        match = re.search(r'Completeness[:\s]+(\d+\.?\d*)\s*%?', output, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            metrics['completeness'] = value if value <= 1 else value / 100
        
        # Extract multiplicity
        match = re.search(r'Multiplicity[:\s]+(\d+\.?\d*)', output, re.IGNORECASE)
        if match:
            metrics['multiplicity'] = float(match.group(1))
        
        # Extract resolution
        match = re.search(r'Resolution[:\s]+(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', output, re.IGNORECASE)
        if match:
            metrics['resolution_low'] = float(match.group(1))
            metrics['resolution_high'] = float(match.group(2))
        
        # Extract I/sigma
        match = re.search(r'<I/sigma>[:\s]+(\d+\.?\d*)', output, re.IGNORECASE)
        if match:
            metrics['mean_i_sigma'] = float(match.group(1))
        
        # Generate summary
        if result.success:
            parts = []
            if 'rmerge' in metrics:
                rmerge_pct = metrics['rmerge'] * 100 if metrics['rmerge'] < 1 else metrics['rmerge']
                parts.append(f"Rmerge: {rmerge_pct:.1f}%")
            if 'cc_half' in metrics:
                parts.append(f"CC1/2: {metrics['cc_half']:.3f}")
            if 'completeness' in metrics:
                comp_pct = metrics['completeness'] * 100 if metrics['completeness'] <= 1 else metrics['completeness']
                parts.append(f"Completeness: {comp_pct:.1f}%")
            if 'multiplicity' in metrics:
                parts.append(f"Multiplicity: {metrics['multiplicity']:.1f}")
            if 'resolution_high' in metrics:
                parts.append(f"Resolution: {metrics['resolution_high']:.2f} Å")
            
            summary = "Scaling successful. " + "; ".join(parts) if parts else "Scaling completed."
            
            # Quality assessment
            if 'rmerge' in metrics:
                rmerge = metrics['rmerge'] if metrics['rmerge'] < 1 else metrics['rmerge'] / 100
                if rmerge < 0.05:
                    summary += " ✓ Excellent Rmerge."
                elif rmerge < 0.10:
                    summary += " ✓ Good Rmerge."
                elif rmerge > 0.15:
                    summary += " ⚠️ High Rmerge - check for problems."
            
            if result.output_files:
                summary += f" Created: {', '.join(result.output_files)}"
        else:
            summary = "Scaling failed."
        
        suggestions = []
        if metrics.get('rmerge', 0) > 0.15:
            suggestions.extend([
                "High Rmerge may indicate non-isomorphism or radiation damage",
                "Try applying outlier rejection: outlier_rejection=simple"
            ])
        
        return ParsedMetrics(
            command=result.command,
            success=result.success,
            summary=summary,
            metrics=metrics,
            warnings=self._extract_warnings(output),
            errors=self._extract_errors(output) if not result.success else [],
            suggestions=suggestions
        )
    
    def _parse_export(self, result: CommandResult) -> ParsedMetrics:
        """Parse dials.export output."""
        output = result.stdout + result.stderr
        metrics = {}
        
        # Extract output file
        match = re.search(r'(?:Writing|Exported\s+to)[:\s]+(\S+\.mtz)', output, re.IGNORECASE)
        if match:
            metrics['output_file'] = match.group(1)
        
        # Extract reflection count
        match = re.search(r'(\d+)\s+reflections?\s+(?:written|exported)', output, re.IGNORECASE)
        if match:
            metrics['reflection_count'] = int(match.group(1))
        
        # Generate summary
        if result.success:
            parts = []
            if 'output_file' in metrics:
                parts.append(f"Output: {metrics['output_file']}")
            if 'reflection_count' in metrics:
                parts.append(f"{metrics['reflection_count']:,} reflections")
            
            summary = "Export successful. " + "; ".join(parts) if parts else "Export completed."
            
            if result.output_files:
                summary += f" Created: {', '.join(result.output_files)}"
        else:
            summary = "Export failed."
        
        return ParsedMetrics(
            command=result.command,
            success=result.success,
            summary=summary,
            metrics=metrics,
            warnings=self._extract_warnings(output),
            errors=self._extract_errors(output) if not result.success else []
        )
    
    def _parse_show(self, result: CommandResult) -> ParsedMetrics:
        """Parse dials.show output."""
        output = result.stdout
        metrics = {}
        
        # Extract experiment info
        match = re.search(r'(\d+)\s+experiment', output, re.IGNORECASE)
        if match:
            metrics['num_experiments'] = int(match.group(1))
        
        # Extract reflection info
        match = re.search(r'(\d+)\s+reflection', output, re.IGNORECASE)
        if match:
            metrics['num_reflections'] = int(match.group(1))
        
        # Extract unit cell
        match = re.search(
            r'Unit cell:\s*\(?\s*(\d+\.?\d*)[,\s]+(\d+\.?\d*)[,\s]+(\d+\.?\d*)',
            output
        )
        if match:
            metrics['unit_cell'] = {
                'a': float(match.group(1)),
                'b': float(match.group(2)),
                'c': float(match.group(3))
            }
        
        # Extract space group
        match = re.search(r'Space group:\s*(\S+)', output)
        if match:
            metrics['space_group'] = match.group(1)
        
        # Generate summary
        summary = "File information retrieved."
        parts = []
        if 'num_experiments' in metrics:
            parts.append(f"{metrics['num_experiments']} experiment(s)")
        if 'num_reflections' in metrics:
            parts.append(f"{metrics['num_reflections']:,} reflections")
        if 'space_group' in metrics:
            parts.append(f"Space group: {metrics['space_group']}")
        
        if parts:
            summary = "; ".join(parts)
        
        return ParsedMetrics(
            command=result.command,
            success=result.success,
            summary=summary,
            metrics=metrics,
            warnings=self._extract_warnings(output),
            errors=[]
        )
    
    def _parse_generic(self, result: CommandResult) -> ParsedMetrics:
        """Generic parser for unknown commands."""
        output = result.stdout + result.stderr
        
        if result.success:
            summary = f"Command completed successfully in {result.duration:.1f}s."
            if result.output_files:
                summary += f" Created: {', '.join(result.output_files)}"
        else:
            summary = f"Command failed with return code {result.return_code}."
            if result.error_message:
                summary += f" Error: {result.error_message}"
        
        return ParsedMetrics(
            command=result.command,
            success=result.success,
            summary=summary,
            metrics={},
            warnings=self._extract_warnings(output),
            errors=self._extract_errors(output) if not result.success else []
        )


def create_parser() -> OutputParser:
    """Create a new output parser instance."""
    return OutputParser()
