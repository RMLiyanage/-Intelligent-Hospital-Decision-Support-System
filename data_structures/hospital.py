
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Hospital:
   
    hospital_id: int
    name: str
    location_id: int
    location_name: str = ""
    address: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    capacity: int = 100
    available_beds: int = 50
    icu_beds: int = 10
    available_icu_beds: int = 5
    rating: float = 3.0
    status: str = 'active'
    opening_time: str = '08:00:00'
    closing_time: str = '20:00:00'
    avg_wait_time_min: int = 30
    distance_km: float = 0.0
    available_doctors: List[Dict[str, Any]] = field(default_factory=list)
    available_resources: List[Dict[str, Any]] = field(default_factory=list)

    def __hash__(self) -> int:
        return hash(self.hospital_id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Hospital) and self.hospital_id == other.hospital_id

    # -------------------------------------------------------- #
    # Status checks                                            #
    # -------------------------------------------------------- #

    @property
    def is_available(self) -> bool:
        """True if hospital is active and has at least one free bed."""
        return self.status == 'active' and self.available_beds > 0

    @property
    def bed_utilization(self) -> float:
        """Bed occupancy rate [0.0, 1.0]. 1.0 = fully occupied."""
        if self.capacity == 0:
            return 1.0
        return 1.0 - (self.available_beds / self.capacity)

    @property
    def icu_utilization(self) -> float:
        """ICU occupancy rate [0.0, 1.0]."""
        if self.icu_beds == 0:
            return 1.0
        return 1.0 - (self.available_icu_beds / self.icu_beds)

    def has_specialty(self, specialization: str) -> bool:
      
        spec_lower = specialization.lower()
        return any(
            d.get('specialization', '').lower() == spec_lower
            and d.get('availability_status') == 'available'
            for d in self.available_doctors
        )

    def has_resource(self, resource_type: str) -> bool:
      
        rtype_lower = resource_type.lower()
        return any(
            r.get('resource_type', '').lower() == rtype_lower
            and int(r.get('available_quantity', 0)) > 0
            for r in self.available_resources
        )

    # -------------------------------------------------------- #
    # Normalization for Weighted Ranking (Module 4)            #
    # -------------------------------------------------------- #

    def normalized_rating(self, max_rating: float = 5.0) -> float:
       
        return max(0.0, min(1.0, self.rating / max_rating))

    def normalized_availability(self) -> float:
        
        if self.capacity == 0:
            return 0.0
        return min(1.0, self.available_beds / self.capacity)

    def normalized_distance(self, max_distance_km: float) -> float:
     
        if max_distance_km <= 0:
            return 1.0
        return max(0.0, 1.0 - (self.distance_km / max_distance_km))

    def normalized_wait_time(self, max_wait_min: float = 120.0) -> float:
     
        return max(0.0, 1.0 - (self.avg_wait_time_min / max_wait_min))

    def normalized_resources(self) -> float:
    
        if not self.available_resources:
            return 0.0
        available_count = sum(
            1 for r in self.available_resources
            if int(r.get('available_quantity', 0)) > 0
        )
        return available_count / len(self.available_resources)

    # -------------------------------------------------------- #
    # Serialisation                                            #
    # -------------------------------------------------------- #

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serialisable dict for API responses."""
        return {
            'id': self.hospital_id,
            'name': self.name,
            'location_id': self.location_id,
            'location_name': self.location_name,
            'address': self.address,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'capacity': self.capacity,
            'available_beds': self.available_beds,
            'icu_beds': self.icu_beds,
            'available_icu_beds': self.available_icu_beds,
            'rating': self.rating,
            'status': self.status,
            'opening_time': str(self.opening_time),
            'closing_time': str(self.closing_time),
            'avg_wait_time_min': self.avg_wait_time_min,
            'distance_km': round(self.distance_km, 2),
            'is_available': self.is_available,
            'bed_utilization': round(self.bed_utilization, 3),
            'icu_utilization': round(self.icu_utilization, 3),
        }

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Hospital':
        """Construct a Hospital from a database query result dict."""
        return cls(
            hospital_id=int(row['id']),
            name=row['name'],
            location_id=int(row['location_id']),
            location_name=row.get('location_name', ''),
            address=row.get('address', ''),
            latitude=float(row.get('latitude', 0)),
            longitude=float(row.get('longitude', 0)),
            capacity=int(row.get('capacity', 100)),
            available_beds=int(row.get('available_beds', 50)),
            icu_beds=int(row.get('icu_beds', 10)),
            available_icu_beds=int(row.get('available_icu_beds', 5)),
            rating=float(row.get('rating', 3.0)),
            status=row.get('status', 'active'),
            opening_time=str(row.get('opening_time', '08:00:00')),
            closing_time=str(row.get('closing_time', '20:00:00')),
            avg_wait_time_min=int(row.get('avg_wait_time_min', 30)),
        )
