#!/usr/bin/env python3
"""Keep callable host functions separate from functions in a target image."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from analyze import Graph, reader_context, reader_value


def payload(mode='NATIVE', value=None, reader=700, package='KEYWORD'):
    nodes = [{'id': 1, 'kind': 'symbol', 'name': mode, 'package': package},
             {'id': 2, 'kind': 'function', 'code': reader},
             {'id': 3, 'kind': 'function', 'code': 900}]
    refs = [{'string': 'fixture.dx64fsl'}, {'integer': 3}, {'integer': 80}]
    if value is not None: refs.append({'ref': 3} if value == 'host' else {'integer': value})
    refs.extend([{'ref': 1}, {'ref': 2}])
    for i, ref in enumerate(refs):
        nodes.append({'id': 100 + i, 'kind': 'cons', 'expanded': True, 'car': ref,
                      'cdr': {'ref': 101 + i} if i + 1 < len(refs) else {'atom': 'nil'}})
    return {'root': {'ref': 100}, 'objects': nodes}


def test(regression=None):
    host = payload(value='host'); image = payload('CROSS-DUMP', 0x100f)
    assert reader_value(Graph(host), reader_context(payload(), host)) == {'function': 900}
    assert reader_value(Graph(image), reader_context(payload('CROSS-DUMP'), image)) == {'image_word': 0x100f}
    outcomes = []
    def reject(name, action):
        try: action()
        except ValueError as exc: outcomes.append({'name': name, 'status': 'REJECTED', 'reason': str(exc)})
        else: raise ValueError('reader control escaped: ' + name)
    reject('host-reader-returned-image-word', lambda: reader_value(Graph(image), {'reader_mode': 'native'}))
    reject('image-reader-returned-host-function', lambda: reader_value(Graph(host), {'reader_mode': 'cross-dump'}))
    reject('wrong-function-tag', lambda: reader_value(Graph(payload('CROSS-DUMP', 0x1000)), {'reader_mode': 'cross-dump'}))
    reject('overflow-image-word', lambda: reader_value(Graph(payload('CROSS-DUMP', 2**64 + 15)), {'reader_mode': 'cross-dump'}))
    reject('unknown-dispatch-table', lambda: reader_context(payload('OTHER')))
    reject('false-keyword-identity', lambda: reader_context(payload(package='COMMON-LISP-USER')))
    reject('changed-reader-function', lambda: reader_context(payload(), payload(value='host', reader=701)))
    reject('changed-reader-mode', lambda: reader_context(payload(), image))
    result = {'status': 'PASS', 'positive_cases': 2, 'controls_rejected': len(outcomes), 'outcomes': outcomes}
    if regression:
        row = json.loads(regression.read_text()); graph = Graph(row['payload'])
        assert reader_value(graph, {'reader_mode': 'unrecorded'}) == {'image_word': 52913997089791}
        result['original_regression'] = {'path': str(regression), 'sha256': hashlib.sha256(regression.read_bytes()).hexdigest(),
            'sequence': row['sequence'], 'reader_mode': 'unrecorded',
            'scope': 'The original failing return is preserved as an image word; its old payload did not record table identity.'}
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('output', type=Path)
    p.add_argument('--regression', type=Path); args = p.parse_args()
    result = test(args.regression)
    result['source_sha256'] = {str(x): hashlib.sha256(x.read_bytes()).hexdigest() for x in (Path(__file__), Path(__file__).with_name('analyze.py'))}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'positive_cases', 'controls_rejected')}))
