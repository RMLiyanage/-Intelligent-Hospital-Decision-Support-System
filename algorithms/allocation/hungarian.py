import time
import tracemalloc
from typing import Any, Dict, List, Tuple

from data_structures.patient import Patient
from data_structures.resource import Resource


def hungarian_allocation(
    patients: List[Patient],
    resources: List[Resource],
) -> Dict[str, Any]:

    if not patients:
        return _empty_result('hungarian', "No patients provided")
    if not resources:
        return _empty_result('hungarian', "No resources provided")

    tracemalloc.start()
    t_start = time.perf_counter()

    # Expand resources by quantity into discrete unit slots (cap at 2 per resource to keep matrix dimension <= 50 for O(N^3) speed)
    unit_resources = []
    for r in resources:
        max_units = min(r.available_quantity, 2)
        for unit in range(max_units):
            unit_resources.append({
                'resource_id': r.resource_id,
                'resource_name': r.resource_name,
                'resource_type': r.resource_type,
                'hospital_id': r.hospital_id,
                'hospital_name': r.hospital_name,
                'object': r,
            })

    n = len(patients)
    m = len(unit_resources)
    dim = max(n, m)

    if dim == 0:
        return _empty_result('hungarian', "No resources available")

    # Build N×M cost matrix
    cost_matrix = []
    BIG_COST = 1000.0

    for i in range(dim):
        row = []
        for j in range(dim):
            if i < n and j < m:
                patient = patients[i]
                res = unit_resources[j]
                req_type = patient.required_resources[0] if patient.required_resources else None
                cost = res['object'].assignment_cost(patient.emergency_level, required_type=req_type)
                # Boost urgency: critical patients get negative cost offset to prioritize them
                prio_factor = (5 - patient.numeric_priority) * 0.1
                final_cost = max(0.01, cost - prio_factor)
                row.append(final_cost)
            else:
                row.append(BIG_COST)  # Padding for non-square matrix
        cost_matrix.append(row)

    # Solve matching via Hungarian algorithm
    matching = _solve_hungarian(cost_matrix, dim)

    assignments = []
    unassigned = []

    used_resource_units = set()

    for i in range(n):
        j = matching[i]
        patient = patients[i]
        if j < m and cost_matrix[i][j] < BIG_COST / 2:
            res = unit_resources[j]
            used_resource_units.add(j)
            assignments.append({
                'patient_id': patient.patient_id,
                'patient_name': patient.name,
                'emergency_level': patient.emergency_level,
                'resource_id': res['resource_id'],
                'resource_name': res['resource_name'],
                'resource_type': res['resource_type'],
                'hospital_id': res['hospital_id'],
                'hospital_name': res['hospital_name'],
                'match_cost': round(cost_matrix[i][j], 3),
                'priority_score': round(patient.priority_score(), 3),
            })
        else:
            unassigned.append({
                'patient_id': patient.patient_id,
                'patient_name': patient.name,
                'emergency_level': patient.emergency_level,
                'reason': 'No optimal matching resource available',
            })

    t_end = time.perf_counter()
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    total = len(patients)
    alloc_cnt = len(assignments)
    unalloc_cnt = len(unassigned)

    alloc_ratio = alloc_cnt / total if total > 0 else 0.0
    critical_satisfied = sum(1 for a in assignments if a['emergency_level'] in ('critical', 'high'))
    critical_total = sum(1 for p in patients if p.is_critical)
    crit_ratio = (critical_satisfied / critical_total) if critical_total > 0 else 1.0

    solution_quality = (alloc_ratio * 60.0) + (crit_ratio * 40.0)

    return {
        'assignments': assignments,
        'unassigned': unassigned,
        'allocated_count': alloc_cnt,
        'unassigned_count': unalloc_cnt,
        'total_patients': total,
        'satisfaction_rate': round(alloc_ratio * 100, 1),
        'critical_satisfaction_rate': round(crit_ratio * 100, 1),
        'solution_quality': round(solution_quality, 2),
        'execution_time_ms': (t_end - t_start) * 1000,
        'memory_kb': peak_mem / 1024,
        'algorithm': 'hungarian',
        'error': None,
    }


def _solve_hungarian(matrix: List[List[float]], n: int) -> List[int]:
    """
    Pure Python Hungarian Algorithm solver.

    Time Complexity: O(N³)

    Returns
    -------
    list[int] : matching array where matching[row] = col
    """
    u = [0.0] * (n + 1)
    v = [0.0] * (n + 1)
    p = [0] * (n + 1)
    way = [0] * (n + 1)

    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [float('inf')] * (n + 1)
        used = [False] * (n + 1)

        while True:
            used[j0] = True
            i0 = p[j0]
            delta = float('inf')
            j1 = 0

            for j in range(1, n + 1):
                if not used[j]:
                    cur = matrix[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur
                        way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]
                        j1 = j

            for j in range(0, n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta

            j0 = j1
            if p[j0] == 0:
                break

        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break

    matching = [-1] * n
    for j in range(1, n + 1):
        if p[j] != 0:
            matching[p[j] - 1] = j - 1

    return matching


def _empty_result(algo: str, error: str) -> Dict[str, Any]:
    return {
        'assignments': [], 'unassigned': [],
        'allocated_count': 0, 'unassigned_count': 0, 'total_patients': 0,
        'satisfaction_rate': 0.0, 'solution_quality': 0.0,
        'execution_time_ms': 0.0, 'memory_kb': 0.0,
        'algorithm': algo, 'error': error,
    }
