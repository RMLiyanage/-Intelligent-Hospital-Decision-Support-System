

import time
import tracemalloc
from typing import Any, Dict, List, Optional

from data_structures.hospital import Hospital
from data_structures.patient import Patient


def decision_tree_recommendation(
    patient: Patient,
    hospitals: List[Hospital],
) -> Dict[str, Any]:
 
    if not hospitals:
        return _empty_result('decision_tree', "No hospitals provided")

    tracemalloc.start()
    t_start = time.perf_counter()

    evaluated = []

    for h in hospitals:
        rule_path = []
        tier = 3  # Default lowest tier
        score = 50.0

        # Node 1: Emergency Hard Constraint
        if patient.is_critical:
            if h.available_icu_beds > 0:
                rule_path.append("ICU Available (+30)")
                score += 30.0
            else:
                rule_path.append("NO ICU (-40)")
                score -= 40.0
        else:
            if h.available_beds > 0:
                rule_path.append("Beds Available (+15)")
                score += 15.0

        # Node 2: Specialty Match
        has_spec = (patient.required_specialization and
                    h.has_specialty(patient.required_specialization))
        if has_spec:
            rule_path.append("Specialty Matched (+25)")
            score += 25.0
        elif not patient.required_specialization:
            rule_path.append("General Patient (+10)")
            score += 10.0
        else:
            rule_path.append("No Spec Match (-10)")
            score -= 10.0

        # Node 3: Distance Threshold
        if h.distance_km <= 25.0:
            rule_path.append("Within 25km (+20)")
            score += 20.0
        elif h.distance_km <= 60.0:
            rule_path.append("Within 60km (+10)")
            score += 10.0
        else:
            rule_path.append("Far Distance (-15)")
            score -= 15.0

        # Node 4: Quality Check
        if h.rating >= 4.5:
            rule_path.append("High Rating (+10)")
            score += 10.0

        final_score = max(0.0, min(100.0, score))

        evaluated.append({
            'hospital_id': h.hospital_id,
            'hospital_name': h.name,
            'location_id': h.location_id,
            'location_name': h.location_name,
            'composite_score': round(final_score, 2),
            'distance_km': round(h.distance_km, 2),
            'available_beds': h.available_beds,
            'available_icu_beds': h.available_icu_beds,
            'rating': h.rating,
            'avg_wait_time_min': h.avg_wait_time_min,
            'rule_path': " → ".join(rule_path),
        })

    evaluated.sort(key=lambda x: x['composite_score'], reverse=True)

    t_end = time.perf_counter()
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    rec = evaluated[0] if evaluated else None

    return {
        'rankings': evaluated,
        'recommended_hospital': rec,
        'total_candidates': len(evaluated),
        'execution_time_ms': (t_end - t_start) * 1000,
        'memory_kb': peak_mem / 1024,
        'algorithm': 'decision_tree',
        'error': None,
    }


def _empty_result(algo: str, error: str) -> Dict[str, Any]:
    return {
        'rankings': [], 'recommended_hospital': None,
        'total_candidates': 0,
        'execution_time_ms': 0.0, 'memory_kb': 0.0,
        'algorithm': algo, 'error': error,
    }
