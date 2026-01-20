#!/usr/bin/env python3
"""
Convert homiletic feedback JSON files to a single TSV file for analysis in R.

This script reads all JSON analysis files from the docs directory,
groups them by sermon (theologian + sermon_id), and creates one row per sermon
with all information from the 6 analysis domains (aristoteles, dekker, kolb,
schulz_von_thun, esthetiek, transactional).

W.M. Otte (w.m.otte@umcutrecht.nl)

Usage:
    python json_to_tsv_converter.py

Output:
    homiletic_feedback_data.tsv in the current directory
"""

import json
import csv
from pathlib import Path
from collections import defaultdict
from typing import Any


# Configuration
DOCS_DIR = Path("docs")
OUTPUT_FILE = Path("data/homiletic_feedback_data.tsv")

# Known analysis types
ANALYSIS_TYPES = ['aristoteles', 'dekker', 'kolb', 'schulz_von_thun', 'esthetiek', 'transactional']


def parse_filename(filename: str) -> tuple[str, str, str] | None:
    """
    Parse a filename like 'augustine_01_aristoteles.json' into components.
    Returns (theologian, sermon_id, analysis_type) or None if invalid.
    """
    if not filename.endswith('.json'):
        return None

    # Skip special files
    skip_patterns = ['statistics', 'violin_data', 'file_index', '.raw']
    if any(pattern in filename for pattern in skip_patterns):
        return None

    base = filename.replace('.json', '')
    parts = base.split('_')

    if len(parts) < 3:
        return None

    theologian = parts[0]

    # Find where the analysis type starts
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
        # Fallback
        sermon_id = parts[1]
        analysis = '_'.join(parts[2:])
    else:
        sermon_id = '_'.join(parts[1:analysis_start_idx])
        analysis = '_'.join(parts[analysis_start_idx:])

    return theologian, sermon_id, analysis


def serialize_value(value: Any) -> str:
    """
    Convert any value to a string representation suitable for TSV.
    Lists and dicts are converted to JSON strings.
    Newlines are replaced with spaces to prevent TSV corruption.
    """
    if value is None:
        return ""
    elif isinstance(value, (list, dict)):
        json_str = json.dumps(value, ensure_ascii=False)
        # Replace newlines in JSON strings
        return json_str.replace('\n', ' ').replace('\r', '')
    elif isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    elif isinstance(value, (int, float)):
        return str(value)
    else:
        # Replace newlines in regular strings
        return str(value).replace('\n', ' ').replace('\r', '')


def flatten_dict(data: dict, parent_key: str = '', sep: str = '.') -> dict:
    """
    Flatten a nested dictionary.

    Example:
        {'a': {'b': 1, 'c': 2}} -> {'a.b': 1, 'a.c': 2}
    """
    items = []
    for k, v in data.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k

        if isinstance(v, dict) and not any(isinstance(vv, (list, dict)) for vv in v.values()):
            # If dict contains only simple values, flatten it
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            # Otherwise keep the value as is (will be serialized later)
            items.append((new_key, v))

    return dict(items)


def extract_analysis_data(data: dict, analysis_type: str) -> dict:
    """
    Extract all relevant data from an analysis JSON.
    Returns a flattened dictionary with prefixed keys.
    """
    result = {}

    # Add metadata
    if 'metadata' in data:
        for key, value in data['metadata'].items():
            result[f'metadata.{key}'] = serialize_value(value)

    # Extract analysis-specific data
    if analysis_type == 'aristoteles':
        # Aristotelian modes
        modes = data.get('aristotelian_modes_analysis', {})
        for mode in ['logos', 'pathos', 'ethos']:
            if mode in modes:
                mode_data = modes[mode]
                result[f'aristoteles.{mode}.score'] = mode_data.get('score', '')
                result[f'aristoteles.{mode}.analysis'] = serialize_value(mode_data.get('analysis', ''))
                result[f'aristoteles.{mode}.quotes'] = serialize_value(mode_data.get('quotes', []))
                result[f'aristoteles.{mode}.strengths'] = serialize_value(mode_data.get('strengths', []))
                result[f'aristoteles.{mode}.improvement_points'] = serialize_value(mode_data.get('improvement_points', []))
                result[f'aristoteles.{mode}.specific_diagnosis'] = serialize_value(mode_data.get('specific_diagnosis', ''))
                if mode == 'pathos':
                    result[f'aristoteles.{mode}.emotional_tone'] = serialize_value(mode_data.get('emotional_tone', ''))
                if mode == 'ethos':
                    result[f'aristoteles.{mode}.authenticity'] = serialize_value(mode_data.get('authenticity', ''))

        # Balance analysis
        balance = data.get('rhetorical_balance_analysis', {})
        result['aristoteles.balance.dominant_mode'] = serialize_value(balance.get('dominant_mode', ''))
        result['aristoteles.balance.suppressed_mode'] = serialize_value(balance.get('suppressed_mode', ''))
        result['aristoteles.balance.balance_score'] = balance.get('balance_score', '')
        result['aristoteles.balance.analysis'] = serialize_value(balance.get('analysis', ''))
        result['aristoteles.balance.consequences_of_imbalance'] = serialize_value(balance.get('consequences_of_imbalance', []))
        result['aristoteles.balance.recommendation_for_balance'] = serialize_value(balance.get('recommendation_for_balance', ''))

        # Orthodoxy/Orthopathy/Orthopraxy
        ortho = data.get('orthodoxy_orthopathy_orthopraxy', {})
        for key in ['orthodoxy_logos', 'orthopathy_pathos', 'orthopraxy_ethos']:
            if key in ortho:
                result[f'aristoteles.{key}.score'] = ortho[key].get('score', '')
                result[f'aristoteles.{key}.analysis'] = serialize_value(ortho[key].get('analysis', ''))

        # Overall picture
        overall = data.get('overall_picture', {})
        result['aristoteles.overall.overall_rhetorical_score'] = overall.get('overall_rhetorical_score', '')
        result['aristoteles.overall.summary'] = serialize_value(overall.get('summary', ''))
        result['aristoteles.overall.strengths_top_3'] = serialize_value(overall.get('strengths_top_3', []))
        result['aristoteles.overall.improvement_points_top_3'] = serialize_value(overall.get('improvement_points_top_3', []))
        result['aristoteles.overall.primary_rhetorical_style'] = serialize_value(overall.get('primary_rhetorical_style', ''))
        result['aristoteles.overall.audience_analysis'] = serialize_value(overall.get('audience_analysis', ''))
        result['aristoteles.overall.recommendations_for_next_sermon'] = serialize_value(overall.get('recommendations_for_next_sermon', []))
        result['aristoteles.overall.conclusion'] = serialize_value(overall.get('conclusion', ''))

    elif analysis_type == 'dekker':
        # Analysis per criterion
        criteria = data.get('analysis_per_criterion', {})
        for criterion_key, criterion_data in criteria.items():
            if isinstance(criterion_data, dict):
                # Normalize criterion name
                normalized_key = criterion_key.replace('criterion_', '').replace('concrete_concrete', 'concrete')
                result[f'dekker.{normalized_key}.score'] = criterion_data.get('score_1_to_10', '')
                result[f'dekker.{normalized_key}.findings'] = serialize_value(criterion_data.get('findings', ''))
                result[f'dekker.{normalized_key}.quotes'] = serialize_value(criterion_data.get('quotes', []))
                result[f'dekker.{normalized_key}.improvement_point'] = serialize_value(criterion_data.get('improvement_point', ''))

        # Overall dekker analysis
        overall = data.get('overall_dekker_analysis', {})
        result['dekker.overall.average_score'] = overall.get('average_score', '')
        result['dekker.overall.strengths'] = serialize_value(overall.get('strengths', []))
        result['dekker.overall.weaknesses'] = serialize_value(overall.get('weaknesses', []))
        result['dekker.overall.general_recommendation'] = serialize_value(overall.get('general_recommendation', ''))

    elif analysis_type == 'kolb':
        # Kolb phases
        phases = data.get('kolb_phases_analysis', {})
        phase_names = {
            'phase_1_concrete_experience': 'concrete_experience',
            'phase_2_reflective_observation': 'reflective_observation',
            'phase_3_abstract_conceptualization': 'abstract_conceptualization',
            'phase_4_active_experimentation': 'active_experimentation'
        }

        for phase_key, phase_name in phase_names.items():
            if phase_key in phases:
                phase_data = phases[phase_key]
                result[f'kolb.{phase_name}.score'] = phase_data.get('score', '')
                result[f'kolb.{phase_name}.analysis'] = serialize_value(phase_data.get('analysis', ''))
                result[f'kolb.{phase_name}.quotes'] = serialize_value(phase_data.get('quotes', []))
                result[f'kolb.{phase_name}.strengths'] = serialize_value(phase_data.get('strengths', []))
                result[f'kolb.{phase_name}.improvement_points'] = serialize_value(phase_data.get('improvement_points', []))
                result[f'kolb.{phase_name}.homiletical_manifestations'] = serialize_value(phase_data.get('homiletical_manifestations', ''))

        # Learning styles
        styles = data.get('learning_styles_analysis', {})
        for style in ['dreamer', 'thinker', 'doer', 'decider']:
            if style in styles:
                style_data = styles[style]
                result[f'kolb.learning_style.{style}.score'] = style_data.get('score', '')
                result[f'kolb.learning_style.{style}.analysis'] = serialize_value(style_data.get('analysis', ''))

        # Integrality
        integ = data.get('integrality_and_cycle', {})
        for key in ['cycle_completeness', 'balance_between_phases', 'holistic_learning']:
            if key in integ:
                integ_data = integ[key]
                result[f'kolb.integrality.{key}.score'] = integ_data.get('score', '')
                result[f'kolb.integrality.{key}.analysis'] = serialize_value(integ_data.get('analysis', ''))

        # Overall
        overall = data.get('overall_picture', {})
        result['kolb.overall.overall_kolb_score'] = overall.get('overall_kolb_score', '')
        result['kolb.overall.summary'] = serialize_value(overall.get('summary', ''))
        result['kolb.overall.strengths_top_3'] = serialize_value(overall.get('strengths_top_3', []))
        result['kolb.overall.improvement_points_top_3'] = serialize_value(overall.get('improvement_points_top_3', []))

    elif analysis_type == 'schulz_von_thun':
        # Four aspects
        aspects = data.get('schulz_von_thun_analysis', {})
        aspect_names = {
            'factual_content_blue': 'factual_content',
            'self_revelation_green': 'self_revelation',
            'relational_aspect_yellow': 'relational_aspect',
            'appeal_aspect_red': 'appeal_aspect'
        }

        for aspect_key, aspect_name in aspect_names.items():
            if aspect_key in aspects:
                aspect_data = aspects[aspect_key]
                result[f'schulz.{aspect_name}.score'] = aspect_data.get('score', '')
                result[f'schulz.{aspect_name}.analysis'] = serialize_value(aspect_data.get('analysis', ''))
                result[f'schulz.{aspect_name}.quotes'] = serialize_value(aspect_data.get('quotes', []))
                result[f'schulz.{aspect_name}.strengths'] = serialize_value(aspect_data.get('strengths', []))
                result[f'schulz.{aspect_name}.improvement_points'] = serialize_value(aspect_data.get('improvement_points', []))

        # Congruence and disruptions (replaces balance)
        congruence = data.get('congruence_and_disruptions', {})
        result['schulz.congruence.congruence_judgment'] = serialize_value(congruence.get('congruence_judgment', ''))
        result['schulz.congruence.dominant_side'] = serialize_value(congruence.get('dominant_side', ''))
        result['schulz.congruence.disruptions'] = serialize_value(congruence.get('disruptions', ''))
        result['schulz.congruence.healing_disruption'] = serialize_value(congruence.get('healing_disruption', ''))

        # Overall
        overall = data.get('overall_picture', {})
        result['schulz.overall.overall_communication_score'] = overall.get('overall_communication_score', '')
        result['schulz.overall.summary'] = serialize_value(overall.get('summary', ''))
        result['schulz.overall.strengths_top_3'] = serialize_value(overall.get('strengths_top_3', []))
        result['schulz.overall.improvement_points_top_3'] = serialize_value(overall.get('improvement_points_top_3', []))

    elif analysis_type == 'esthetiek':
        # Domain A - Poetics of Language
        dom_a = data.get('domain_a_poetics_of_language', {})
        result['esthetiek.poetics.average_score'] = dom_a.get('average_score_language', '')
        for key, value in dom_a.items():
            if key.startswith('criterion_'):
                if isinstance(value, dict):
                    criterion_name = key.replace('criterion_', '')
                    result[f'esthetiek.poetics.{criterion_name}.score'] = value.get('score', '')
                    result[f'esthetiek.poetics.{criterion_name}.analysis'] = serialize_value(value.get('analysis', ''))
                    result[f'esthetiek.poetics.{criterion_name}.quotes'] = serialize_value(value.get('quotes', []))

        # Domain B - Dramaturgy of Structure
        dom_b = data.get('domain_b_dramaturgy_of_structure', {})
        result['esthetiek.dramaturgy.average_score'] = dom_b.get('average_score_structure', '')
        for key, value in dom_b.items():
            if key.startswith('criterion_'):
                if isinstance(value, dict):
                    criterion_name = key.replace('criterion_', '')
                    result[f'esthetiek.dramaturgy.{criterion_name}.score'] = value.get('score', '')
                    result[f'esthetiek.dramaturgy.{criterion_name}.analysis'] = serialize_value(value.get('analysis', ''))
                    result[f'esthetiek.dramaturgy.{criterion_name}.quotes'] = serialize_value(value.get('quotes', []))

        # Kitsch diagnosis
        kitsch = data.get('kitsch_diagnosis', {})
        result['esthetiek.kitsch.anti_kitsch_score'] = kitsch.get('anti_kitsch_score', '')
        result['esthetiek.kitsch.analysis'] = serialize_value(kitsch.get('analysis', ''))
        result['esthetiek.kitsch.quotes'] = serialize_value(kitsch.get('quotes', []))

        # Space for grace
        space = data.get('space_for_grace_analysis', {})
        result['esthetiek.space_for_grace.space_score'] = space.get('space_score', '')
        result['esthetiek.space_for_grace.analysis'] = serialize_value(space.get('analysis', ''))
        result['esthetiek.space_for_grace.quotes'] = serialize_value(space.get('quotes', []))

        # Overall
        overall = data.get('overall_aesthetics', {})
        result['esthetiek.overall.overall_aesthetic_score'] = overall.get('overall_aesthetic_score', '')
        result['esthetiek.overall.summary'] = serialize_value(overall.get('summary', ''))
        result['esthetiek.overall.strengths_top_3'] = serialize_value(overall.get('strengths_top_3', []))
        result['esthetiek.overall.improvement_points_top_3'] = serialize_value(overall.get('improvement_points_top_3', []))

    elif analysis_type == 'transactional':
        # Ego positions scan
        ego = data.get('ego_positions_scan', {})

        # Parent
        parent = ego.get('parent', {})
        for key in ['freedom_from_critical_parent_CP', 'healthy_care_NP']:
            if key in parent:
                key_clean = key.replace('freedom_from_critical_parent_CP', 'freedom_CP').replace('healthy_care_NP', 'nurturing_NP')
                parent_data = parent[key]
                result[f'transactional.parent.{key_clean}.score'] = parent_data.get('score', '')
                result[f'transactional.parent.{key_clean}.analysis'] = serialize_value(parent_data.get('analysis', ''))
                result[f'transactional.parent.{key_clean}.quotes'] = serialize_value(parent_data.get('quotes', []))

        # Adult
        adult = ego.get('adult', {})
        result['transactional.adult.score'] = adult.get('score', '')
        result['transactional.adult.analysis'] = serialize_value(adult.get('analysis', ''))
        result['transactional.adult.quotes'] = serialize_value(adult.get('quotes', []))

        # Child
        child = ego.get('child', {})
        for key in ['freedom_from_adapted_child_AC', 'free_child_FC']:
            if key in child:
                key_clean = key.replace('freedom_from_adapted_child_AC', 'freedom_AC').replace('free_child_FC', 'free_FC')
                child_data = child[key]
                result[f'transactional.child.{key_clean}.score'] = child_data.get('score', '')
                result[f'transactional.child.{key_clean}.analysis'] = serialize_value(child_data.get('analysis', ''))
                result[f'transactional.child.{key_clean}.quotes'] = serialize_value(child_data.get('quotes', []))

        # Transaction analysis
        trans = data.get('transaction_analysis', {})
        result['transactional.transaction.communicative_purity_score'] = trans.get('communicative_purity_score', '')
        result['transactional.transaction.analysis'] = serialize_value(trans.get('analysis', ''))
        result['transactional.transaction.primary_transaction_style'] = serialize_value(trans.get('primary_transaction_style', ''))
        result['transactional.transaction.ulterior_motives'] = serialize_value(trans.get('ulterior_motives', ''))

        # Games analysis (no score field, just detected_games)
        games = data.get('games_analysis', {})
        result['transactional.games.detected_games'] = serialize_value(games.get('detected_games', []))
        result['transactional.games.absence_of_games_analysis'] = serialize_value(games.get('absence_of_games_analysis', ''))

        # Drama triangle analysis (no score field)
        drama = data.get('drama_triangle_analysis', {})
        if isinstance(drama.get('preacher_roles'), dict):
            result['transactional.drama.preacher_rescuer'] = serialize_value(drama['preacher_roles'].get('rescuer', ''))
            result['transactional.drama.preacher_persecutor'] = serialize_value(drama['preacher_roles'].get('persecutor', ''))
            result['transactional.drama.preacher_victim'] = serialize_value(drama['preacher_roles'].get('victim', ''))
        result['transactional.drama.congregation_position'] = serialize_value(drama.get('congregation_position', ''))
        result['transactional.drama.escape_possibilities'] = serialize_value(drama.get('escape_possibilities', ''))

        # Overall
        conclusion = data.get('conclusion_and_recommendation', {})
        result['transactional.overall.psychological_health_score'] = conclusion.get('psychological_health_score', '')
        result['transactional.overall.summary'] = serialize_value(conclusion.get('summary', ''))
        result['transactional.overall.strengths_top_3'] = serialize_value(conclusion.get('strengths_top_3', []))
        result['transactional.overall.improvement_points_top_3'] = serialize_value(conclusion.get('improvement_points_top_3', []))

    return result


def load_all_sermons() -> dict:
    """
    Load all JSON files and group them by sermon (theologian + sermon_id).

    Returns:
        dict[tuple[theologian, sermon_id], dict[analysis_type, data]]
    """
    sermons = defaultdict(dict)

    if not DOCS_DIR.exists():
        print(f"Error: Directory {DOCS_DIR} not found")
        return sermons

    json_files = list(DOCS_DIR.glob("*.json"))
    print(f"Found {len(json_files)} JSON files in {DOCS_DIR}")

    processed = 0
    skipped = 0

    for filepath in sorted(json_files):
        parsed = parse_filename(filepath.name)
        if not parsed:
            skipped += 1
            continue

        theologian, sermon_id, analysis_type = parsed

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle array JSON files (some files are wrapped in arrays)
            if isinstance(data, list):
                if len(data) > 0 and isinstance(data[0], dict):
                    data = data[0]  # Take first element
                else:
                    print(f"Warning: Skipping {filepath} - array with no valid object")
                    skipped += 1
                    continue

            if not isinstance(data, dict):
                print(f"Warning: Skipping {filepath} - not a valid object")
                skipped += 1
                continue

            sermon_key = (theologian, sermon_id)
            sermons[sermon_key][analysis_type] = {
                'filename': filepath.name,
                'data': data
            }
            processed += 1

        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load {filepath}: {e}")
            skipped += 1

    print(f"Successfully loaded {processed} analysis files")
    print(f"Skipped {skipped} files")
    print(f"Found {len(sermons)} unique sermons")

    return sermons


def create_tsv(sermons: dict):
    """
    Create a TSV file with one row per sermon and all analysis data.
    """
    # Collect all possible column names
    all_columns = set(['theologian', 'sermon_id', 'sermon_key'])

    # First pass: collect all column names
    print("\nCollecting column names...")
    for sermon_key, analyses in sermons.items():
        for analysis_type, analysis_info in analyses.items():
            data = analysis_info['data']
            extracted = extract_analysis_data(data, analysis_type)
            all_columns.update(extracted.keys())

    # Sort columns for consistent ordering
    meta_columns = ['theologian', 'sermon_id', 'sermon_key']
    data_columns = sorted([col for col in all_columns if col not in meta_columns])
    all_columns_ordered = meta_columns + data_columns

    print(f"Total columns: {len(all_columns_ordered)}")

    # Write TSV
    print(f"\nWriting TSV to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=all_columns_ordered, delimiter='\t',
                               extrasaction='ignore', quoting=csv.QUOTE_ALL)

        writer.writeheader()

        for sermon_key, analyses in sorted(sermons.items()):
            theologian, sermon_id = sermon_key

            row = {
                'theologian': theologian,
                'sermon_id': sermon_id,
                'sermon_key': f"{theologian}_{sermon_id}"
            }

            # Extract data from all analyses for this sermon
            for analysis_type, analysis_info in analyses.items():
                data = analysis_info['data']
                extracted = extract_analysis_data(data, analysis_type)
                row.update(extracted)

            writer.writerow(row)

    print(f"TSV file created successfully: {OUTPUT_FILE}")


def print_summary(sermons: dict):
    """Print summary statistics."""
    theologian_counts = defaultdict(int)
    analysis_counts = defaultdict(int)

    for sermon_key, analyses in sermons.items():
        theologian, _ = sermon_key
        theologian_counts[theologian] += 1

        for analysis_type in analyses.keys():
            analysis_counts[analysis_type] += 1

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"\nTotal sermons: {len(sermons)}")
    print(f"\nSermons per theologian:")
    for theologian, count in sorted(theologian_counts.items()):
        print(f"  - {theologian}: {count}")

    print(f"\nAnalyses per type:")
    for analysis_type, count in sorted(analysis_counts.items()):
        print(f"  - {analysis_type}: {count}")

    # Check completeness
    print(f"\nCompleteness check:")
    complete = 0
    incomplete = []
    for sermon_key, analyses in sermons.items():
        if len(analyses) == 6:
            complete += 1
        else:
            missing = set(ANALYSIS_TYPES) - set(analyses.keys())
            incomplete.append((sermon_key, missing))

    print(f"  - Complete sermons (all 6 analyses): {complete}")
    print(f"  - Incomplete sermons: {len(incomplete)}")

    if incomplete and len(incomplete) <= 10:
        print(f"\n  Incomplete sermons:")
        for sermon_key, missing in incomplete[:10]:
            print(f"    - {sermon_key[0]}_{sermon_key[1]}: missing {', '.join(missing)}")


def main():
    print("=" * 60)
    print("CONVERT HOMILETIC FEEDBACK JSON TO TSV")
    print("=" * 60)

    # Load all sermons
    sermons = load_all_sermons()

    if not sermons:
        print("No data found. Exiting.")
        return

    # Print summary
    print_summary(sermons)

    # Create TSV
    create_tsv(sermons)

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
