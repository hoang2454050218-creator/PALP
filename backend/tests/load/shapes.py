"""
Custom LoadTestShape classes for PALP performance scenarios.

Each shape defines a time-based ramp pattern matching PALP SLO requirements:
  - CONCURRENT_USERS_STABLE = 200
  - CONCURRENT_USERS_SPIKE  = 300

Usage:
    # Soak (30-min endurance):
    locust -f locustfile.py,shapes.py --host=... SoakShape

    # Spike (burst to 300 users in 30s):
    locust -f locustfile.py,shapes.py --host=... SpikeShape

    # Stress (200 users, 15 min sustained):
    locust -f locustfile.py,shapes.py --host=... StressShape
"""
import math

from locust import LoadTestShape


# ---------------------------------------------------------------------------
# Soak Test -- LT-05 variant: 200 users held for 30 minutes
#   Detects memory leaks, connection pool exhaustion, cache drift
#
# Timeline:
#   0:00 - 2:00   ramp up to 200
#   2:00 - 32:00  hold at 200  (30 min steady state)
#   32:00 - 33:00 ramp down to 0
# ---------------------------------------------------------------------------
class SoakShape(LoadTestShape):
    RAMP_UP_SECONDS = 120
    HOLD_SECONDS = 1800          # 30 minutes
    RAMP_DOWN_SECONDS = 60
    TARGET_USERS = 200
    SPAWN_RATE = 10

    stages = [
        {"duration": RAMP_UP_SECONDS,
         "users": TARGET_USERS, "spawn_rate": SPAWN_RATE},
        {"duration": RAMP_UP_SECONDS + HOLD_SECONDS,
         "users": TARGET_USERS, "spawn_rate": SPAWN_RATE},
        {"duration": RAMP_UP_SECONDS + HOLD_SECONDS + RAMP_DOWN_SECONDS,
         "users": 0, "spawn_rate": SPAWN_RATE},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]
        return None


# ---------------------------------------------------------------------------
# Spike Test -- LT-04: burst from 200 → 300 in 30 seconds, hold 5 min
#   Validates auto-scaling / graceful degradation and recovery
#
# Timeline:
#   0:00 - 2:00   ramp to 200
#   2:00 - 7:00   hold at 200 (warm up)
#   7:00 - 7:30   spike to 300 in 30s (spawn_rate=20)
#   7:30 - 12:30  hold at 300  (5 min spike window)
#   12:30 - 13:00 drop back to 200
#   13:00 - 15:00 hold at 200  (recovery observation)
#   15:00 - 16:00 ramp down to 0
# ---------------------------------------------------------------------------
class SpikeShape(LoadTestShape):
    STABLE = 200
    SPIKE = 300

    stages = [
        {"duration": 120,  "users": STABLE, "spawn_rate": 10},
        {"duration": 420,  "users": STABLE, "spawn_rate": 10},
        {"duration": 450,  "users": SPIKE,  "spawn_rate": 20},
        {"duration": 750,  "users": SPIKE,  "spawn_rate": 20},
        {"duration": 780,  "users": STABLE, "spawn_rate": 20},
        {"duration": 900,  "users": STABLE, "spawn_rate": 10},
        {"duration": 960,  "users": 0,      "spawn_rate": 10},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]
        return None


# ---------------------------------------------------------------------------
# Stress Test -- LT-03: 200 concurrent users for 15 minutes
#   Validates sustained throughput at the SLO boundary
#
# Timeline:
#   0:00 - 5:00   ramp to 200 (gradual, 40 users/min)
#   5:00 - 20:00  hold at 200 (15 min)
#   20:00 - 21:00 ramp down to 0
# ---------------------------------------------------------------------------
class StressShape(LoadTestShape):
    TARGET = 200

    stages = [
        {"duration": 300,  "users": TARGET, "spawn_rate": 5},
        {"duration": 1200, "users": TARGET, "spawn_rate": 5},
        {"duration": 1260, "users": 0,      "spawn_rate": 10},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]
        return None


# ---------------------------------------------------------------------------
# Normal Load -- LT-01/02 baseline: ramp 50 → 100 users, 10 min each
# ---------------------------------------------------------------------------
class NormalLoadShape(LoadTestShape):

    stages = [
        {"duration": 60,   "users": 50,  "spawn_rate": 5},
        {"duration": 660,  "users": 50,  "spawn_rate": 5},
        {"duration": 720,  "users": 100, "spawn_rate": 5},
        {"duration": 1320, "users": 100, "spawn_rate": 5},
        {"duration": 1380, "users": 0,   "spawn_rate": 10},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]
        return None
