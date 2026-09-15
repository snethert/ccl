"""Independent expectations for S0-LL19-a nested exception transfer.

check() raises ValueError naming the first failing check, or returns a
summary. Expected results, states, values and event orders are derived here
from the fixture interface, not copied from any engine output.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ABI = json.loads((HERE / 'abi.json').read_text())
V = ABI['transit_values']; D = ABI['debugger_transit_values']
NIL = ABI['self']
RESTORED = {'vsp': ABI['regions']['vsp_base'] + 8, 'tsp': ABI['regions']['tsp_base'], 'csp': ABI['regions']['csp_base'], 'special': ABI['initial_special'], 'root_head': 0, 'handler_depth': 0}
STATE_ORDER = ['vsp', 'tsp', 'csp', 'special', 'root_head', 'handler_depth', 'cleanup_count', 'post_exit_effects', 'mv_count', 'transit_count', 'handler_calls', 'max_handler_depth', 'resumed']
PUSH, CLEAN, POP, EFFECT = 100, 200, 300, 400
LISP_EXIT, CLEANUP_EXIT, UNHANDLED_EXIT, USE_VALUE, DECLINE, LISP_CAUGHT, OTHER_CAUGHT, RESUMED, DBG_IN, DBG_OUT, ADAPTER = 50, 52, 53, 61, 62, 63, 64, 70, 80, 81, 90


def pad(values):
    return list(values) + [0] * (6 - len(values))


def state(cleanup, post, mv_count, transit_count, handler_calls=0, max_depth=1, resumed=0):
    return {**RESTORED, 'cleanup_count': cleanup, 'post_exit_effects': post, 'mv_count': mv_count, 'transit_count': transit_count,
            'handler_calls': handler_calls, 'max_handler_depth': max_depth, 'resumed': resumed}


NORMAL_TAIL = [EFFECT + 4, POP + 4, EFFECT + 3, CLEAN + 3, POP + 3, EFFECT + 2, CLEAN + 2, POP + 2, POP + 1]
EXIT_TAIL = [LISP_EXIT, CLEAN + 3, POP + 3, CLEAN + 2, POP + 2, LISP_CAUGHT, POP + 1]
ENTER = [PUSH + 1, PUSH + 2, PUSH + 3, PUSH + 4]
EXPECTED = {
    'normal': dict(returned=[18, 2], state=state(2, 3, 2, 0), mv=pad([18, 110]), transit=pad([]), events=ENTER + NORMAL_TAIL),
    'exit-0-values': dict(returned=[NIL, 0], state=state(2, 0, 0, 0), mv=pad([]), transit=pad([]), events=ENTER + EXIT_TAIL),
    'exit-1-value': dict(returned=[V[0], 1], state=state(2, 0, 1, 1), mv=pad(V[:1]), transit=pad(V[:1]), events=ENTER + EXIT_TAIL),
    'exit-6-values': dict(returned=[V[0], 6], state=state(2, 0, 6, 6), mv=V, transit=V, events=ENTER + EXIT_TAIL),
    'cleanup-throws-again': dict(returned=[9, 1], state=state(2, 0, 1, 6), mv=pad([9]), transit=V,
                                 events=ENTER + [LISP_EXIT, CLEAN + 3, POP + 3, CLEANUP_EXIT, CLEAN + 2, POP + 2, OTHER_CAUGHT, POP + 1]),
    'missing-handler': dict(thrown={'error': 'Exception', 'wasm_exception': True, 'tag': 'unhandled', 'arg': 77}, state=state(2, 0, 0, 0), mv=pad([]), transit=pad([]),
                            events=ENTER + [UNHANDLED_EXIT, CLEAN + 3, POP + 3, CLEAN + 2, POP + 2, POP + 1, ADAPTER]),
    'recoverable-use-value': dict(returned=[24, 2], state=state(2, 3, 2, 0, handler_calls=1, resumed=1), mv=pad([24, 112]), transit=pad([]),
                                  events=ENTER + [USE_VALUE, RESUMED] + NORMAL_TAIL),
    'nested-debugger': dict(returned=[V[0], 6], state=state(3, 0, 6, 3, max_depth=2), mv=V, transit=D + V[3:],
                            events=ENTER + [LISP_EXIT, CLEAN + 3, POP + 3, CLEAN + 2, POP + 2, LISP_CAUGHT, DBG_IN, PUSH + 9, LISP_EXIT, CLEAN + 9, POP + 9, DBG_OUT, POP + 1]),
    'deep-chain': dict(returned=[V[0], 6], state=state(9, 0, 6, 6), mv=V, transit=V,
                       events=[PUSH + 1, PUSH + 2] + [PUSH + d for d in range(5, 13)] + [LISP_EXIT] + [e for d in range(12, 4, -1) for e in (CLEAN + d, POP + d)] + [CLEAN + 2, POP + 2, LISP_CAUGHT, POP + 1]),
    'recoverable-declined': dict(returned=[V[0], 1], state=state(2, 0, 1, 1, handler_calls=1), mv=pad(V[:1]), transit=pad(V[:1]),
                                 events=ENTER + [DECLINE] + EXIT_TAIL),
}


def require(condition, name):
    if not condition:
        raise ValueError(name)


def check(observed):
    require(isinstance(observed, dict) and isinstance(observed.get('cases'), dict), 'OBSERVED')
    cases = observed['cases']
    require(list(cases) == [c['name'] for c in ABI['cases']], 'CASE inventory')
    for name, expected in EXPECTED.items():
        c = cases[name]
        if 'returned' in expected:
            require('thrown' not in c and c.get('returned') == expected['returned'], 'RESULT ' + name)
        else:
            require('returned' not in c and c.get('thrown') == expected['thrown'], 'RESULT ' + name)
        st = c.get('state') or {}
        for field in STATE_ORDER:
            require(st.get(field) == expected['state'][field], 'STATE ' + name + ' ' + field)
        require(c.get('result_region') == expected['mv'], 'VALUES ' + name + ' result-region')
        require(c.get('transit_region') == expected['transit'], 'VALUES ' + name + ' transit')
        require(st.get('event_count') == len(expected['events']) and c.get('events') == expected['events'], 'EVENTS ' + name)
    return {'cases': len(EXPECTED), 'cleanup_frames_max': 9, 'values_max': 6, 'restored_fields': list(RESTORED)}
