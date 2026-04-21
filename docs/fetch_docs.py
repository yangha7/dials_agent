#!/usr/bin/env python3
"""Fetch DIALS program documentation from the official website and save as markdown files."""

import os
import re
import html
import urllib.request

BASE_URL = "https://dials.github.io/documentation/programs/"

MAIN_PROGRAMS = [
    "dials_import",
    "dials_find_spots",
    "dials_index",
    "dials_refine_bravais_settings",
    "dials_reindex",
    "dials_refine",
    "dials_integrate",
    "dials_two_theta_refine",
    "dials_cosym",
    "dials_symmetry",
    "dials_scale",
    "dials_export",
]

UTILITY_PROGRAMS = [
    "dials_show",
    "dials_image_viewer",
    "dials_generate_mask",
    "dials_check_indexing_symmetry",
    "dials_search_beam_position",
    "dials_report",
    "dials_plot_scan_varying_model",
    "dials_find_spots_server",
    "dials_apply_mask",
    "dials_create_profile_model",
    "dials_estimate_gain",
    "dials_estimate_resolution",
    "dials_predict",
    "dials_merge_cbf",
    "dials_spot_counts_per_image",
    "dials_stereographic_projection",
    "dials_combine_experiments",
    "dials_align_crystal",
    "dials_anvil_correction",
    "dials_missing_reflections",
    "dials_filter_reflections",
    "dials_import_xds",
]

def fetch_and_clean(page_name):
    """Fetch a DIALS documentation page and extract the body text as markdown."""
    url = f"{BASE_URL}{page_name}.html"
    print(f"Fetching {url}...")
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            html_content = response.read().decode('utf-8')
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return None
    
    # Extract body content between <div class="body" and <div class="sphinxsidebar"
    body_match = re.search(r'<div class="body"[^>]*>(.*?)<div class="sphinxsidebar"', html_content, re.DOTALL)
    if not body_match:
        # Try alternative pattern
        body_match = re.search(r'<div class="body"[^>]*>(.*?)$', html_content, re.DOTALL)
    
    if not body_match:
        print(f"  Could not find body content for {page_name}")
        return None
    
    body = body_match.group(1)
    
    # Convert some HTML to markdown
    # Headers
    body = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1', body)
    body = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1', body)
    body = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1', body)
    body = re.sub(r'<h4[^>]*>(.*?)</h4>', r'#### \1', body)
    
    # Code blocks
    body = re.sub(r'<pre[^>]*>(.*?)</pre>', r'```\n\1\n```', body, flags=re.DOTALL)
    body = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', body)
    
    # Remove all remaining HTML tags
    body = re.sub(r'<[^>]+>', '', body)
    
    # Decode HTML entities
    body = html.unescape(body)
    
    # Remove pilcrow signs
    body = body.replace('¶', '')
    
    # Clean up excessive whitespace but preserve structure
    lines = body.split('\n')
    cleaned_lines = []
    prev_empty = False
    for line in lines:
        stripped = line.rstrip()
        if not stripped:
            if not prev_empty:
                cleaned_lines.append('')
                prev_empty = True
        else:
            cleaned_lines.append(stripped)
            prev_empty = False
    
    return '\n'.join(cleaned_lines).strip()


def main():
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "programs")
    os.makedirs(output_dir, exist_ok=True)
    
    print("=== Main Processing Commands ===")
    for page in MAIN_PROGRAMS:
        content = fetch_and_clean(page)
        if content:
            output_path = os.path.join(output_dir, f"{page}.md")
            with open(output_path, 'w') as f:
                f.write(content)
            line_count = content.count('\n') + 1
            print(f"  Saved {output_path} ({line_count} lines)")
        else:
            print(f"  FAILED: {page}")
    
    print("\n=== Utility Programs ===")
    for page in UTILITY_PROGRAMS:
        content = fetch_and_clean(page)
        if content:
            output_path = os.path.join(output_dir, f"{page}.md")
            with open(output_path, 'w') as f:
                f.write(content)
            line_count = content.count('\n') + 1
            print(f"  Saved {output_path} ({line_count} lines)")
        else:
            print(f"  FAILED: {page}")
    
    print("\nDone!")


if __name__ == "__main__":
    main()
