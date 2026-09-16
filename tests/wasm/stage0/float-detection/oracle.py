"""Compare observed checked-operation statuses and results with the corpus expectations."""


def require(condition, name):
    if not condition:
        raise ValueError(name)


def check(corpus, observed):
    results = {r['id']: r for r in observed['results']}
    require(list(results) == [c['id'] for c in corpus['cases']], 'CASE inventory')
    counts = {}
    for c in corpus['cases']:
        r = results[c['id']]
        require(r['error'] is None, 'TRAP ' + c['id'] + ' ' + str(r['error']))
        require(r['status'] == c['status'], 'STATUS ' + c['id'] + ' expected %d observed %s' % (c['status'], r['status']))
        if c['op'] == 'trunc':
            if c['status'] == 0:
                require(r['integer'] == c['integer'], 'INTEGER ' + c['id'])
            elif c['status'] == 6:
                require(r['result'] == c['result'], 'RESULT ' + c['id'])
        elif c['op'] == 'compare':
            require(r['ordered'] == c['ordered'], 'ORDERED ' + c['id'])
        elif c['op'] == 'policy':
            require(r['mask'] == c['mask'], 'MASK ' + c['id'])
        elif c['result'] is None:
            require(r['nan'], 'RESULT ' + c['id'] + ' expected NaN')
        else:
            require(r['result'] == c['result'], 'RESULT ' + c['id'] + ' expected %s observed %s' % (c['result'], r['result']))
        counts[c['status']] = counts.get(c['status'], 0) + 1
    return dict(cases=len(corpus['cases']), by_status={str(k): v for k, v in sorted(counts.items())})
