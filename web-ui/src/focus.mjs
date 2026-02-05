export const FOCUS_REASONS = {
  COMMAND: "command",
  USER: "user",
  PROGRAM: "program",
  RESTORE: "restore"
};

export function setFocus(state, target, reason = FOCUS_REASONS.COMMAND, seq = null) {
  const entry = {
    seq: seq ?? state.focusHistory.length + 1,
    target,
    reason
  };
  return {
    ...state,
    focus: target,
    focusHistory: [...state.focusHistory, entry]
  };
}

export function focusHistory(state) {
  return state.focusHistory;
}
