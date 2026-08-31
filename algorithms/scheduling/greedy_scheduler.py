"""
algorithms/scheduling/greedy_scheduler.py
============================================
Module 5 — Scheduling Optimization: Greedy Priority Scheduler

PROBLEM STATEMENT
-----------------
Schedule N patient appointments across M available doctor time slots to
minimize waiting times and eliminate room/doctor schedule conflicts.

GREEDY HEURISTIC: Earliest Deadline First (EDF) + Priority First
-----------------------------------------------------------------
1. Sort appointments by emergency priority (critical first) then requested duration.
2. For each appointment, find the earliest available non-conflicting time slot
   with an available doctor.
3. Assign slot and update schedule.

COMPLEXITY
----------
  Time  : O(N log N + N × S)  where N = appointments, S = total time slots
  Space : O(N + S)

COMPARISON IN MODULE 5
----------------------
  - Greedy: O(N log N) — fast, greedy baseline, may get trapped in local optima.
  - Genetic Algorithm: Metaheuristic search — avoids local optima via population crossover.
  - Brute Force: O(N!) — exact global optimum, feasible ONLY for N ≤ 8.
"""

import time
import tracemalloc
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from data_structures.appointment import Appointment
from data_structures.doctor import Doctor
from data_structures.schedule import Schedule, ScheduleEntry


def greedy_scheduler(
    appointments: List[Appointment],
    doctors: List[Doctor],
    base_datetime: Optional[datetime] = None,
    slot_duration_min: int = 30,
) -> Dict[str, Any]:
    """
    Greedy Priority Scheduler.

    Baseline algorithm for Module 5.

    Parameters
    ----------
    appointments     : List of Appointment dataclasses to schedule
    doctors          : List of Doctor dataclasses available
    base_datetime    : Start date/time for scheduling grid
    slot_duration_min: Duration of each slot (default 30 min)

    Returns
    -------
    dict with keys:
        schedule          : Schedule dataclass instance / dict
        scheduled_count   : int
        unscheduled_count : int
        total_appointments: int
        fitness_score     : float [0, 100]
        conflicts         : int
        avg_wait_time_min : float
        execution_time_ms : float
        memory_kb         : float
        algorithm         : 'greedy_scheduler'
    """
    if not appointments:
        return _empty_result('greedy_scheduler', "No appointments provided")

    tracemalloc.start()
    t_start = time.perf_counter()

    if base_datetime is None:
        base_datetime = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)

    # Sort appointments by emergency priority (lower priority value = more urgent)
    sorted_appts = sorted(appointments, key=lambda a: (a.priority_value, a.duration_min))

    doc_map = {d.doctor_id: d for d in doctors}

    # Doctor busy timelines: doctor_id → list of (start, end)
    doc_timeline: Dict[int, List[Tuple[datetime, datetime]]] = {
        d.doctor_id: [] for d in doctors
    }

    schedule = Schedule(total_patients=len(appointments), algorithm_used='greedy_scheduler')
    unscheduled = []

    for appt in sorted_appts:
        # Find an available doctor matching hospital/spec or any available
        target_doc_ids = [
            d.doctor_id for d in doctors
            if d.hospital_id == appt.hospital_id and d.is_available
        ]
        if not target_doc_ids:
            target_doc_ids = [d.doctor_id for d in doctors if d.is_available]

        if not target_doc_ids:
            unscheduled.append(appt)
            continue

        scheduled_slot = False
        duration = timedelta(minutes=appt.duration_min)

        # Search time slots from 8 AM to 5 PM
        for slot_idx in range(18):  # 18 slots of 30 min = 9 hours
            slot_start = base_datetime + timedelta(minutes=slot_idx * slot_duration_min)
            slot_end = slot_start + duration

            for doc_id in target_doc_ids:
                # Check doctor conflict
                conflict = False
                for start, end in doc_timeline[doc_id]:
                    if slot_start < end and start < slot_end:
                        conflict = True
                        break

                if not conflict:
                    # Book slot
                    doc_timeline[doc_id].append((slot_start, slot_end))

                    wait_min = max(0.0, (slot_start - base_datetime).total_seconds() / 60.0)

                    doc = doc_map.get(doc_id)
                    doc_name = doc.name if doc else f"Dr. {doc_id}"

                    entry = ScheduleEntry(
                        patient_id=appt.patient_id,
                        doctor_id=doc_id,
                        room=appt.room_number or f"Room {(slot_idx % 10) + 1:02d}",
                        start_time=slot_start,
                        end_time=slot_end,
                        emergency_level=appt.emergency_level,
                        patient_name=appt.patient_name,
                        doctor_name=doc_name,
                        wait_time_min=wait_min,
                    )
                    schedule.add_entry(entry)
                    scheduled_slot = True
                    break

            if scheduled_slot:
                break

        if not scheduled_slot:
            unscheduled.append(appt)

    t_end = time.perf_counter()
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    fitness = schedule.fitness()

    return {
        'schedule': schedule.to_dict(),
        'scheduled_count': schedule.scheduled_count,
        'unscheduled_count': len(unscheduled),
        'total_appointments': len(appointments),
        'fitness_score': round(fitness, 2),
        'conflicts': schedule.count_conflicts(),
        'avg_wait_time_min': round(schedule.avg_wait_time(), 1),
        'execution_time_ms': (t_end - t_start) * 1000,
        'memory_kb': peak_mem / 1024,
        'algorithm': 'greedy_scheduler',
        'error': None,
    }


def _empty_result(algo: str, error: str) -> Dict[str, Any]:
    return {
        'schedule': {}, 'scheduled_count': 0, 'unscheduled_count': 0,
        'total_appointments': 0, 'fitness_score': 0.0, 'conflicts': 0,
        'avg_wait_time_min': 0.0,
        'execution_time_ms': 0.0, 'memory_kb': 0.0,
        'algorithm': algo, 'error': error,
    }
