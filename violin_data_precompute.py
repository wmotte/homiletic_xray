#!/usr/bin/env python3
"""
Precompute violin plot data for the homiletic feedback dashboard.

This script reads all JSON analysis files from the outputs directory,
collects all individual scores per theologian (preserving the full distribution),
and saves the results to docs/violin_data.json for JavaScript violin plot rendering.

Usage:
    python violin_data_precompute.py
"""

import json
from pathlib import Path
from collections import defaultdict
from statistics import median, quantiles

# Configuration
DOCS_DIR = Path("docs")
INPUT_DIR = DOCS_DIR  # JSON analysis files are in docs/
OUTPUT_FILE = DOCS_DIR / "violin_data.json"


def parse_filename(filename: str) -> tuple[str, str, str] | None:
    """
    Parse a filename like 'augustine_01_aristoteles.json' into components.
    Also handles 'hervormd_11jan2026_01_aristoteles.json' format.
    Returns (theologian, sermon, analysis_type) or None if invalid.
    """

    if not filename.endswith('.json') or filename.endswith('.raw') or filename.startswith( 'file_index' ) or filename.startswith( 'statistics' ) or filename.startswith( 'violin_data' ):
        return None

    base = filename.replace('.json', '')
    parts = base.split('_')

    if len(parts) < 3:
        return None

    theologian = parts[0]

    # Known analysis types (including multi-part ones)
    KNOWN_ANALYSIS_TYPES = ['aristoteles', 'dekker', 'kolb', 'schulz_von_thun', 'esthetiek', 'transactional']

    # Find where the analysis type starts by looking for known analysis types
    analysis_start_idx = None
    for i in range(1, len(parts)):
        for analysis_type in KNOWN_ANALYSIS_TYPES:
            analysis_parts = analysis_type.split('_')
            candidate = '_'.join(parts[i:i + len(analysis_parts)])
            if candidate == analysis_type:
                analysis_start_idx = i
                break
        if analysis_start_idx is not None:
            break

    if analysis_start_idx is None or analysis_start_idx < 2:
        # Fallback to old behavior if no known analysis type found
        sermon = parts[1]
        analysis = '_'.join(parts[2:])
    else:
        # Sermon is everything between theologian and analysis type
        sermon = '_'.join(parts[1:analysis_start_idx])
        analysis = '_'.join(parts[analysis_start_idx:])

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
                # Normalize common typos in criterion names
                normalized_key = key.replace('concrete_concrete', 'concrete')

                # Format: criterion_1_specific_bible_passage -> #1 specific bible passage
                name = normalized_key.replace('criterion_', '').replace('_', ' ')
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

    elif analysis_type == 'transactional':
        # Ego positions scan
        ego_scan = data.get('ego_positions_scan', {})
        parent = ego_scan.get('parent', {})
        child = ego_scan.get('child', {})
        adult = ego_scan.get('adult', {})

        if parent.get('freedom_from_critical_parent_CP', {}).get('score'):
            add_score('Freedom from Critical Parent', parent['freedom_from_critical_parent_CP']['score'])
        if parent.get('healthy_care_NP', {}).get('score'):
            add_score('Nurturing Parent', parent['healthy_care_NP']['score'])
        if adult.get('score'):
            add_score('Adult Presence', adult['score'])
        if child.get('freedom_from_adapted_child_AC', {}).get('score'):
            add_score('Freedom from Adapted Child', child['freedom_from_adapted_child_AC']['score'])
        if child.get('free_child_FC', {}).get('score'):
            add_score('Free Child', child['free_child_FC']['score'])

        # Transaction analysis
        trans = data.get('transaction_analysis', {})
        if trans.get('communicative_purity_score'):
            add_score('Communicative Purity', trans['communicative_purity_score'])

        # Overall psychological health score
        conclusion = data.get('conclusion_and_recommendation', {})
        if conclusion.get('psychological_health_score'):
            add_score('Overall', conclusion['psychological_health_score'])

    return scores


def calculate_violin_data(values: list[float]) -> dict:
    """
    Prepare data for violin plot rendering.

    Returns:
        - values: all raw data points (for KDE computation in JS)
        - summary: min, max, median, q1, q3 for box plot overlay
        - count: number of data points
    """
    if not values:
        return None

    n = len(values)
    sorted_vals = sorted(values)

    # Calculate summary statistics
    mean_val = sum(values) / n
    min_val = sorted_vals[0]
    max_val = sorted_vals[-1]
    median_val = median(sorted_vals)

    # Calculate quartiles (need at least 4 values for proper quartiles)
    if n >= 4:
        q = quantiles(sorted_vals, n=4)
        q1, q2, q3 = q[0], q[1], q[2]
    elif n >= 2:
        q1 = sorted_vals[n // 4] if n > 1 else sorted_vals[0]
        q3 = sorted_vals[(3 * n) // 4] if n > 1 else sorted_vals[-1]
    else:
        q1 = q3 = sorted_vals[0]

    return {
        'values': [round(v, 2) for v in sorted_vals],  # All raw values for KDE
        'summary': {
            'min': round(min_val, 2),
            'max': round(max_val, 2),
            'median': round(median_val, 2),
            'q1': round(q1, 2),
            'q3': round(q3, 2),
            'mean': round(mean_val, 2)
        },
        'count': n
    }


def aggregate_scores(all_data: list[dict], detailed: bool = False) -> dict:
    """
    Aggregate scores from all analysis data for violin plot rendering.

    Returns a nested dictionary:
    {
        metric_key: {
            theologian: { values, summary, count }
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

    # Calculate violin plot data
    result = {}
    for metric_key, theologian_scores in scores_by_metric_and_theologian.items():
        result[metric_key] = {}
        for theologian, values in theologian_scores.items():
            violin_data = calculate_violin_data(values)
            if violin_data:
                result[metric_key][theologian] = violin_data

    return result


def load_all_data() -> list[dict]:
    """Load all JSON analysis files from the docs directory."""
    all_data = []

    if not INPUT_DIR.exists():
        print(f"Error: Directory {INPUT_DIR} not found")
        return all_data

    json_files = list(INPUT_DIR.glob("*.json"))
    print(f"Found {len(json_files)} JSON files in {INPUT_DIR}")

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


def count_sermons_per_theologian(all_data: list[dict]) -> dict[str, int]:
    """Count unique sermons per theologian."""
    sermons_by_theologian = defaultdict(set)
    for item in all_data:
        sermons_by_theologian[item['theologian']].add(item['sermon'])
    return {theologian: len(sermons) for theologian, sermons in sorted(sermons_by_theologian.items())}


def main():
    print("=" * 60)
    print("PRECOMPUTE VIOLIN PLOT DATA FOR HOMILETIC FEEDBACK")
    print("=" * 60)

    # Load all data
    all_data = load_all_data()

    if not all_data:
        print("No data found. Exiting.")
        return

    # Get available theologians and sermon counts
    theologians = get_available_theologians(all_data)
    sermon_counts = count_sermons_per_theologian(all_data)
    print(f"\nTheologians found: {', '.join(theologians)}")
    print(f"\nSermons per theologian:")
    for theologian, count in sermon_counts.items():
        print(f"  - {theologian}: {count} sermons")

    # Compute violin data for both modes
    print("\nComputing summary violin data...")
    summary_violin = aggregate_scores(all_data, detailed=False)

    print("Computing detailed violin data...")
    detailed_violin = aggregate_scores(all_data, detailed=True)

    # Create output structure
    output = {
        'generated_at': __import__('datetime').datetime.now().isoformat(),
        'theologians': theologians,
        'sermon_counts': sermon_counts,
        'summary': summary_violin,
        'detailed': detailed_violin
    }

    # Ensure docs directory exists
    DOCS_DIR.mkdir(exist_ok=True)

    # Write output
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nViolin plot data saved to {OUTPUT_FILE}")

    # Print summary
    print(f"\nSummary:")
    print(f"  - Theologians: {len(theologians)}")
    print(f"  - Summary metrics: {len(summary_violin)}")
    print(f"  - Detailed metrics: {len(detailed_violin)}")

    # Print sample of metrics with data point counts
    print(f"\nSample metrics (summary):")
    for metric, data in list(summary_violin.items())[:5]:
        theol_info = ', '.join(f"{t}({d['count']})" for t, d in data.items())
        print(f"  - {metric}: {theol_info}")


if __name__ == "__main__":
    main()
