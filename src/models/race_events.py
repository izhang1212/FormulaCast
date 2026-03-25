# Stochastic race event generators calibrated from historical race data
    # Models race events (safety car deployment, overtake, pitstop)

import numpy as np

# Model Safety Car deployments per race
class SafetyCarModel:

    def __init__(self, base_prob_per_lap = 0.015, first_lap_multiplier = 4.0):
        self.base_prob = base_prob_per_lap
        self.first_lap_multiplier = first_lap_multiplier

    # Returns list of laps where safety car is deployed
    def simulate(self, total_laps: int, rng: np.random.Generator) -> list[int]:
        
        sc_laps = []
        cooldown = 0

        for lap in range(1, total_laps + 1):
            # each time reduce cooldown
            if cooldown > 0:
                cooldown -= 1
                continue
            
            prob = self.base_prob
            # apply multiplier for first few laps
            if lap <= 3:
                prob *= self.first_lap_multiplier

            if rng.random() < prob:
                sc_laps.append(lap)
                cooldown = 4  

        return sc_laps
    
# Models situations in which a car does not finish
class DNFModel:

    def __init__(self, base_mechanical_rate = 0.33, first_lap_accident_rate = 0.08):
        self.mechanical_rate = base_mechanical_rate
        self.first_lap_rate = first_lap_accident_rate

    def simulate(
        self, 
        drivers: list[str], 
        team_reliability: dict,
        rng: np.random.Generator
    ) -> dict:
        
        dnfs = {}

        for driver in drivers:
            # First lap accident
            if rng.random() < self.first_lap_rate:
                dnfs[driver] = 1
                continue
            
            # Mechanical failure
            reliability = team_reliability.get(driver, 1.0)
            if rng.random() < self.mechanical_rate * reliability:
                dnfs[driver] = rng.integers(2, 60)

        return dnfs
    
class PitStopModel:

    def __init__(
        self, 
        mean_time = 2.5, 
        std_time = 0.4,
        error_prob = 0.02,
        error_penalty = 5.0
    ):
        self.mean_time = mean_time
        self.std_time = std_time
        self.error_prob = error_prob
        self.error_penalty = error_penalty

    # returns pit stop time in seconds
    def simulate_stop(self, team_avg: float, rng: np.random.Generator) -> float:

        base = rng.normal(loc = team_avg, scale = self.std_time)
        
        if rng.random() < self.error_prob:
            base += self.error_penalty

        return max(base, 1.8)

class OvertakeModel:

    def __init__(self, pace_threshold = 0.3, overtake_base_prob = 0.15):
        self.pace_threshold = pace_threshold
        self.overtake_prob = overtake_base_prob

    # Given a pace delta (seconds per lap,  positive = faster)
        # Returns whether an overtake succeeds (True) or fails (False)
    def attempt_overtake(self, pace_delta: float, rng: np.random.Generator) -> bool:
        
        if pace_delta < self.pace_threshold:
            return False

        prob = min(self.overtake_prob * (pace_delta / self.pace_threshold), 0.8)
        return rng.random() < prob