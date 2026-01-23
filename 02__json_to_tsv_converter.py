#!/usr/bin/env python3
"""
Convert homiletic feedback JSON files to a single TSV file for analysis in R.

This script reads all JSON analysis files from the docs directory,
groups them by sermon (theologian + sermon_id), and creates one row per sermon
with all information from the 9 analysis domains (aristoteles, dekker, kolb,
schulz_von_thun, esthetiek, transactional, metaphor, speech_act, narrative).

Note: Sölle B files (second run on same sermons) are excluded from the analysis.

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
ANALYSIS_TYPES = ['aristoteles', 'dekker', 'kolb', 'schulz_von_thun', 'esthetiek', 'transactional', 'metaphor', 'speech_act', 'narrative']


def parse_filename(filename: str) -> tuple[str, str, str] | None:
    """
    Parse a filename like 'augustine_01_aristoteles.json' into components.
    Returns (theologian, sermon_id, analysis_type) or None if invalid.
    """
    if not filename.endswith('.json'):
        return None

    # Skip special files and Sölle B (second run) files
    skip_patterns = ['statistics', 'violin_data', 'file_index', '.raw']
    if any(pattern in filename for pattern in skip_patterns):
        return None

    # Skip Sölle B files (second run on same sermons)
    if '_B_' in filename:
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
        criterion_scores = []
        for criterion_key, criterion_data in criteria.items():
            if isinstance(criterion_data, dict):
                # Normalize criterion name
                normalized_key = criterion_key.replace('criterion_', '').replace('concrete_concrete', 'concrete')
                score = criterion_data.get('score_1_to_10', '')
                result[f'dekker.{normalized_key}.score'] = score
                result[f'dekker.{normalized_key}.findings'] = serialize_value(criterion_data.get('findings', ''))
                result[f'dekker.{normalized_key}.quotes'] = serialize_value(criterion_data.get('quotes', []))
                result[f'dekker.{normalized_key}.improvement_point'] = serialize_value(criterion_data.get('improvement_point', ''))
                # Collect scores for average calculation
                if score != '' and score is not None:
                    try:
                        criterion_scores.append(float(score))
                    except (ValueError, TypeError):
                        pass

        # Overall dekker analysis
        overall = data.get('overall_dekker_analysis', {})
        # Compute average from sub-scores if not provided in JSON
        avg_score = overall.get('average_score', '')
        if (avg_score == '' or avg_score is None) and criterion_scores:
            avg_score = sum(criterion_scores) / len(criterion_scores)
        result['dekker.overall.average_score'] = avg_score
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
        result['aesthetics.poetics.average_score'] = dom_a.get('average_score_language', '')
        for key, value in dom_a.items():
            if key.startswith('criterion_'):
                if isinstance(value, dict):
                    criterion_name = key.replace('criterion_', '')
                    result[f'aesthetics.poetics.{criterion_name}.score'] = value.get('score', '')
                    result[f'aesthetics.poetics.{criterion_name}.analysis'] = serialize_value(value.get('analysis', ''))
                    result[f'aesthetics.poetics.{criterion_name}.quotes'] = serialize_value(value.get('quotes', []))

        # Domain B - Dramaturgy of Structure
        dom_b = data.get('domain_b_dramaturgy_of_structure', {})
        result['aesthetics.dramaturgy.average_score'] = dom_b.get('average_score_structure', '')
        for key, value in dom_b.items():
            if key.startswith('criterion_'):
                if isinstance(value, dict):
                    criterion_name = key.replace('criterion_', '')
                    result[f'aesthetics.dramaturgy.{criterion_name}.score'] = value.get('score', '')
                    result[f'aesthetics.dramaturgy.{criterion_name}.analysis'] = serialize_value(value.get('analysis', ''))
                    result[f'aesthetics.dramaturgy.{criterion_name}.quotes'] = serialize_value(value.get('quotes', []))

        # Kitsch diagnosis
        kitsch = data.get('kitsch_diagnosis', {})
        result['aesthetics.kitsch.anti_kitsch_score'] = kitsch.get('anti_kitsch_score', '')
        result['aesthetics.kitsch.analysis'] = serialize_value(kitsch.get('analysis', ''))
        result['aesthetics.kitsch.quotes'] = serialize_value(kitsch.get('quotes', []))

        # Space for grace
        space = data.get('space_for_grace_analysis', {})
        result['aesthetics.space_for_grace.space_score'] = space.get('space_score', '')
        result['aesthetics.space_for_grace.analysis'] = serialize_value(space.get('analysis', ''))
        result['aesthetics.space_for_grace.quotes'] = serialize_value(space.get('quotes', []))

        # Overall
        overall = data.get('overall_aesthetics', {})
        result['aesthetics.overall.overall_aesthetic_score'] = overall.get('overall_aesthetic_score', '')
        result['aesthetics.overall.summary'] = serialize_value(overall.get('summary', ''))
        result['aesthetics.overall.strengths_top_3'] = serialize_value(overall.get('strengths_top_3', []))
        result['aesthetics.overall.improvement_points_top_3'] = serialize_value(overall.get('improvement_points_top_3', []))

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

    elif analysis_type == 'metaphor':
        # Primary analysis - dominant domains
        primaire = data.get('primaire_analyse', {})
        result['metaphor.dominante_domeinen'] = serialize_value(primaire.get('dominante_domeinen', []))
        result['metaphor.metafoor_inventaris'] = serialize_value(primaire.get('metafoor_inventaris', []))

        # Diagnostic evaluation
        diag = data.get('diagnostische_evaluatie', {})
        coherentie = diag.get('coherentie_analyse', {})
        result['metaphor.coherentie.overall'] = serialize_value(coherentie.get('overall_coherentie', ''))
        # Convert categorical coherence to numeric score
        coherentie_mapping = {
            'HIGHLY_COHERENT': 10,
            'MOSTLY_COHERENT': 7,
            'MIXED': 4,
            'INCOHERENT': 1
        }
        overall_coherentie = coherentie.get('overall_coherentie', '')
        result['metaphor.coherentie.score'] = coherentie_mapping.get(overall_coherentie, '')
        result['metaphor.coherentie.verklaring'] = serialize_value(coherentie.get('coherentie_verklaring', ''))
        result['metaphor.coherentie.incoherentie_punten'] = serialize_value(coherentie.get('incoherentie_punten', []))
        result['metaphor.coherentie.succesvolle_blending'] = serialize_value(coherentie.get('succesvolle_blending', []))
        result['metaphor.sterktes'] = serialize_value(diag.get('sterktes', []))
        result['metaphor.risicos'] = serialize_value(diag.get('risicos', []))

        # Text world analysis
        text_world = diag.get('text_world_analyse', {})
        result['metaphor.text_world.primaire_wereld'] = serialize_value(text_world.get('primaire_wereld', ''))
        result['metaphor.text_world.sub_worlds'] = serialize_value(text_world.get('sub_worlds', []))
        result['metaphor.text_world.effectiviteit'] = serialize_value(text_world.get('world_building_effectiviteit', ''))
        result['metaphor.text_world.deictic_shifts'] = serialize_value(text_world.get('deictic_shifts', []))

        # Schema analysis
        schema = diag.get('schema_analyse', {})
        result['metaphor.schema.versterkte_schemas'] = serialize_value(schema.get('versterkte_schemas', []))
        result['metaphor.schema.verstoorde_schemas'] = serialize_value(schema.get('verstoorde_schemas', []))
        result['metaphor.schema.liturgische_aansluiting'] = serialize_value(schema.get('liturgische_schema_aansluiting', ''))

        # Recommendations
        aanbev = data.get('aanbevelingen', {})
        result['metaphor.audit_samenvatting'] = serialize_value(aanbev.get('metafoor_audit_samenvatting', ''))
        result['metaphor.revitalisatie_suggesties'] = serialize_value(aanbev.get('revitalisatie_suggesties', []))
        result['metaphor.coherentie_verbeteringen'] = serialize_value(aanbev.get('coherentie_verbeteringen', []))
        result['metaphor.entailment_checks'] = serialize_value(aanbev.get('entailment_checks', []))
        result['metaphor.alternatieve_domeinen'] = serialize_value(aanbev.get('alternatieve_domeinen', []))
        result['metaphor.overall.beoordeling'] = serialize_value(aanbev.get('overall_beoordeling', ''))
        result['metaphor.overall.slotopmerking'] = serialize_value(aanbev.get('slotopmerking', ''))

        # Comparative analysis
        comp = data.get('comparatieve_analyse', {})
        result['metaphor.vergelijk.esthetiek'] = serialize_value(comp.get('verschil_met_esthetiek', ''))
        result['metaphor.vergelijk.kolb'] = serialize_value(comp.get('verschil_met_kolb', ''))
        result['metaphor.vergelijk.unieke_inzichten'] = serialize_value(comp.get('unieke_inzichten_CMT', ''))

        # Appendices
        appendices = data.get('appendices', {})
        result['metaphor.volledige_metafoor_lijst'] = serialize_value(appendices.get('volledige_metafoor_lijst', []))
        result['metaphor.woord_frequentie'] = serialize_value(appendices.get('woord_frequentie_analyse', {}))
        result['metaphor.notities'] = serialize_value(appendices.get('notities', ''))

    elif analysis_type == 'speech_act':
        # Threefold structure analysis
        drievoudig = data.get('drievoudige_structuur_analyse', {})
        locutie = drievoudig.get('locutie', {})
        result['speech_act.locutie.beschrijving'] = serialize_value(locutie.get('beschrijving', ''))
        result['speech_act.locutie.exegetische_kwaliteit'] = serialize_value(locutie.get('exegetische_kwaliteit', ''))
        result['speech_act.locutie.omvang_procent'] = locutie.get('omvang_procent', '')

        illocutie = drievoudig.get('illocutie', {})
        result['speech_act.illocutie.beschrijving'] = serialize_value(illocutie.get('beschrijving', ''))
        result['speech_act.illocutie.primaire_kracht'] = serialize_value(illocutie.get('primaire_kracht', ''))
        result['speech_act.illocutie.helderheid_score'] = illocutie.get('helderheid_score', '')
        result['speech_act.illocutie.voorbeelden'] = serialize_value(illocutie.get('voorbeelden', []))

        perlocutie = drievoudig.get('perlocutie', {})
        result['speech_act.perlocutie.beoogd_effect'] = serialize_value(perlocutie.get('beoogd_effect', ''))
        result['speech_act.perlocutie.pneumatologisch_bewustzijn'] = serialize_value(perlocutie.get('pneumatologisch_bewustzijn', ''))
        result['speech_act.perlocutie.werkwoorden'] = serialize_value(perlocutie.get('perlocutionaire_werkwoorden', []))

        # Verb analysis
        werkwoord = data.get('werkwoord_analyse', {})
        for category in ['assertieven', 'directieven', 'expressieven', 'commissieven', 'declaratieven']:
            cat_data = werkwoord.get(category, {})
            result[f'speech_act.werkwoord.{category}.frequentie'] = cat_data.get('frequentie', '')
            result[f'speech_act.werkwoord.{category}.procent'] = cat_data.get('procent', '')
            result[f'speech_act.werkwoord.{category}.voorbeelden'] = serialize_value(cat_data.get('voorbeelden', []))
            result[f'speech_act.werkwoord.{category}.dominante_werkwoorden'] = serialize_value(cat_data.get('dominante_werkwoorden', []))

        # Constative/Performative diagnosis
        const_perf = data.get('constatief_performatief_diagnose', {})
        result['speech_act.const_perf.classificatie'] = serialize_value(const_perf.get('primaire_classificatie', ''))
        result['speech_act.const_perf.constatief_percentage'] = const_perf.get('constatief_percentage', '')
        result['speech_act.const_perf.performatief_percentage'] = const_perf.get('performatief_percentage', '')

        surplus = const_perf.get('constatief_surplus_analyse', {})
        result['speech_act.const_perf.surplus_aanwezig'] = serialize_value(surplus.get('aanwezig', ''))
        result['speech_act.const_perf.surplus_ernst'] = serialize_value(surplus.get('ernst', ''))

        deficit = const_perf.get('performatief_deficit_analyse', {})
        result['speech_act.const_perf.deficit_aanwezig'] = serialize_value(deficit.get('aanwezig', ''))
        result['speech_act.const_perf.deficit_ernst'] = serialize_value(deficit.get('ernst', ''))

        toezegging = const_perf.get('toezegging_check', {})
        result['speech_act.toezegging.aanwezig'] = serialize_value(toezegging.get('toezegging_aanwezig', ''))
        result['speech_act.toezegging.aantal'] = toezegging.get('aantal_toezeggen', '')
        result['speech_act.toezegging.kwaliteit'] = serialize_value(toezegging.get('kwaliteit_toezeggen', ''))

        # Addressing analysis
        adres = data.get('adressering_analyse', {})
        result['speech_act.adressering.effectiviteit'] = adres.get('adressering_effectiviteit', '')
        persoon = adres.get('persoonsvorm_distributie', {})
        for p in ['eerste_persoon', 'tweede_persoon', 'derde_persoon']:
            p_data = persoon.get(p, {})
            result[f'speech_act.adressering.{p}.frequentie'] = p_data.get('frequentie', '')

        # Sacramental pattern analysis
        sacr = data.get('sacramenteel_patroon_analyse', {})
        result['speech_act.sacramenteel.patroon'] = serialize_value(sacr.get('patroon_identificatie', ''))
        fout = sacr.get('foutief_patroon', {})
        result['speech_act.sacramenteel.foutief_aanwezig'] = serialize_value(fout.get('aanwezig', ''))
        sacr_patr = sacr.get('sacramenteel_patroon', {})
        result['speech_act.sacramenteel.sacramenteel_aanwezig'] = serialize_value(sacr_patr.get('aanwezig', ''))
        result['speech_act.sacramenteel.sacramenteel_kwaliteit'] = serialize_value(sacr_patr.get('kwaliteit', ''))

        # Diagnostic evaluation
        diag = data.get('diagnostische_evaluatie', {})
        result['speech_act.diagnose.primaire'] = serialize_value(diag.get('primaire_diagnose', ''))
        result['speech_act.diagnose.toelichting'] = serialize_value(diag.get('diagnose_toelichting', ''))
        result['speech_act.diagnose.sterke_punten'] = serialize_value(diag.get('sterke_punten', []))
        result['speech_act.diagnose.zwakke_punten'] = serialize_value(diag.get('zwakke_punten', []))
        result['speech_act.diagnose.gebeuren_score'] = diag.get('gebeuren_score', '')
        result['speech_act.diagnose.sacramentele_kracht'] = diag.get('sacramentele_kracht', '')

        # Theological depth analysis
        theol = data.get('theologische_diepte_analyse', {})
        openb = theol.get('openbaringsleer', {})
        result['speech_act.theologie.god_als_spreker'] = serialize_value(openb.get('god_als_spreker', ''))
        result['speech_act.theologie.prediker_mandataris'] = serialize_value(openb.get('prediker_als_mandataris', ''))
        pneum = theol.get('pneumatologie', {})
        result['speech_act.theologie.geest_rol'] = serialize_value(pneum.get('geest_rol_erkend', ''))
        sacr_theol = theol.get('sacramentstheologie', {})
        result['speech_act.theologie.preek_als_genademiddel'] = serialize_value(sacr_theol.get('preek_als_genademiddel', ''))

        # Recommendations
        aanbev = data.get('aanbevelingen', {})
        result['speech_act.aanbeveling.audit_samenvatting'] = serialize_value(aanbev.get('werkwoord_audit_samenvatting', ''))
        perf_int = aanbev.get('performatieve_intensivering', {})
        result['speech_act.aanbeveling.perf_intensivering_nodig'] = serialize_value(perf_int.get('nodig', ''))
        result['speech_act.aanbeveling.overall_beoordeling'] = serialize_value(aanbev.get('overall_beoordeling', ''))
        result['speech_act.aanbeveling.slotopmerking'] = serialize_value(aanbev.get('slotopmerking', ''))

    elif analysis_type == 'narrative':
        # Actantial analysis
        actant = data.get('actantiele_analyse', {})
        primair = actant.get('primair_narratief_programma', {})
        result['narrative.primair.beschrijving'] = serialize_value(primair.get('beschrijving', ''))

        # Subject
        subject = primair.get('subject', {})
        result['narrative.subject.identificatie'] = serialize_value(subject.get('identificatie', ''))
        result['narrative.subject.frequentie_score'] = subject.get('frequentie_score', '')

        # Object
        obj = primair.get('object', {})
        result['narrative.object.identificatie'] = serialize_value(obj.get('identificatie', ''))
        result['narrative.object.aard'] = serialize_value(obj.get('aard_van_object', ''))

        # Sender
        zender = primair.get('zender', {})
        result['narrative.zender.identificatie'] = serialize_value(zender.get('identificatie', ''))
        result['narrative.zender.rol'] = serialize_value(zender.get('rol_interpretatie', ''))

        # Receiver
        ontvanger = primair.get('ontvanger', {})
        result['narrative.ontvanger.identificatie'] = serialize_value(ontvanger.get('identificatie', ''))
        result['narrative.ontvanger.positie_hoorder'] = serialize_value(ontvanger.get('positie_hoorder', ''))

        # Helper
        helper = primair.get('helper', {})
        result['narrative.helper.identificatie'] = serialize_value(helper.get('identificatie', ''))
        result['narrative.helper.rol_god'] = serialize_value(helper.get('rol_van_god', ''))
        result['narrative.helper.rol_geest'] = serialize_value(helper.get('rol_van_geest', ''))

        # Opponent
        tegenst = primair.get('tegenstander', {})
        result['narrative.tegenstander.identificatie'] = serialize_value(tegenst.get('identificatie', ''))
        result['narrative.tegenstander.ernst'] = serialize_value(tegenst.get('ernst_tegenstander', ''))

        # Secondary narrative program
        secundair = actant.get('secundair_narratief_programma', {})
        result['narrative.secundair.aanwezig'] = serialize_value(secundair.get('aanwezig', ''))
        result['narrative.secundair.beschrijving'] = serialize_value(secundair.get('beschrijving', ''))
        result['narrative.secundair.verhouding'] = serialize_value(secundair.get('verhouding_tot_primair', ''))

        # Grammatical analysis (excluding raw counts: god_als_subject_count, mens_als_subject_count)
        gram = data.get('grammaticale_analyse', {})
        subject_check = gram.get('subject_check', {})
        result['narrative.grammaticaal.ratio'] = serialize_value(subject_check.get('ratio', ''))
        result['narrative.grammaticaal.rutledge_score'] = subject_check.get('rutledge_score', '')

        # Modal analysis
        modal = gram.get('modale_analyse', {})
        result['narrative.modal.dominante_modaliteit'] = serialize_value(modal.get('dominante_modaliteit', ''))
        result['narrative.modal.interpretatie'] = serialize_value(modal.get('modale_interpretatie', ''))

        # Semiotic square
        semiot = data.get('semiotisch_vierkant_analyse', {})
        prim_teg = semiot.get('primaire_tegenstelling', {})
        result['narrative.semiotisch.s1'] = serialize_value(prim_teg.get('s1', ''))
        result['narrative.semiotisch.s2'] = serialize_value(prim_teg.get('s2', ''))
        result['narrative.semiotisch.beweging'] = serialize_value(semiot.get('beweging_in_preek', ''))
        result['narrative.semiotisch.resolutie'] = serialize_value(semiot.get('theologische_resolutie', ''))

        # Diagnostic evaluation
        diag = data.get('diagnostische_evaluatie', {})
        result['narrative.diagnose.classificatie'] = serialize_value(diag.get('primaire_classificatie', ''))
        result['narrative.diagnose.toelichting'] = serialize_value(diag.get('classificatie_toelichting', ''))
        result['narrative.diagnose.indicatoren_moralisme'] = serialize_value(diag.get('indicatoren_moralisme', []))
        result['narrative.diagnose.indicatoren_genade'] = serialize_value(diag.get('indicatoren_genade', []))

        exemplarisme = diag.get('exemplarisme_check', {})
        result['narrative.exemplarisme.aanwezig'] = serialize_value(exemplarisme.get('aanwezig', ''))
        result['narrative.exemplarisme.figuren'] = serialize_value(exemplarisme.get('bijbelse_figuren_als_model', []))

        identificatie = diag.get('identificatie_patroon', {})
        result['narrative.identificatie.met'] = serialize_value(identificatie.get('hoorder_identificeert_met', ''))
        result['narrative.identificatie.effect'] = serialize_value(identificatie.get('effect_op_hoorder', ''))

        coherentie = diag.get('narratieve_coherentie', {})
        result['narrative.coherentie.score'] = coherentie.get('coherentie_score', '')

        # Theological depth
        theol = data.get('theologische_diepte_analyse', {})
        soter = theol.get('soteriologie', {})
        result['narrative.theologie.soteriologie_model'] = serialize_value(soter.get('primaire_model', ''))
        result['narrative.theologie.menselijke_rol'] = serialize_value(soter.get('menselijke_rol_in_redding', ''))

        pneum = theol.get('pneumatologie', {})
        result['narrative.theologie.geest_rol'] = serialize_value(pneum.get('rol_heilige_geest', ''))

        hamart = theol.get('hamartologie', {})
        result['narrative.theologie.zonde_aard'] = serialize_value(hamart.get('aard_van_zonde', ''))

        eschat = theol.get('eschatologie', {})
        result['narrative.theologie.hoop_structuur'] = serialize_value(eschat.get('hoop_structuur', ''))

        # Recommendations
        aanbev = data.get('aanbevelingen', {})
        result['narrative.aanbeveling.audit_samenvatting'] = serialize_value(aanbev.get('actantiele_audit_samenvatting', ''))
        subj_herp = aanbev.get('subject_herpositionering', {})
        result['narrative.aanbeveling.herpositionering_nodig'] = serialize_value(subj_herp.get('nodig', ''))
        result['narrative.aanbeveling.overall_beoordeling'] = serialize_value(aanbev.get('overall_beoordeling', ''))
        result['narrative.aanbeveling.slotopmerking'] = serialize_value(aanbev.get('slotopmerking', ''))

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
        if len(analyses) == 9:
            complete += 1
        else:
            missing = set(ANALYSIS_TYPES) - set(analyses.keys())
            incomplete.append((sermon_key, missing))

    print(f"  - Complete sermons (all 9 analyses): {complete}")
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
