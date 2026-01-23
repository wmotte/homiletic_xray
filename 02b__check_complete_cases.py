#!/usr/bin/env python3
"""
Check for complete cases in the homiletic feedback JSON files.

This script identifies:
1. Missing analysis files (entire JSON files that don't exist)
2. Missing score fields within existing JSON files

Output: A table of problematic theologians/sermons/domains

W.M. Otte (w.m.otte@umcutrecht.nl)

Usage:
    python 03__check_complete_cases.py
"""

import json
from pathlib import Path
from collections import defaultdict
import csv
import sys

# Configuration
DOCS_DIR = Path("docs")
OUTPUT_FILE = Path("data/incomplete_cases_report.tsv")

# Known analysis types
ANALYSIS_TYPES = [
    'aristoteles', 'dekker', 'kolb', 'schulz_von_thun',
    'esthetiek', 'transactional', 'metaphor', 'speech_act', 'narrative'
]

# Critical score fields to check per analysis type (field path -> description)
# These are the key numeric scores that should always be present
# Note: Some fields like dekker.overall.average_score are computed by the converter
#       from sub-scores, so we check sub-scores instead
SCORE_FIELDS = {
    'aristoteles': [
        ('aristotelian_modes_analysis.logos.score', 'logos.score'),
        ('aristotelian_modes_analysis.pathos.score', 'pathos.score'),
        ('aristotelian_modes_analysis.ethos.score', 'ethos.score'),
        ('overall_picture.overall_rhetorical_score', 'overall.score'),
    ],
    'dekker': [
        # Check for at least one criterion score (average is computed from these)
        ('analysis_per_criterion.1_specific_bible_passage.score_1_to_10', 'specific_bible_passage.score'),
    ],
    'kolb': [
        ('kolb_phases_analysis.phase_1_concrete_experience.score', 'concrete_experience.score'),
        ('kolb_phases_analysis.phase_2_reflective_observation.score', 'reflective_observation.score'),
        ('kolb_phases_analysis.phase_3_abstract_conceptualization.score', 'abstract_conceptualization.score'),
        ('kolb_phases_analysis.phase_4_active_experimentation.score', 'active_experimentation.score'),
        ('overall_picture.overall_kolb_score', 'overall.score'),
    ],
    'schulz_von_thun': [
        ('schulz_von_thun_analysis.factual_content_blue.score', 'factual_content.score'),
        ('schulz_von_thun_analysis.self_revelation_green.score', 'self_revelation.score'),
        ('schulz_von_thun_analysis.relational_aspect_yellow.score', 'relational_aspect.score'),
        ('schulz_von_thun_analysis.appeal_aspect_red.score', 'appeal_aspect.score'),
        ('overall_picture.overall_communication_score', 'overall.score'),
    ],
    'esthetiek': [
        ('overall_aesthetics.overall_aesthetic_score', 'overall.score'),
    ],
    'transactional': [
        ('conclusion_and_recommendation.psychological_health_score', 'overall.score'),
    ],
    'metaphor': [
        ('diagnostische_evaluatie.coherentie_analyse.overall_coherentie', 'coherentie.overall'),
    ],
    'speech_act': [
        ('drievoudige_structuur_analyse.illocutie.helderheid_score', 'illocutie.helderheid_score'),
        ('diagnostische_evaluatie.gebeuren_score', 'diagnose.gebeuren_score'),
    ],
    'narrative': [
        ('diagnostische_evaluatie.narratieve_coherentie.coherentie_score', 'coherentie.score'),
    ],
}


def get_nested_value(data: dict, path: str):
    """Get a value from a nested dictionary using dot notation."""
    keys = path.split('.')
    value = data
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None
    return value


def parse_filename(filename: str) -> tuple[str, str, str] | None:
    """Parse a filename into (theologian, sermon_id, analysis_type).

    Handles both regular files (e.g., solle_01_aristoteles.json) and
    B-run files (e.g., solle_01_B_aristoteles.json).
    For B-run files, the sermon_id becomes '01_B'.
    """
    if not filename.endswith('.json'):
        return None

    skip_patterns = ['statistics', 'violin_data', 'file_index', '.raw']
    if any(pattern in filename for pattern in skip_patterns):
        return None

    base = filename.replace('.json', '')
    parts = base.split('_')

    if len(parts) < 3:
        return None

    theologian = parts[0]

    analysis_start_idx = None
    for i in range(1, len(parts)):
        for analysis_type in ANALYSIS_TYPES:
            analysis_parts = analysis_type.split('_')
            candidate = '_'.join(parts[i:i + len(analysis_parts)])
            if candidate == analysis_type:
                analysis_start_idx = i
                break
        if analysis_start_idx is not None:
            break

    if analysis_start_idx is None or analysis_start_idx < 2:
        sermon_id = parts[1]
        analysis = '_'.join(parts[2:])
    else:
        sermon_id = '_'.join(parts[1:analysis_start_idx])
        analysis = '_'.join(parts[analysis_start_idx:])

    return theologian, sermon_id, analysis


def check_complete_cases():
    """Check for complete cases and return list of problems."""
    problems = []

    # First, collect all existing files
    existing_files = defaultdict(set)  # (theologian, sermon_id) -> set of analysis_types

    if not DOCS_DIR.exists():
        print(f"Error: Directory {DOCS_DIR} not found")
        return problems

    json_files = list(DOCS_DIR.glob("*.json"))

    for filepath in json_files:
        parsed = parse_filename(filepath.name)
        if not parsed:
            continue

        theologian, sermon_id, analysis_type = parsed
        if analysis_type in ANALYSIS_TYPES:
            existing_files[(theologian, sermon_id)].add(analysis_type)

    # Get all unique sermons
    all_sermons = sorted(existing_files.keys())

    print(f"Checking {len(all_sermons)} sermons for completeness...\n")

    # Check each sermon
    for theologian, sermon_id in all_sermons:
        sermon_key = f"{theologian}_{sermon_id}"
        present_analyses = existing_files[(theologian, sermon_id)]

        # Check for missing files
        for analysis_type in ANALYSIS_TYPES:
            if analysis_type not in present_analyses:
                problems.append({
                    'theologian': theologian,
                    'sermon_id': sermon_id,
                    'sermon_key': sermon_key,
                    'domain': analysis_type,
                    'issue_type': 'missing_file',
                    'field': '',
                    'description': f'File {sermon_key}_{analysis_type}.json does not exist'
                })
            else:
                # File exists, check for missing score fields
                filepath = DOCS_DIR / f"{sermon_key}_{analysis_type}.json"
                if not filepath.exists():
                    # Try alternative naming
                    possible_files = list(DOCS_DIR.glob(f"{theologian}_{sermon_id}_{analysis_type}.json"))
                    if possible_files:
                        filepath = possible_files[0]
                    else:
                        continue

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    if isinstance(data, list) and len(data) > 0:
                        data = data[0]

                    if not isinstance(data, dict):
                        continue

                    # Check score fields for this analysis type
                    if analysis_type in SCORE_FIELDS:
                        for field_path, field_name in SCORE_FIELDS[analysis_type]:
                            value = get_nested_value(data, field_path)
                            if value is None or value == '':
                                problems.append({
                                    'theologian': theologian,
                                    'sermon_id': sermon_id,
                                    'sermon_key': sermon_key,
                                    'domain': analysis_type,
                                    'issue_type': 'missing_field',
                                    'field': field_name,
                                    'description': f'Field {field_path} is missing or empty'
                                })

                except (json.JSONDecodeError, IOError) as e:
                    problems.append({
                        'theologian': theologian,
                        'sermon_id': sermon_id,
                        'sermon_key': sermon_key,
                        'domain': analysis_type,
                        'issue_type': 'read_error',
                        'field': '',
                        'description': f'Error reading file: {e}'
                    })

    return problems


def print_summary(problems: list):
    """Print a summary of the problems found."""
    if not problems:
        print("=" * 70)
        print("ALL CASES COMPLETE - No missing data found!")
        print("=" * 70)
        return

    print("=" * 70)
    print("INCOMPLETE CASES REPORT")
    print("=" * 70)

    # Count by issue type
    missing_files = [p for p in problems if p['issue_type'] == 'missing_file']
    missing_fields = [p for p in problems if p['issue_type'] == 'missing_field']
    read_errors = [p for p in problems if p['issue_type'] == 'read_error']

    print(f"\nTotal issues found: {len(problems)}")
    print(f"  - Missing files: {len(missing_files)}")
    print(f"  - Missing fields: {len(missing_fields)}")
    print(f"  - Read errors: {len(read_errors)}")

    # Unique sermons affected
    affected_sermons = set(p['sermon_key'] for p in problems)
    print(f"\nSermons affected: {len(affected_sermons)}")

    # Group by theologian
    by_theologian = defaultdict(list)
    for p in problems:
        by_theologian[p['theologian']].append(p)

    print(f"\nIssues by theologian:")
    for theologian in sorted(by_theologian.keys()):
        issues = by_theologian[theologian]
        sermons = set(p['sermon_key'] for p in issues)
        print(f"  - {theologian}: {len(issues)} issues in {len(sermons)} sermon(s)")

    # Print detailed table
    print("\n" + "=" * 70)
    print("DETAILED ISSUE TABLE")
    print("=" * 70)
    print(f"\n{'Theologian':<15} {'Sermon':<12} {'Domain':<18} {'Type':<15} {'Field':<30}")
    print("-" * 90)

    for p in sorted(problems, key=lambda x: (x['theologian'], x['sermon_id'], x['domain'])):
        field_display = p['field'] if p['field'] else '-'
        print(f"{p['theologian']:<15} {p['sermon_id']:<12} {p['domain']:<18} {p['issue_type']:<15} {field_display:<30}")


def save_report(problems: list):
    """Save the problems to a TSV file."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f,
                               fieldnames=['theologian', 'sermon_id', 'sermon_key', 'domain', 'issue_type', 'field', 'description'],
                               delimiter='\t')
        writer.writeheader()
        writer.writerows(problems)

    print(f"\nReport saved to: {OUTPUT_FILE}")


def main():
    print("=" * 70)
    print("CHECK COMPLETE CASES")
    print("=" * 70)
    print()

    problems = check_complete_cases()
    print_summary(problems)

    if problems:
        save_report(problems)

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)

    # Return exit code based on completeness
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
