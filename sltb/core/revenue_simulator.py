"""
revenue_simulator.py
────────────────────
Automated passenger & revenue simulation for SLTB trips.

Logic:
  - Passengers board at each stop based on a realistic distribution.
  - Peak hours (06:00–09:00 and 17:00–19:00) produce significantly more riders.
  - Fares are distance-based (SLTB-style tiered pricing in LKR).
  - AC buses charge a ~30 % premium over non-AC.
  - Passengers gradually alight across stops (they don't all ride to the end).
  - The simulation is seeded per trip so results are reproducible but varied.
"""

import random
from decimal import Decimal
from datetime import time as dtime


# ── Fare tiers (LKR per passenger, approximate SLTB 2024 rates) ──────────────
# These apply to non-AC buses.  AC buses get a 1.30× multiplier.
FARE_TIERS = [
    (5,   20),   # 0–5 km
    (10,  30),
    (20,  45),
    (35,  65),
    (50,  90),
    (75,  130),
    (100, 175),
    (150, 230),
    (float('inf'), 280),
]

AC_MULTIPLIER = Decimal('1.30')


def _fare_for_distance(distance_km: float, is_ac: bool) -> Decimal:
    """Return the base fare for a given route distance."""
    fare = 20  # minimum
    for threshold, price in FARE_TIERS:
        if distance_km <= threshold:
            fare = price
            break
    base = Decimal(str(fare))
    return (base * AC_MULTIPLIER).quantize(Decimal('1')) if is_ac else base


def _is_peak(departure_time) -> bool:
    """True if the departure time falls within peak hours."""
    if departure_time is None:
        return False
    if isinstance(departure_time, dtime):
        t = departure_time
    else:
        # DateTimeField – extract the time part
        t = departure_time.time()

    morning_peak = dtime(6, 0) <= t <= dtime(9, 0)
    evening_peak = dtime(17, 0) <= t <= dtime(19, 0)
    return morning_peak or evening_peak


def simulate_trip_revenue(trip):
    """
    Simulate passenger boarding/alighting across all stops for a trip.

    Returns a dict ready to be persisted:
    {
        'total_passengers': int,
        'total_revenue': Decimal,
        'stops': [
            {
                'stop_name': str,
                'stop_order': int,
                'passengers_boarded': int,
                'passengers_alighted': int,
                'fare_per_passenger': Decimal,
                'stop_revenue': Decimal,
                'cumulative_passengers': int,
                'cumulative_revenue': Decimal,
            },
            ...
        ]
    }
    """
    schedule = trip.schedule
    route = schedule.timetable.route
    bus = schedule.bus

    # Bus capacity (default 50 if not set)
    capacity = bus.capacity or 50
    is_ac = bus.bus_type == 'AC'

    # Distance-based fare
    distance_km = route.distance or 30.0
    fare = _fare_for_distance(distance_km, is_ac)

    # Is it a peak-hour trip?
    departure_time = schedule.timetable.departure_time
    peak = _is_peak(departure_time)

    # Stops for this route (ordered)
    from .models import RouteStop
    route_stops = list(
        RouteStop.objects.filter(route=route)
        .select_related('stop')
        .order_by('order')
    )

    # If no stops defined, create synthetic ones based on route distance
    if not route_stops:
        num_stops = max(4, int(distance_km / 5))
        synthetic = []
        for i in range(num_stops):
            class FakeStop:
                pass
            rs = FakeStop()
            rs.order = i + 1
            rs.stop = FakeStop()
            rs.stop.stop_name = f"Stop {i + 1}"
            synthetic.append(rs)
        route_stops = synthetic

    num_stops = len(route_stops)

    # ── Passenger generation parameters ──────────────────────────────────────
    # Peak:   boarding avg = 60–80 % of capacity spread over stops
    # Normal: boarding avg = 25–45 % of capacity spread over stops

    rng = random.Random(trip.id * 31337)  # reproducible per trip

    if peak:
        # total boardings across whole trip: 70–110 % of capacity
        total_boardings_target = int(rng.uniform(0.70, 1.10) * capacity)
    else:
        # normal: 25–55 %
        total_boardings_target = int(rng.uniform(0.25, 0.55) * capacity)

    # Distribute boardings across stops (more at early stops, fewer at later ones)
    # Use a roughly exponential decay so front stops are busier
    weights = [max(1, num_stops - i) for i in range(num_stops)]
    total_weight = sum(weights)
    boardings_per_stop = [
        int((w / total_weight) * total_boardings_target) for w in weights
    ]

    # Add small per-stop random jitter  (±20 % of the stop's target)
    boardings_per_stop = [
        max(0, b + rng.randint(-max(1, b // 5), max(1, b // 5)))
        for b in boardings_per_stop
    ]

    # Don't board at the last stop
    boardings_per_stop[-1] = 0

    # ── Simulate stop-by-stop ─────────────────────────────────────────────────
    on_bus = 0
    cumulative_passengers = 0
    cumulative_revenue = Decimal('0')
    stops_data = []

    for idx, rs in enumerate(route_stops):
        boarded = min(boardings_per_stop[idx], max(0, capacity - on_bus))

        # Alighting: passengers randomly leave at each stop after the first
        if idx == 0:
            alighted = 0
        elif idx == num_stops - 1:
            alighted = on_bus  # everyone off at the last stop
        else:
            # 10–35 % of current riders alight at each intermediate stop
            alight_rate = rng.uniform(0.10, 0.35)
            alighted = min(on_bus, int(on_bus * alight_rate))

        on_bus = on_bus - alighted + boarded
        stop_revenue = fare * boarded
        cumulative_passengers += boarded
        cumulative_revenue += stop_revenue

        stops_data.append({
            'stop_name': rs.stop.stop_name,
            'stop_order': rs.order if hasattr(rs, 'order') else idx + 1,
            'passengers_boarded': boarded,
            'passengers_alighted': alighted,
            'fare_per_passenger': fare,
            'stop_revenue': stop_revenue,
            'cumulative_passengers': cumulative_passengers,
            'cumulative_revenue': cumulative_revenue,
        })

    return {
        'total_passengers': cumulative_passengers,
        'total_revenue': cumulative_revenue,
        'stops': stops_data,
    }
