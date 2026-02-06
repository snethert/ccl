#!/usr/bin/env python3
import json
import os
import sys
from typing import List, Dict

STEPS: List[str] = [
    "Step 1: Lisp-side interrupt hook at UI boundaries",
    "Step 2: Lisp-side UI mapping (enqueue ui:interrupt + yieldUiTurn)",
    "Step 3: Host interrupt API usable end-to-end",
    "Step 4: Lisp-level interrupt delivery test",
    "Step 5: Build + test verification",
]

STATE_FILE = os.path.join(os.path.dirname(__file__), ".interrupt_steps.json")


def load_state() -> Dict[str, bool]:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return {str(k): bool(v) for k, v in data.items()}
    except Exception:
        return {}


def save_state(state: Dict[str, bool]) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)


def print_status(state: Dict[str, bool]) -> None:
    for idx, step in enumerate(STEPS, start=1):
        key = str(idx)
        done = state.get(key, False)
        status = "DONE" if done else "PENDING"
        print(f"[{status}] {idx}. {step}")


def complete_step(state: Dict[str, bool], step_num: int) -> None:
    if step_num < 1 or step_num > len(STEPS):
        raise ValueError(f"step must be between 1 and {len(STEPS)}")
    state[str(step_num)] = True
    save_state(state)


def reset_state() -> None:
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)


def main(argv: List[str]) -> int:
    state = load_state()

    if "--reset" in argv:
        reset_state()
        print("Step state reset.")
        return 0

    if "--complete" in argv:
        try:
            idx = argv.index("--complete")
            step_num = int(argv[idx + 1])
        except Exception:
            print("Usage: interrupt_stepper.py --complete <N>", file=sys.stderr)
            return 2
        complete_step(state, step_num)
        print(f"Marked step {step_num} complete.")
        print_status(load_state())
        return 0

    print_status(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
