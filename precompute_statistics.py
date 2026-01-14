#!/usr/bin/env python3
"""
Precompute statistics for the homiletic feedback dashboard.

This script reads all JSON analysis files from the outputs directory,
aggregates scores per theologian with mean and standard deviation,
and saves the results to docs/statistics.json for fast loading.

Usage:
    python precompute_statistics.py
"""

import os
import json
import math
from pathlib import Path
from collections import defaultdict

# Configuration
OUTPUTS_DIR = Path("docs")
DOCS_DIR = Path("docs")
OUTPUT_FILE = DOCS_DIR / "statistics.json"


def parse_filename(filename: str) -> tuple[str, str, str] | None:
    """
    Parse a filename like 'augustine_01_aristoteles.json' into components.
    Returns (theologian, sermon, analysis_type) or None if invalid.
    """
    if not filename.endswith('.json') or filename.endswith('.raw') or filename.startswith( 'file_index' ) or filename.startswith( 'statistics' ):
        return None

    base = filename.replace('.json', '')
    parts = base.split('_')

    if len(parts) < 3:
        return None

    theologian = parts[0]
    sermon = parts[1]
    # Handle analysis types like 'schulz_von_thun' (multi-part)
    analysis = '_'.join(parts[2:])

    return theologian, sermon, analysis


def extract_scores(data: dict, analysis_type: str, detailed: bool = False) -> dict[str, float]:
    """
    Extract scores from analysis data based on the analysis type.
    Returns a dictionary of {metric_name: score}.
    """
    scores = {}

    # Skip if data is not a dict (malformed JSON)
    if not isinstance(data, dict):
        return scores

    def add_score(category: str, value):
        """Add a score if it's a valid number between 0 and 10."""
        if isinstance(value, (int, float)) and 0 <= value <= 10:
            key = f"{analysis_type}_{category}"
            scores[key] = value

    if analysis_type == 'aristoteles':
        modes = data.get('aristotelian_modes_analysis', {})
        if modes.get('logos', {}).get('score'):
            add_score('Logos', modes['logos']['score'])
        if modes.get('pathos', {}).get('score'):
            add_score('Pathos', modes['pathos']['score'])
        if modes.get('ethos', {}).get('score'):
            add_score('Ethos', modes['ethos']['score'])
        if data.get('overall_picture', {}).get('overall_rhetorical_score'):
            add_score('Overall', data['overall_picture']['overall_rhetorical_score'])
        if detailed and data.get('rhetorical_balance_analysis', {}).get('balance_score'):
            add_score('Balance Score', data['rhetorical_balance_analysis']['balance_score'])

    elif analysis_type == 'dekker':
        criteria = data.get('analysis_per_criterion', {})
        for key, value in criteria.items():
            if isinstance(value, dict) and value.get('score_1_to_10'):
                # Format: criterion_1_specific_bible_passage -> #1 specific bible passage
                name = key.replace('criterion_', '').replace('_', ' ')
                # Add # before the number at the start
                parts = name.split(' ', 1)
                if parts[0].isdigit():
                    name = f"#{parts[0]} {parts[1]}" if len(parts) > 1 else f"#{parts[0]}"
                add_score(name, value['score_1_to_10'])

    elif analysis_type == 'kolb':
        phases = data.get('kolb_phases_analysis', {})
        if phases.get('phase_1_concrete_experience', {}).get('score'):
            add_score('Concrete Experience', phases['phase_1_concrete_experience']['score'])
        if phases.get('phase_2_reflective_observation', {}).get('score'):
            add_score('Reflective Observation', phases['phase_2_reflective_observation']['score'])
        if phases.get('phase_3_abstract_conceptualization', {}).get('score'):
            add_score('Abstract Conceptualization', phases['phase_3_abstract_conceptualization']['score'])
        if phases.get('phase_4_active_experimentation', {}).get('score'):
            add_score('Active Experimentation', phases['phase_4_active_experimentation']['score'])

        if detailed:
            # Learning styles
            styles = data.get('learning_styles_analysis', {})
            if styles.get('dreamer', {}).get('score'):
                add_score('Dreamer', styles['dreamer']['score'])
            if styles.get('thinker', {}).get('score'):
                add_score('Thinker', styles['thinker']['score'])
            if styles.get('doer', {}).get('score'):
                add_score('Doer', styles['doer']['score'])
            if styles.get('decider', {}).get('score'):
                add_score('Decider', styles['decider']['score'])

            # Also check alternative key names
            if styles.get('assimilating_style', {}).get('score'):
                add_score('Assimilating', styles['assimilating_style']['score'])
            if styles.get('converging_style', {}).get('score'):
                add_score('Converging', styles['converging_style']['score'])
            if styles.get('accommodating_style', {}).get('score'):
                add_score('Accommodating', styles['accommodating_style']['score'])
            if styles.get('diverging_style', {}).get('score'):
                add_score('Diverging', styles['diverging_style']['score'])

            # Integrality metrics
            integ = data.get('integrality_and_cycle', {})
            if integ.get('cycle_completeness', {}).get('score'):
                add_score('Cycle Completeness', integ['cycle_completeness']['score'])
            if integ.get('balance_between_phases', {}).get('score'):
                add_score('Balance Between Phases', integ['balance_between_phases']['score'])
            if integ.get('holistic_learning', {}).get('score'):
                add_score('Holistic Learning', integ['holistic_learning']['score'])

        if data.get('overall_picture', {}).get('overall_kolb_score'):
            add_score('Overall', data['overall_picture']['overall_kolb_score'])

    elif analysis_type == 'schulz_von_thun':
        analysis = data.get('schulz_von_thun_analysis', {})
        if analysis.get('factual_content_blue', {}).get('score'):
            add_score('Factual Content', analysis['factual_content_blue']['score'])
        if analysis.get('self_revelation_green', {}).get('score'):
            add_score('Self-Revelation', analysis['self_revelation_green']['score'])
        if analysis.get('relational_aspect_yellow', {}).get('score'):
            add_score('Relational Aspect', analysis['relational_aspect_yellow']['score'])
        if analysis.get('appeal_aspect_red', {}).get('score'):
            add_score('Appeal Aspect', analysis['appeal_aspect_red']['score'])
        if data.get('overall_picture', {}).get('overall_communication_score'):
            add_score('Overall', data['overall_picture']['overall_communication_score'])

    elif analysis_type == 'esthetiek':
        if detailed:
            # Domain A - Poetics of Language (all individual criteria)
            dom_a = data.get('domain_a_poetics_of_language', {})
            for key, value in dom_a.items():
                if isinstance(value, dict) and value.get('score') is not None:
                    # Format: criterion_a1_imagery -> Imagery
                    import re
                    name = re.sub(r'criterion_a\d+_', '', key).replace('_', ' ')
                    name = name.title()
                    add_score(name, value['score'])

            # Domain B - Dramaturgy of Structure (all individual criteria)
            dom_b = data.get('domain_b_dramaturgy_of_structure', {})
            for key, value in dom_b.items():
                if isinstance(value, dict) and value.get('score') is not None:
                    import re
                    name = re.sub(r'criterion_b\d+_', '', key).replace('_', ' ')
                    name = name.title()
                    add_score(name, value['score'])

            # Anti-kitsch and Space for Grace
            if data.get('kitsch_diagnosis', {}).get('anti_kitsch_score'):
                add_score('Anti-Kitsch', data['kitsch_diagnosis']['anti_kitsch_score'])
            if data.get('space_for_grace_analysis', {}).get('space_score'):
                add_score('Space for Grace', data['space_for_grace_analysis']['space_score'])
        else:
            # Summary scores only
            if data.get('domain_a_poetics_of_language', {}).get('average_score_language'):
                add_score('Poetics', data['domain_a_poetics_of_language']['average_score_language'])
            if data.get('domain_b_dramaturgy_of_structure', {}).get('average_score_structure'):
                add_score('Dramaturgy', data['domain_b_dramaturgy_of_structure']['average_score_structure'])

        if data.get('overall_aesthetics', {}).get('overall_aesthetic_score'):
            add_score('Overall', data['overall_aesthetics']['overall_aesthetic_score'])

    return scores


def calculate_stats(values: list[float]) -> dict:
    """Calculate mean and standard deviation for a list of values."""
    if not values:
        return None

    n = len(values)
    mean = sum(values) / n

    if n > 1:
        variance = sum((x - mean) ** 2 for x in values) / n
        std_dev = math.sqrt(variance)
    else:
        std_dev = 0.0

    return {
        'mean': round(mean, 2),
        'stdDev': round(std_dev, 2),
        'count': n
    }


def aggregate_scores(all_data: list[dict], detailed: bool = False) -> dict:
    """
    Aggregate scores from all analysis data.

    Returns a nested dictionary:
    {
        metric_key: {
            theologian: { mean, stdDev, count }
        }
    }
    """
    # Collect scores per theologian per metric
    scores_by_metric_and_theologian = defaultdict(lambda: defaultdict(list))

    for item in all_data:
        theologian = item['theologian']
        analysis_type = item['analysis']
        data = item['data']

        scores = extract_scores(data, analysis_type, detailed)

        for metric_key, score in scores.items():
            scores_by_metric_and_theologian[metric_key][theologian].append(score)

    # Calculate statistics
    result = {}
    for metric_key, theologian_scores in scores_by_metric_and_theologian.items():
        result[metric_key] = {}
        for theologian, values in theologian_scores.items():
            stats = calculate_stats(values)
            if stats:
                result[metric_key][theologian] = stats

    return result


def load_all_data() -> list[dict]:
    """Load all JSON analysis files from the outputs directory."""
    all_data = []

    if not OUTPUTS_DIR.exists():
        print(f"Error: Directory {OUTPUTS_DIR} not found")
        return all_data

    json_files = list(OUTPUTS_DIR.glob("*.json"))
    print(f"Found {len(json_files)} JSON files in {OUTPUTS_DIR}")

    for filepath in sorted(json_files):
        parsed = parse_filename(filepath.name)
        if not parsed:
            continue

        theologian, sermon, analysis = parsed

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Skip if data is not a dict (malformed structure)
            if not isinstance(data, dict):
                print(f"Warning: Skipping {filepath} - not a valid object")
                continue

            all_data.append({
                'theologian': theologian,
                'sermon': sermon,
                'analysis': analysis,
                'data': data
            })
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load {filepath}: {e}")

    print(f"Successfully loaded {len(all_data)} analysis files")
    return all_data


def get_available_theologians(all_data: list[dict]) -> list[str]:
    """Get a sorted list of unique theologians."""
    return sorted(set(item['theologian'] for item in all_data))


def main():
    print("=" * 60)
    print("PRECOMPUTE STATISTICS FOR HOMILETIC FEEDBACK")
    print("=" * 60)

    # Load all data
    all_data = load_all_data()

    if not all_data:
        print("No data found. Exiting.")
        return

    # Get available theologians
    theologians = get_available_theologians(all_data)
    print(f"\nTheologians found: {', '.join(theologians)}")

    # Compute statistics for both modes
    print("\nComputing summary statistics...")
    summary_stats = aggregate_scores(all_data, detailed=False)

    print("Computing detailed statistics...")
    detailed_stats = aggregate_scores(all_data, detailed=True)

    # Create output structure
    output = {
        'generated_at': __import__('datetime').datetime.now().isoformat(),
        'theologians': theologians,
        'summary': summary_stats,
        'detailed': detailed_stats
    }

    # Ensure docs directory exists
    DOCS_DIR.mkdir(exist_ok=True)

    # Write output
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Statistics saved to {OUTPUT_FILE}")

    # Print summary
    print(f"\nSummary:")
    print(f"  - Theologians: {len(theologians)}")
    print(f"  - Summary metrics: {len(summary_stats)}")
    print(f"  - Detailed metrics: {len(detailed_stats)}")

    # Print sample of metrics
    print(f"\nSample metrics (summary):")
    for i, (metric, data) in enumerate(list(summary_stats.items())[:5]):
        theol_count = len(data)
        print(f"  - {metric}: {theol_count} theologians")


if __name__ == "__main__":
    main()
