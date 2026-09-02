"""
data_structures/priority_queue.py
==================================
Min-heap priority queue for MediRoute algorithms.

WHY A PRIORITY QUEUE?
---------------------
A*, Dijkstra, and Greedy Allocation all share the same core need:
repeatedly find the item with the MINIMUM cost/priority from a
dynamic set that grows and shrinks during execution.

IMPLEMENTATION: Binary Min-Heap (via Python heapq)
----------------------------------------------------
Python's heapq module provides heap operations on a plain list.
We wrap it with a class to provide:

  1. Clean API     — hide the (priority, counter, item) tuple pattern
  2. Tie-breaking  — monotonic counter prevents comparisons on items
  3. Membership    — O(1) contains() via _entry_finder dict
  4. Update        — lazy deletion for update_priority()

OPERATION COSTS
---------------
  push(item, priority)          O(log n)
  pop()                         O(log n) amortised
  peek()                        O(1) amortised
  update_priority(item, p)      O(log n) — lazy deletion + re-push
  contains(item)                O(1)
  get_priority(item)            O(1)

vs. Sorted List alternative:
  push  O(n)  ← too slow for graphs with thousands of nodes
  pop   O(1)

LAZY DELETION PATTERN
---------------------
When A* finds a shorter path to a node already in the open set,
we cannot efficiently find and remove its old heap entry.

Solution:
  1. Mark old entry as _REMOVED (O(1))
  2. Push a new entry with the updated priority (O(log n))
  3. During pop(), skip any _REMOVED entries (amortised O(log n))

This gives O(log n) priority update instead of O(n) linear search.

HEAP INVARIANT
--------------
For a min-heap rooted at index 0:
  heap[parent].priority <= heap[child].priority  for all children

Python's heapq maintains this invariant automatically.

MODULE USAGE
------------
  Module 1 (Route Optimization): A* open set, Dijkstra unvisited set
  Module 2 (Resource Allocation): patient priority queue
  Module 5 (Scheduling): job priority queue for greedy scheduler
"""

import heapq
from typing import Any, Dict, List, Optional, Tuple


class PriorityQueue:
    """
    Min-heap priority queue with O(log n) push, pop, and update.

    Lower priority value = processed first (min-heap).

    Attributes
    ----------
    _heap         : list — (priority, counter, item) tuples
    _counter      : int  — monotonically increasing; breaks priority ties
    _entry_finder : dict — item → heap entry (list); enables O(1) lookup
    _REMOVED      : sentinel object marking logically deleted entries

    Usage Example (A* open set)
    ---------------------------
        pq = PriorityQueue()

        pq.push('Colombo',  priority=0.0)
        pq.push('Kandy',    priority=116.0)
        pq.push('Galle',    priority=120.0)

        node = pq.pop()          # → 'Colombo' (lowest f-score)

        # Shorter path to Kandy found — update its priority
        pq.update_priority('Kandy', 98.0)
        node = pq.pop()          # → 'Kandy' (now priority 98.0)
    """

    # Sentinel — a unique object that is faster to compare than a string
    _REMOVED: object = object()

    def __init__(self) -> None:
        self._heap: List[List] = []          # mutable lists so we can mark removed
        self._counter: int = 0
        self._entry_finder: Dict[Any, List] = {}

    # -------------------------------------------------------- #
    # Core operations                                          #
    # -------------------------------------------------------- #

    def push(self, item: Any, priority: float) -> None:
        """
        Add item with the given priority.

        If item already exists, its priority is updated (lazy deletion).

        Time: O(log n)
        """
        if item in self._entry_finder:
            self._mark_removed(item)

        entry: List = [priority, self._counter, item]
        self._counter += 1
        self._entry_finder[item] = entry
        heapq.heappush(self._heap, entry)

    def pop(self) -> Any:
        """
        Remove and return the item with the LOWEST priority.

        Skips logically removed entries (lazy deletion).

        Time: O(log n) amortised

        Raises
        ------
        KeyError : If the queue is empty.
        """
        while self._heap:
            _priority, _count, item = heapq.heappop(self._heap)
            if item is not self._REMOVED:
                del self._entry_finder[item]
                return item
        raise KeyError("pop from an empty PriorityQueue")

    def pop_with_priority(self) -> Tuple[Any, float]:
        """
        Remove and return (item, priority) of the lowest-priority item.

        Time: O(log n) amortised
        """
        while self._heap:
            priority, _count, item = heapq.heappop(self._heap)
            if item is not self._REMOVED:
                del self._entry_finder[item]
                return item, priority
        raise KeyError("pop from an empty PriorityQueue")

    def peek(self) -> Any:
        """
        Return lowest-priority item WITHOUT removing it.

        Time: O(1) amortised (may skip removed entries once)
        """
        while self._heap:
            _priority, _count, item = self._heap[0]
            if item is not self._REMOVED:
                return item
            heapq.heappop(self._heap)
        raise KeyError("peek on an empty PriorityQueue")

    def peek_priority(self) -> float:
        """Return the minimum priority value without removing. O(1) amortised."""
        while self._heap:
            priority, _count, item = self._heap[0]
            if item is not self._REMOVED:
                return priority
            heapq.heappop(self._heap)
        raise KeyError("peek on an empty PriorityQueue")

    def update_priority(self, item: Any, new_priority: float) -> None:
        """
        Update an existing item's priority using lazy deletion.

        LAZY DELETION:
          - Mark old entry as _REMOVED in O(1)
          - Push new entry with updated priority in O(log n)
          - Skip _REMOVED entries on pop() — amortised cost spread out

        This avoids the O(n) cost of finding and removing the old entry
        from the middle of the heap.

        Time: O(log n)
        """
        self._mark_removed(item)
        self.push(item, new_priority)

    # -------------------------------------------------------- #
    # Query operations                                         #
    # -------------------------------------------------------- #

    def is_empty(self) -> bool:
        """Return True if no active items exist. O(1)."""
        return not self._entry_finder

    def contains(self, item: Any) -> bool:
        """Check membership. O(1)."""
        return item in self._entry_finder

    def get_priority(self, item: Any) -> Optional[float]:
        """
        Get current priority of item. O(1).
        Returns None if item not in queue.
        """
        entry = self._entry_finder.get(item)
        return entry[0] if entry is not None else None

    # -------------------------------------------------------- #
    # Internal helpers                                         #
    # -------------------------------------------------------- #

    def _mark_removed(self, item: Any) -> None:
        """
        Mark an existing entry as logically REMOVED.

        Sets the item slot to _REMOVED sentinel.
        The dead entry stays in the heap until popped and discarded.

        Time: O(1)
        """
        entry = self._entry_finder.pop(item)
        entry[2] = self._REMOVED  # mutate in-place — no heap restructure needed

    # -------------------------------------------------------- #
    # Python dunder methods                                    #
    # -------------------------------------------------------- #

    def __len__(self) -> int:
        """Number of ACTIVE (non-removed) items. O(1)."""
        return len(self._entry_finder)

    def __contains__(self, item: Any) -> bool:
        return self.contains(item)

    def __bool__(self) -> bool:
        return not self.is_empty()

    def __repr__(self) -> str:
        if self.is_empty():
            return "PriorityQueue(empty)"
        try:
            top = self.peek_priority()
            return f"PriorityQueue(size={len(self)}, min_priority={top:.4f})"
        except KeyError:
            return "PriorityQueue(empty)"
