"""
data_structures/__init__.py
============================
MediRoute Data Structures package.

Exports all data structure classes used by the five algorithm modules.

Data Structures Summary
-----------------------
┌────────────────────┬──────────────────────────────────────────────┐
│ Class              │ Used By                                      │
├────────────────────┼──────────────────────────────────────────────┤
│ Graph              │ Modules 1 (route) and 3 (network)           │
│ GraphNode          │ Modules 1 and 3                             │
│ GraphEdge          │ Modules 1 and 3                             │
│ PriorityQueue      │ Modules 1 (A*, Dijkstra) and 2 (Greedy)    │
│ Hospital           │ Modules 2, 4                                │
│ Patient            │ All modules                                 │
│ Doctor             │ Modules 2, 4, 5                             │
│ Resource           │ Module 2 (Allocation)                       │
│ Appointment        │ Module 5 (Scheduling)                       │
│ TimeSlot           │ Module 5 (Scheduling)                       │
│ Schedule           │ Module 5 (Scheduling)                       │
│ ScheduleEntry      │ Module 5 (Scheduling)                       │
│ Chromosome         │ Module 5 (Genetic Algorithm)               │
│ Population         │ Module 5 (Genetic Algorithm)               │
└────────────────────┴──────────────────────────────────────────────┘
"""

from data_structures.graph import Graph, GraphNode, GraphEdge
from data_structures.priority_queue import PriorityQueue
from data_structures.hospital import Hospital
from data_structures.patient import Patient
from data_structures.doctor import Doctor
from data_structures.resource import Resource
from data_structures.appointment import Appointment
from data_structures.schedule import Schedule, ScheduleEntry, TimeSlot
from data_structures.chromosome import Chromosome, Population

__all__ = [
    'Graph', 'GraphNode', 'GraphEdge',
    'PriorityQueue',
    'Hospital',
    'Patient',
    'Doctor',
    'Resource',
    'Appointment',
    'Schedule', 'ScheduleEntry', 'TimeSlot',
    'Chromosome', 'Population',
]
