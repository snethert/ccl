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
STATE_ORDER = ['vsp', 'tsp', 'csp', 'special', 'root_head', 'handler_depth', 'cleanup_count', 'post_exit_effects', 'mv_count', 'transit_count', 'handler_calls', 'max_handler_depth', 'resumed', 'handler_witness_count']
PUSH, CLEAN, POP, EFFECT = 100, 200, 300, 400
LISP_EXIT, CLEANUP_EXIT, UNHANDLED_EXIT, USE_VALUE, DECLINE, LISP_CAUGHT, OTHER_CAUGHT, RESUMED, DBG_IN, DBG_OUT, ADAPTER = 50, 52, 53, 61, 62, 63, 64, 70, 80, 81, 90
UNHANDLED_THROUGH = 65   # handler witness code on the handler frame's propagation path; no event
HANDLER_CODES = (LISP_CAUGHT, OTHER_CAUGHT, DBG_IN, DBG_OUT)
HANDLER_FRAME = 1        # the only frame that owns no cleanup record
FRAME_BYTES = ABI['frame_record']['bytes'] + ABI['root_record']['bytes']   # TSP consumed per live frame
RESERVE = ABI['frame_record']['vsp_reserve']; CLEANUP_BYTES = ABI['cleanup_record']['bytes']
CLEANUP_WORDS = ABI['regions']['cleanup_witness']['words']; HANDLER_WORDS = ABI['regions']['handler_witness']['words']


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


def model(events, unhandled):
    """Walk the expected events with the frame model and return the state every
    cleanup and every handler must observe on entry, derived from the region
    bases, the record sizes and the live frames alone: never from the saved
    fields of any record, so a frame that saves a wrong incoming value cannot
    make its own witness pass. A frame inner to a cleanup or handler that has
    no event of its own departed by the exception; it must own no cleanup
    record, since a cleanup record always runs its cleanup and logs it."""
    live = []; cleanups = 0; cleanup_expect = {}; handler_expect = []
    owns = lambda d: d not in ABI['frame_record']['cleanup_free_frames']
    def depart_to(d):
        require(d in live, 'MODEL frame %d live' % d)
        while live[-1] != d:
            gone = live.pop(); require(not owns(gone), 'MODEL departed frame %d owned a cleanup record' % gone)
    def own():
        n = len(live); tsp = ABI['regions']['tsp_base'] - FRAME_BYTES * n
        return dict(special=100 + live[-1], root_head=tsp, tsp=tsp, frame=tsp + ABI['root_record']['bytes'],
                    vsp=RESTORED['vsp'] + RESERVE * n, csp=ABI['regions']['csp_base'] - CLEANUP_BYTES * cleanups)
    def handler(code, index):
        depart_to(HANDLER_FRAME); require(live == [HANDLER_FRAME] and cleanups == 0, 'MODEL handler frame alone at %d' % code)
        s = own(); handler_expect.append(dict(code=code, special=s['special'], root_head=s['root_head'], tsp=s['tsp'], vsp=s['vsp'], csp=s['csp'], handler_depth=1, event_count=index))
    for index, e in enumerate(events):
        if PUSH < e < PUSH + 100:
            live.append(e - PUSH); cleanups += owns(e - PUSH)
        elif CLEAN < e < CLEAN + 100:
            d = e - CLEAN; require(owns(d), 'MODEL cleanup without a record'); depart_to(d); s = own()
            cleanup_expect[d] = dict(s, saved_vsp=s['vsp'] - RESERVE, saved_csp=s['csp'] + CLEANUP_BYTES)
        elif POP < e < POP + 100:
            d = e - POP
            if d == HANDLER_FRAME and unhandled: handler(UNHANDLED_THROUGH, index)
            depart_to(d); live.pop(); cleanups -= owns(d)
        if e in HANDLER_CODES: handler(e, index)
    require(not live and cleanups == 0, 'MODEL frames balanced')
    return cleanup_expect, handler_expect


def check(observed):
    require(isinstance(observed, dict) and isinstance(observed.get('cases'), dict), 'OBSERVED')
    cases = observed['cases']
    require(list(cases) == [c['name'] for c in ABI['cases']], 'CASE inventory')
    for name, expected in EXPECTED.items():
        c = cases[name]
        cleanup_expect, handler_expect = model(expected['events'], UNHANDLED_EXIT in expected['events'])
        expected_state = dict(expected['state'], handler_witness_count=len(handler_expect))
        if 'returned' in expected:
            require('thrown' not in c and c.get('returned') == expected['returned'], 'RESULT ' + name)
        else:
            require('returned' not in c and c.get('thrown') == expected['thrown'], 'RESULT ' + name)
        st = c.get('state') or {}
        for field in STATE_ORDER:
            require(st.get(field) == expected_state[field], 'STATE ' + name + ' ' + field)
        require(c.get('result_region') == expected['mv'], 'VALUES ' + name + ' result-region')
        require(c.get('transit_region') == expected['transit'], 'VALUES ' + name + ' transit')
        require(st.get('event_count') == len(expected['events']) and c.get('events') == expected['events'], 'EVENTS ' + name)
        # Before a handler delivers values, enters the debugger or propagates,
        # only the handler frame is live and it owns no cleanup record.
        handlers = c.get('handler_witness') or []
        require(len(handlers) == len(handler_expect), 'HANDLER ' + name + ' count')
        for w, exp in zip(handlers, handler_expect):
            for word in HANDLER_WORDS:
                require(w.get(word) == exp[word], 'HANDLER ' + name + ' %d %s' % (exp['code'], word))
        # Inside every cleanup the departed inner frames are gone: the cleanup
        # sees its own binding, its own root record as head and TSP, its VSP
        # reserve and its own cleanup record, on ordinary and exceptional paths.
        witnessed = c.get('cleanup_witness') or {}
        require(sorted(int(d) for d in witnessed) == sorted(cleanup_expect), 'CLEANUP ' + name + ' witnessed frames')
        for depth in sorted(cleanup_expect):
            w = witnessed[str(depth)]
            for word in CLEANUP_WORDS:
                require(w.get(word) == cleanup_expect[depth][word], 'CLEANUP ' + name + ' depth %d %s' % (depth, word))
    return {'cases': len(EXPECTED), 'cleanup_frames_max': 9, 'values_max': 6, 'restored_fields': list(RESTORED), 'cleanup_witness_fields': CLEANUP_WORDS, 'handler_witness_fields': HANDLER_WORDS,
            'handler_witnesses': sum(len(model(e['events'], UNHANDLED_EXIT in e['events'])[1]) for e in EXPECTED.values())}
