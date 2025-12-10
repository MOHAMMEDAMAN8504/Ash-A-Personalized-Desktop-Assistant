# Backend/RLPolicy.py
import os, json, time, math, random
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "Data"
DATA_DIR.mkdir(exist_ok=True)
POLICY_PATH = DATA_DIR / "rl_policy.json"
METRICS_PATH = DATA_DIR / "metrics.csv"   # optional; created on first write

# Always-on defaults (no toggles needed)
EPSILON = 0.08   # ~8% exploration
MIN_TRIALS_TO_SWITCH = 5

# Arms per decision point (bounded for safety)
ARMS = {
    "search": {
        "retrieval_k": [3, 5],
        "tie_breaker": ["prefer_realtime", "prefer_general"]
    },
    "chat": {
        "temperature": [0.3, 0.7]
    }
}

def _load_state():
    if POLICY_PATH.exists():
        try:
            return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    # initialize
    state = {}
    for dp, dims in ARMS.items():
        state[dp] = {}
        for name, values in dims.items():
            state[dp][name] = {str(v): {"count": 0, "mean_reward": 0.0} for v in values}
    return state

def _save_state(state):
    try:
        POLICY_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        pass

def _log_metric(row: str):
    # optional: append a CSV row
    try:
        new_file = not METRICS_PATH.exists()
        with open(METRICS_PATH, "a", encoding="utf-8") as f:
            if new_file:
                f.write("ts,decision_point,param,value,reward,epsilon\n")
            f.write(row + "\n")
    except Exception:
        pass

class RLPolicy:
    def __init__(self, epsilon: float = EPSILON):
        self.epsilon = epsilon
        self.state = _load_state()

    def choose(self, decision_point: str, context: dict | None = None) -> dict:
        # epsilon-greedy per parameter dimension
        choice = {}
        dims = ARMS.get(decision_point, {})
        for name, values in dims.items():
            if random.random() < self.epsilon:
                val = random.choice(values)
            else:
                # exploit best mean_reward (break ties by higher count)
                best = None
                best_score = -1e9
                for v in values:
                    slot = self.state[decision_point][name][str(v)]
                    score = slot["mean_reward"]
                    # prefer explored arms slightly
                    score += 1e-6 * slot["count"]
                    if score > best_score:
                        best, best_score = v, score
                val = best
            choice[name] = val
        return choice

    def reward(self, decision_point: str, choice: dict, success: bool):
        r = 1.0 if success else 0.0
        dims = ARMS.get(decision_point, {})
        now = time.time()
        for name, values in dims.items():
            v = choice.get(name)
            if v is None:
                continue
            slot = self.state[decision_point][name][str(v)]
            c = slot["count"]
            m = slot["mean_reward"]
            # online mean update
            new_mean = m + (r - m) / (c + 1)
            slot["count"] = c + 1
            slot["mean_reward"] = round(new_mean, 4)
            # optional metric row
            _log_metric(f"{now},{decision_point},{name},{v},{int(r)},{self.epsilon}")
        _save_state(self.state)
