import json,sys
sys.setrecursionlimit(max(30000,sys.getrecursionlimit()))
# Explicit small AST also drives an independent logical evaluator. Source is
# rendered normally and the native oracle compiles it independently.
FORMS={}
for n in (0,1,2,3,4,5,6,16,32,64):
 vs=[f'a{i}' for i in range(n)];FORMS[f'v{n}']=(vs,['values',*vs]);FORMS[f'call{n}']=(vs,[f'v{n}',*vs])
FORMS.update({
 'nested':(['a','b'],['v2',['v1','a'],['v1','b']]),
 'scalar_zero':([],['values',['v0'],['v1',7],['v6',1,2,3,4,5,6]]),
 'side_order':(['p'],['v2',['progn',['rplaca','p',1],['car','p']],['progn',['rplaca','p',2],['car','p']]]),
 'mutate':(['p','v'],['values',['rplaca','p','v'],['car','p'],['cdr','p']]),
 'mutation_call':(['p'],['mutate','p',['progn',['rplacd','p',99],['v1',42]]]),
 'keep_many':(['p'],['multiple-value-prog1',['v6',1,2,3,4,5,6],['rplaca','p',17],['v2',91,92]]),
 'keep_zero':(['p'],['multiple-value-prog1',['v0'],['rplaca','p',17],['v2',91,92]]),
 'keep_one':(['p'],['prog1',['v6',1,2,3,4,5,6],['rplaca','p',17],['v0']]),
 'choose':(['p','a','b'],['if','p',['v2','a','b'],['v0']]),
 'dynamic2':(['f','a','b'],['funcall','f','a','b']),
 'dynamic0':(['f'],['funcall','f']),
 'nested_fail':(['p','f'],['v2',['progn',['rplaca','p',10],['car','p']],['funcall','f']]),
 'advance':(['p'],['v1',['rplaca','p',['cdr',['car','p']]]]),
 'type_fail':(['p'],['v1',['car',['v1','p']]]),
})
# Optional and keyword defaults are ordinary source forms, including calls.
FORMS.update({
 'opt':(['a','&optional',['b','a','bp'],['c','b','cp']],['values','a','b','bp','c','cp']),
 'opt_nil':(['&optional','a',['b',['v0'],'bp']],['values','a','b','bp']),
 'opt_effect':(['p','&optional',['a',['progn',['rplaca','p',11],['v2',7,8]],'ap'],['b',['progn',['rplacd','p',22],['v1','a']],'bp']],['values','a','ap','b','bp',['car','p'],['cdr','p']]),
 'opt_failure':(['p','f','&optional',['a',['progn',['rplaca','p',11],['funcall','f']]]],['values','a',['car','p']]),
 'opt_forward':(['p','&optional',['a',['v1',31]]],['opt','p','a']),
 'key':(['&key',['a',1,'ap'],['b','a','bp']],['values','a','ap','b','bp']),
 'key_alias':(['r','&key',[[":external",'a'],['v1','r'],'ap'],['b','ap','bp']],['values','r','a','ap','b','bp']),
 'key_effect':(['p','&key',['a',['progn',['rplaca','p',13],['v2',17,19]],'ap'],['b',['progn',['rplacd','p',23],['v1','a']],'bp']],['values','a','ap','b','bp',['car','p'],['cdr','p']]),
 'key_failure':(['p','f','&key',['a',['progn',['rplaca','p',11],['funcall','f']]]],['values','a',['car','p']]),
 'key_allow':(['&key',['a',1,'ap'],'&allow-other-keys'],['values','a','ap']),
 'key_empty':(['&key'],['values',7]),
 'key_empty_allow':(['&key','&allow-other-keys'],['values',9]),
 'key_bind_allow':(['&key',['allow-other-keys','nil','sp'],['a',1]],['values','allow-other-keys','sp','a']),
 'opt_key':(['r','&optional',['o',['v1','r'],'op'],'&key',['a','o','ap'],['b','ap','bp']],['values','r','o','op','a','ap','b','bp']),
 'key_caller':(['p'],['key_effect','p',':b',['progn',['rplaca','p',41],['v1',37]]]),
 'opt_key_caller':(['p'],['opt_key',':a','p',':b',['v2',43,47],':a',['car','p']]),
 'key_dynamic':(['f','p'],['funcall','f','p',':a',53,':b',59]),
})
FORMS.update({
 'rest_all':(['&rest','r'],'r'),
 'rest_parts':(['a','&optional',['b',9,'bp'],'&rest','r'],['values','a','b','bp','r']),
 'rest_key':(['&rest','r','&key',['a',3,'ap'],['b','a']],['values','r','a','ap','b']),
 'rest_default':(['p','&optional',['a',['rest_all',7,9]],'&rest','r'],['values','a','r',['car','p']]),
 'rest_copies':(['p'],['values',['rest_all',1,'p'],['rest_all',1,'p']]),
 'rest_escape':(['p'],['rplaca','p',['rest_all',11,13,17]]),
 'rest_mutate':(['&rest','r'],['values',['rplaca','r',71],'r']),
 'rest_key_fail':(['p','f','&rest','r','&key',['a',['progn',['rplaca','p','r'],['funcall','f']]]],['values','a','r']),
 'apply0':(['f','xs'],['apply','f','xs']),
 'apply2':(['f','a','b','xs'],['apply','f','a','b','xs']),
 'apply_effect':(['p','f','xs'],['apply',['progn',['rplaca','p',1],'f'],['progn',['rplaca','p',2],['car','p']],['progn',['rplacd','p',3],'xs']]),
 'apply_rest':(['f','&rest','r'],['apply','f','r']),
 'apply_nested':(['f','xs'],['values',['apply','f','xs'],['apply','f','xs']]),
 'apply_keep':(['f','xs'],['multiple-value-prog1',['apply','f','xs'],['v6',1,2,3,4,5,6]]),
 'apply_nil':(['f','a','b'],['apply','f','a','b','nil']),
 'apply_built_list':(['f','p'],['apply','f',['rest_all','p',37]]),
 'apply_type_fail':(['f','xs'],['car',['apply','f','xs']]),
 'call_long':([],['rest_all',*range(129)]),
 'required_long':([f'p{i}' for i in range(129)],['values','p0','p64','p128']),
 'call_required_long':([],['required_long',*range(129)]),
})
# Capacities are runtime inputs, independent of the number of source VALUES.
for n in (65,128,129,257,512,1024):
 vs=[f'a{i}' for i in range(n)];FORMS[f'v{n}']=(vs,['values',*vs])
 if n<=512:FORMS[f'call{n}']=(vs,[f'v{n}',*vs])
FORMS.update({
 'many':(['p'],['values',*(['p','nil','t',-536870912,536870911]*26)]),
 'keep_large':(['p'],['multiple-value-prog1',['many','p'],['v64',*range(64)],['rplaca','p',91],['many',7]]),
 'keep_large_nested':(['p'],['multiple-value-prog1',['keep_large','p'],['keep_large','p']]),
 'many_optional':(['p','&optional',['a',['many','p'],'ap']],['values',*(['a','ap','p']*43)]),
 'many_keyword':(['p','&key',['a',['many','p'],'ap']],['values',*(['a','ap','p']*43)]),
 'many_failure':(['p','f'],['multiple-value-prog1',['many','p'],['rplaca','p',71],['funcall','f']]),
 'many_if':(['p','flag'],['if','flag',['many','p'],['v0']]),
 'many_scalar':(['p'],['values',['many','p'],['car',['many','p']]]),
 'large_prog1':(['p'],['prog1',['many','p'],['many',19]]),
 'bound_after_full':(['p','&optional',['a',17]],['progn',['v128',*(['p']*128)],['values','a','p']]),
 'bound_after_many':(['p','&optional',['a',17]],['progn',['many','p'],['values','a','p']]),
 'discard_values':([],['progn',['values',*range(129)],7]),
 'large_effects':(['p'],['values',*([['rplaca','p',i] for i in range(129)])]),
})
FORMS.update({
 'alternate':(['x'],['values','x',99]),
 'dynamic_one':(['f','x'],['funcall','f','x']),
 'function_value':([],['function','v1']),
 'quoted_value':([],['quote','v1']),
 'quoted_call':(['x'],['funcall',['quote','v1'],'x']),
 'function_call':(['x'],['funcall',['function','v1'],'x']),
 'quoted_apply':(['xs'],['apply',['quote','v2'],'xs']),
 'function_apply':(['xs'],['apply',['function','v2'],'xs']),
 'walk_list':(['p'],['if','p',['walk_list',['cdr','p']],['values',71,73]]),
 'mutual_a':(['p'],['if','p',['mutual_b',['cdr','p']],['values',11,13]]),
 'mutual_b':(['p'],['if','p',['mutual_a',['cdr','p']],['values',17,19]]),
 'recursive_keep':(['p'],['if','p',['multiple-value-prog1',['v2',['car','p'],'p'],['recursive_keep',['cdr','p']]],['v0']]),
 'self_named':(['x'],['values',['function','self_named'],'x']),
})
# Factory calls return before their closures are invoked. All mutation is through
# source SETQ; no host-created environment is supplied to generated code.
FORMS.update({
 'factory':(['x'],['lambda',[], 'x']),
 'setter_factory':(['x'],['lambda',['v'],['setq','x','v']]),
 'cell_factory':(['x'],['lambda',['&optional',['v','nil','vp']],['if','vp',['setq','x','v'],'x']]),
 'pair_factory':(['x','p'],['progn',['rplaca','p',['lambda',[],'x']],['rplacd','p',['lambda',['v'],['setq','x','v']]],'p']),
 'nested_factory':(['x'],['lambda',[],['lambda',[],'x']]),
 'empty_factory':([],['lambda',[],17]),
 'closure_call':(['x'],['funcall',['factory','x']]),
 'closure_set':(['x','v'],['let',[['f',['cell_factory','x']]],['values',['funcall','f'],['funcall','f','v'],['funcall','f']]]),
 'closure_siblings':(['x','v','p'],['progn',['pair_factory','x','p'],['values',['funcall',['car','p']],['funcall',['cdr','p'],'v'],['funcall',['car','p']]]]),
 'closure_distinct':(['x','v'],['let',[['a',['cell_factory','x']],['b',['cell_factory','v']]],['values',['funcall','a',71],['funcall','a'],['funcall','b']]]),
 'closure_nested':(['x'],['funcall',['funcall',['nested_factory','x']]]),
 'closure_empty':([],['funcall',['empty_factory']]),
 'closure_shadow':(['x'],['let',[['f',['lambda',[],'x']]],['let',[['x',37]],['values','x',['funcall','f']]]]),
 'closure_parallel':(['x'],['let',[['x',31],['y',['lambda',[],'x']]],['values','x',['funcall','y']]]),
 'closure_sequential':(['x'],['let*',[['x',31],['y',['lambda',[],'x']]],['progn',['setq','x',43],['funcall','y']]]),
 'closure_parent_write':(['x'],['let',[['f',['lambda',[],'x']]],['progn',['setq','x',53],['funcall','f']]]),
 'closure_local_write':(['x'],['let',[['y','x']],['let',[['f',['lambda',[],'y']]],['progn',['setq','y',59],['funcall','f']]]]),
 'closure_default':(['x','&optional',['f',['lambda',[],'x']]],['progn',['setq','x',61],['funcall','f']]),
 'closure_optional_factory':(['&optional',['x',7,'xp']],['lambda',[],['values','x','xp']]),
 'closure_optional':([],['values',['funcall',['closure_optional_factory']],['funcall',['closure_optional_factory',19]]]),
 'closure_key_factory':(['&key',['x',11,'xp']],['lambda',[],['values','x','xp']]),
 'closure_key':([],['funcall',['closure_key_factory',':x',29]]),
 'closure_rest_factory':(['&rest','r'],['lambda',[],'r']),
 'closure_rest':([],['funcall',['closure_rest_factory',7,11,13]]),
 'closure_apply':(['x','xs'],['apply',['cell_factory','x'],'xs']),
 'closure_keep':(['x','v'],['let',[['f',['cell_factory','x']]],['multiple-value-prog1',['values',['funcall','f'],'f'],['funcall','f','v']]]),
 'closure_fail_escape':(['p','x','f'],['let',[['g',['cell_factory','x']]],['progn',['rplaca','p','g'],['funcall','f']]]),
 'closure_multiset':(['x','y'],['progn',['setq','x','y','y',17],['values','x','y']]),
 'closure_many_captures':(['x','y','z'],['let',[['f',['lambda',[],['values','x','y','z']]]],['funcall','f']]),
 'closure_nested_mutate':(['x','v'],['let',[['outer',['lambda',[],['lambda',['v'],['setq','x','v']]]]],['let',[['inner',['funcall','outer']]],['values',['funcall','inner','v'],'x']]]),
 'closure_same':(['x'],['let',[['f',['factory','x']]],['values','f','f']]),
})
FORMS.update({
 'closure_capture_closure':(['x'],['funcall',['funcall',['factory',['factory','x']]]]),
 'closure_function_syntax':(['x'],['let',[['f',['function',['lambda',[],'x']]]],['funcall','f']]),
 'closure_optional_empty':([],['funcall',['closure_optional_factory']]),
 'closure_optional_full':([],['funcall',['closure_optional_factory',23]]),
 'closure_key_empty':([],['funcall',['closure_key_factory']]),
 'closure_bad_default':(['x','f','&optional',['v',['funcall','f']]],['lambda',[],'x']),
 'closure_default_capture':(['x','&optional',['f',['lambda',[],'x']],['v',['funcall','f']]],['values','v',['funcall','f']]),
 'closure_three_levels':(['x'],['let',[['f',['lambda',[],['lambda',[],['lambda',[],'x']]]]],['funcall',['funcall',['funcall','f']]]]),
 'closure_let_order':(['p'],['let',[['a',['progn',['rplaca','p',17],['car','p']]],['b',['progn',['rplacd','p',19],['car','p']]]],['let',[['f',['lambda',[],['values','a','b',['car','p'],['cdr','p']]]]],['funcall','f']]]),
})
wide=[f'c{i}' for i in range(129)]
FORMS['closure_wide']=(wide,['let',[['f',['lambda',[],['values',*wide]]]],['funcall','f']])
FORMS.update({
 'local_flet':(['x'],['flet',[['f',['y'],['values','x','y']]],['f',7]]),
 'local_flet_escape':(['x'],['flet',[['f',['y'],['setq','x','y']]],['function','f']]),
 'local_flet_use':(['x','y'],['let',[['f',['local_flet_escape','x']]],['funcall','f','y']]),
 'local_flet_siblings':(['x','p'],['flet',[['get',[],'x'],['put',['v'],['setq','x','v']]],['progn',['rplaca','p',['function','get']],['rplacd','p',['function','put']],['values',['get'],['put',31],['get']]]]),
 'local_labels':(['x','xs'],['labels',[['f',['p'],['if','p',['f',['cdr','p']],'x']]],['f','xs']]),
 'local_mutual':(['x','xs'],['labels',[['f',['p'],['if','p',['g',['cdr','p']],['values','x',11]]],['g',['p'],['if','p',['f',['cdr','p']],['values','x',13]]]],['f','xs']]),
 'local_mutual_factory':(['x'],['labels',[['f',['p'],['if','p',['g',['cdr','p']],'x']],['g',['p'],['if','p',['f',['cdr','p']],'x']]],['function','f']]),
 'local_mutual_escape':(['x','xs'],['funcall',['local_mutual_factory','x'],'xs']),
 'local_self_identity':(['x'],['labels',[['f',[],['values','x',['function','f']]]],['values',['function','f'],['funcall',['function','f']]]]),
 'local_lexical_shadow':(['x'],['flet',[['v1',['p'],['values','x','p']]],['values',['v1',17],['funcall',['quote','v1'],19],['funcall',['function','v1'],23]]]),
 'local_flet_outer':(['x'],['flet',[['f',[],'x']],['flet',[['f',[],['f']]],['f']]]),
 'local_transitive':(['x'],['flet',[['f',[],'x']],['lambda',[],['lambda',[],['f']]]]),
 'local_transitive_use':(['x'],['funcall',['funcall',['local_transitive','x']]]),
 'local_inline':(['x'],['funcall',['lambda',['y','&optional',['z','y','zp']],['values','x','y','z','zp']],7]),
 'local_inline_full':(['x'],['funcall',['lambda',['y','&optional',['z','y','zp']],['values','x','y','z','zp']],7,11]),
 'local_inline_rest':(['x'],['funcall',['lambda',['&rest','r'],['values','x','r']],7,11]),
 'local_inline_rest_empty':(['x'],['funcall',['lambda',['&rest','r'],['values','x','r']]]),
 'local_inline_order':(['p'],['funcall',['lambda',['x','y'],['values','x','y',['car','p'],['cdr','p']]],['progn',['rplaca','p',17],['car','p']],['progn',['rplacd','p',19],['cdr','p']]]),
 'local_inline_escape':(['x'],['funcall',['lambda',['y'],['lambda',[],['values','x','y']]],17]),
 'local_inline_escape_use':(['x'],['funcall',['local_inline_escape','x']]),
 'local_apply_literal':(['x','xs'],['apply',['lambda',['y'],['values','x','y']],'xs']),
 'local_apply_function_literal':(['x','xs'],['apply',['function',['lambda',['y'],['values','x','y']]],'xs']),
 'local_direct_lambda':(['x'],[['lambda',['y'],['values','x','y']],23]),
 'local_key':(['x'],['flet',[['f',['&key',['y','x','yp']],['values','x','y','yp']]],['f',':y',29]]),
 'local_optional_recursive':(['x','xs'],['labels',[['f',['p','&optional',['v','x']],['if','p',['f',['cdr','p'],'v'],['values','v','x']]]],['f','xs']]),
 'local_apply_self':(['x','xs'],['labels',[['f',['p','&rest','rest'],['if','p',['apply',['function','f'],['cdr','p'],'rest'],['values','x','rest']]]],['f','xs',7,11]]),
})
FORMS.update({
 'local_labels_defaults':(['x'],['labels',[['f',['a','&optional',['b',['g','a']]],['values','x','a','b']],['g',['a'],['values','a','x']]],['f',29]]),
 'local_labels_pair_factory':(['x','p'],['labels',[['get',[],'x'],['put',['v'],['setq','x','v']],['relay',['v'],['put','v']]],['progn',['rplaca','p',['function','get']],['rplacd','p',['function','relay']],'p']]),
 'local_labels_pair_use':(['x','p'],['progn',['local_labels_pair_factory','x','p'],['values',['funcall',['car','p']],['funcall',['cdr','p'],41],['funcall',['car','p']]]]),
 'local_inline_defaults':(['x'],['funcall',['lambda',['a','&optional',['b','a','bp'],['c','b','cp']],['values','a','b','bp','c','cp']],'x']),
 'local_inline_long':(['x'],['funcall',['lambda',['&rest','r'],['values','x','r']],*range(129)]),
 'local_literal_apply_order':(['p'],['apply',['lambda',['x'],['values',['car','p'],['cdr','p'],'x']],['progn',['rplaca','p',17],['car','p']],['progn',['rplacd','p',19],'nil']]),
 'local_apply_variable':(['x'],['let',[['apply',['lambda',['y'],['values','x','y']]]],['funcall','apply',17]]),
 'local_apply_parameter':(['x','&optional',['apply',['lambda',['y'],['values','x','y']]]],['funcall','apply',19]),
})
FORMS.update({'tail_apply_nocapture': (['xs'], ['apply', ['lambda', ['y'], ['values', 'y', 29]], 'xs']),
 'tail_apply_tail_out': (['xs'], ['apply', ['lambda', ['y'], ['v1', 'y']], 'xs']),
 'tail_apply_non_tail': (['x', 'xs'],
                         ['values', ['apply', ['lambda', ['y'], ['values', 'x', 'y']], 'xs'], 'x']),
 'tail_apply_escape': (['x', 'xs'], ['apply', ['lambda', ['y'], ['lambda', [], ['values', 'x', 'y']]], 'xs']),
 'tail_apply_escape_use': (['x', 'xs'], ['funcall', ['tail_apply_escape', 'x', 'xs']]),
 'tail_apply_mutate': (['x', 'xs'],
                       ['apply',
                        ['lambda', ['y'], ['values', 'x', 'y']],
                        ['progn', ['setq', 'x', 33], 'xs']]),
 'tail_apply_nested': (['xs', 'ys'],
                       ['apply',
                        ['lambda', ['a'], ['apply', ['lambda', ['b'], ['values', 'a', 'b']], 'xs']],
                        'ys']),
 'tail_apply_key': (['x', 'xs'],
                    ['apply', ['lambda', ['&key', ['y', ['v1', 'x']]], ['values', 'x', 'y']], 'xs']),
 'tail_apply_loop': (['p'],
                     ['if',
                      'p',
                      ['apply', ['function', 'tail_apply_loop'], ['cdr', 'p'], 'nil'],
                      ['values', 71, 73]]),
 'tail_local_apply_loop': (['x', 'xs'],
                           ['labels',
                            [['f',
                              ['p'],
                              ['if',
                               'p',
                               ['apply', ['function', 'f'], ['cdr', 'p'], 'nil'],
                               ['values', 'x', 73]]]],
                            ['f', 'xs']]),
 'tail_indirect': (['f', 'p'], ['if', 'p', ['funcall', 'f', 'f', ['cdr', 'p']], ['values', 71, 73]]),
 'tail_vary_a': (['p'], ['if', 'p', ['tail_vary_b', ['cdr', 'p'], 11, 13], ['values', 71, 73]]),
 'tail_vary_b': (['p', 'x', 'y'], ['if', 'p', ['tail_vary_a', ['cdr', 'p']], ['values', 'x', 'y']]),
 'tail_failure': (['p', 'bad'], ['if', 'p', ['tail_failure', ['cdr', 'p'], 'bad'], ['car', 'bad']]),
 'non_tail_effect': (['p', 'target'],
                     ['if',
                      'p',
                      ['multiple-value-prog1',
                       ['non_tail_effect', ['cdr', 'p'], 'target'],
                       ['rplaca', 'target', ['car', 'p']]],
                      ['values', 71, 73]])})
FORMS.update({'tail_wide_a': (['p'],
                 ['if',
                  'p',
                  ['tail_wide_b',
                   ['cdr', 'p'],
                   0,
                   1,
                   2,
                   3,
                   4,
                   5,
                   6,
                   7,
                   8,
                   9,
                   10,
                   11,
                   12,
                   13,
                   14,
                   15,
                   16,
                   17,
                   18,
                   19,
                   20,
                   21,
                   22,
                   23,
                   24,
                   25,
                   26,
                   27,
                   28,
                   29,
                   30,
                   31,
                   32,
                   33,
                   34,
                   35,
                   36,
                   37,
                   38,
                   39,
                   40,
                   41,
                   42,
                   43,
                   44,
                   45,
                   46,
                   47,
                   48,
                   49,
                   50,
                   51,
                   52,
                   53,
                   54,
                   55,
                   56,
                   57,
                   58,
                   59,
                   60,
                   61,
                   62,
                   63,
                   64,
                   65,
                   66,
                   67,
                   68,
                   69,
                   70,
                   71,
                   72,
                   73,
                   74,
                   75,
                   76,
                   77,
                   78,
                   79,
                   80,
                   81,
                   82,
                   83,
                   84,
                   85,
                   86,
                   87,
                   88,
                   89,
                   90,
                   91,
                   92,
                   93,
                   94,
                   95,
                   96,
                   97,
                   98,
                   99,
                   100,
                   101,
                   102,
                   103,
                   104,
                   105,
                   106,
                   107,
                   108,
                   109,
                   110,
                   111,
                   112,
                   113,
                   114,
                   115,
                   116,
                   117,
                   118,
                   119,
                   120,
                   121,
                   122,
                   123,
                   124,
                   125,
                   126,
                   127,
                   128],
                  ['values', 71, 73]]),
 'tail_wide_b': (['p',
                  'x0',
                  'x1',
                  'x2',
                  'x3',
                  'x4',
                  'x5',
                  'x6',
                  'x7',
                  'x8',
                  'x9',
                  'x10',
                  'x11',
                  'x12',
                  'x13',
                  'x14',
                  'x15',
                  'x16',
                  'x17',
                  'x18',
                  'x19',
                  'x20',
                  'x21',
                  'x22',
                  'x23',
                  'x24',
                  'x25',
                  'x26',
                  'x27',
                  'x28',
                  'x29',
                  'x30',
                  'x31',
                  'x32',
                  'x33',
                  'x34',
                  'x35',
                  'x36',
                  'x37',
                  'x38',
                  'x39',
                  'x40',
                  'x41',
                  'x42',
                  'x43',
                  'x44',
                  'x45',
                  'x46',
                  'x47',
                  'x48',
                  'x49',
                  'x50',
                  'x51',
                  'x52',
                  'x53',
                  'x54',
                  'x55',
                  'x56',
                  'x57',
                  'x58',
                  'x59',
                  'x60',
                  'x61',
                  'x62',
                  'x63',
                  'x64',
                  'x65',
                  'x66',
                  'x67',
                  'x68',
                  'x69',
                  'x70',
                  'x71',
                  'x72',
                  'x73',
                  'x74',
                  'x75',
                  'x76',
                  'x77',
                  'x78',
                  'x79',
                  'x80',
                  'x81',
                  'x82',
                  'x83',
                  'x84',
                  'x85',
                  'x86',
                  'x87',
                  'x88',
                  'x89',
                  'x90',
                  'x91',
                  'x92',
                  'x93',
                  'x94',
                  'x95',
                  'x96',
                  'x97',
                  'x98',
                  'x99',
                  'x100',
                  'x101',
                  'x102',
                  'x103',
                  'x104',
                  'x105',
                  'x106',
                  'x107',
                  'x108',
                  'x109',
                  'x110',
                  'x111',
                  'x112',
                  'x113',
                  'x114',
                  'x115',
                  'x116',
                  'x117',
                  'x118',
                  'x119',
                  'x120',
                  'x121',
                  'x122',
                  'x123',
                  'x124',
                  'x125',
                  'x126',
                  'x127',
                  'x128'],
                 ['if', 'p', ['tail_wide_a', ['cdr', 'p']], ['values', 'x0', 'x128']]),
 'tail_zero': (['p'], ['if', 'p', ['tail_zero', ['cdr', 'p']], ['values']]),
 'tail_many': (['p'], ['if', 'p', ['tail_many', ['cdr', 'p']], ['many', 7]])})
# The dictionaries are ordered with required callees before callers.
def render(x):return '('+' '.join(map(render,x))+')' if isinstance(x,list) else str(x)
def bound_words(vs):
 mode='required';opt=[];keys=[];rest=0
 for v in vs:
  if v=='&optional':mode='optional'
  elif v=='&rest':mode='rest'
  elif mode=='rest':rest=1;mode='after-rest'
  elif v=='&key':mode='key'
  elif v=='&allow-other-keys':pass
  elif mode=='optional':opt.append(v if isinstance(v,list) else [v])
  elif mode=='key':keys.append(v)
 # U1 provides internal optional presence variables when a default is non-NIL
 # or any explicit supplied-p parameter exists; all keys have presence slots.
 hard=any(len(v)>2 or (len(v)>1 and v[1]!='nil') for v in opt)
 return len(opt)*(2 if hard else 1)+2*len(keys)+rest
# Non-tail APPLY must fill the final continuation, including its prefix.
FORMS.update({
 'ordinary_apply_prefix':(['f','xs','p'],['multiple-value-prog1',['apply','f',['progn',['rplaca','p',17],['car','p']],'xs'],['rplacd','p',29]]),
 'ordinary_apply_mixed':(['f','x','xs'],['values',['apply','f','x','xs'],['apply','f',['v1','x'],'xs'],'x']),
 'ordinary_apply_closure':(['x','xs'],['let',[['f',['lambda',['a','b'],['values','x','a','b']]]],['multiple-value-prog1',['apply','f',['v1','x'],'xs'],['setq','x',37]]]),
 'ordinary_literal_apply_prefix':(['x','xs','p'],['multiple-value-prog1',['apply',['lambda',['a','b'],['values','a','b','x']],['car','p'],'xs'],['rplaca','p',37]])
})

def modules():return [dict(name=n,source=render(['lambda',vs,body]),bound_words=bound_words(vs)) for n,(vs,body) in FORMS.items()]
BINDINGS={}
class Condition(Exception):
 def __init__(self,kind):self.kind=kind

class Cell:
 def __init__(self,value):self.value=value
class Environment(dict):
 def get(self,key,default=None):return dict.get(self,key,Cell(default)).value
 def __setitem__(self,key,value):dict.__setitem__(self,key,Cell(value))
 def assign(self,key,value):dict.__getitem__(self,key).value=value
 def update(self,items):
  for k,v in items:self[k]=v
class Closure:
 def __init__(self,parameters,body,env,functions=None):self.parameters=parameters;self.body=body;self.env=env.copy();self.functions=functions if functions is not None else {}

# Real CCL UNWIND-PROTECT IR; no source rewrite or host cleanup emulation.
FORMS.update({
 'uw_cleanup':(['p','v'],['progn',['rplaca','p','v'],['v2',91,93]]),
 'uw_order':(['p'],['unwind-protect',['unwind-protect',['v2',1,2],['rplaca','p',['cdr',['car','p']]]],['rplacd','p',['car','p']],['rplaca','p',['cdr',['car','p']]]]),
 'uw_capacity':(['p'],['unwind-protect',['many','p'],['uw_cleanup','p',211]]),
 'uw_heap':(['p'],['unwind-protect',['rest_all',*range(64)],['uw_cleanup','p',223]]),
 'uw_datum':(['p','x'],['unwind-protect',['car','x'],['uw_cleanup','p',227]]),
 'uw_zero':(['p'],['unwind-protect',['v0'],['uw_cleanup','p',11]]),
 'uw_one':(['p','x'],['unwind-protect',['v1','x'],['uw_cleanup','p',13]]),
 'uw_many':(['p'],['unwind-protect',['many','p'],['many',17],['uw_cleanup','p',19]]),
 'uw_call':(['p','f'],['unwind-protect',['funcall','f'],['uw_cleanup','p',23]]),
 'uw_argument':(['p','f'],['v2',['unwind-protect',['funcall','f'],['uw_cleanup','p',29]],['car','p']]),
 'uw_nested':(['p','f','g'],['unwind-protect',['unwind-protect',['funcall','f'],['rplaca','p',31],['funcall','g']],['rplacd','p',37]]),
 'uw_replace':(['p','f'],['unwind-protect',['car',['v1',7]],['rplaca','p',41],['funcall','f'],['rplacd','p',43]]),
 'uw_replace_outer':(['p','f'],['unwind-protect',['uw_replace','p','f'],['rplacd','p',47]]),
 'uw_cleanup_extent':(['p','f'],['unwind-protect',['car',['v1',7]],['unwind-protect',['funcall','f'],['rplaca','p',53]]]),
 'uw_normal_nested':(['p'],['unwind-protect',['unwind-protect',['v2',59,61],['uw_cleanup','p',67]],['rplacd','p',['car','p']],['uw_cleanup','p',71]]),
 'uw_mutate_result':(['p'],['unwind-protect',['v2','p',['car','p']],['rplaca','p',73]]),
 'uw_capture':(['p','x'],['let',[['v','x']],['unwind-protect',['lambda',[],'v'],['setq','v',79],['rplaca','p','v']]]),
 'uw_rest':(['p','&rest','r'],['unwind-protect',['values','r',['car','r']],['rplacd','p','r'],['rplaca','r',83]]),
 'uw_apply':(['p','f','xs'],['unwind-protect',['apply','f','xs'],['uw_cleanup','p',89]]),
 'uw_literal_apply':(['p','x'],['unwind-protect',['apply',['lambda',['a'],['v2','a',97]],'x','nil'],['uw_cleanup','p',101]]),
 'uw_walk':(['p'],['if','p',['unwind-protect',['uw_walk',['cdr','p']],['rplaca','p',103]],['v2',107,109]]),
 'uw_tail_child':(['p','xs'],['unwind-protect',['walk_list','xs'],['uw_cleanup','p',113]]),
 'uw_no_cleanup':(['p'],['unwind-protect',['v2','p',127]]),
 'uw_default':(['p','&optional',['x',['unwind-protect',['v2',131,137],['uw_cleanup','p',139]]]],['values','x',['car','p']]),
 'uw_key':(['p','&key',['x',['unwind-protect',['v2',149,151],['uw_cleanup','p',157]]]],['values','x',['car','p']]),
 'uw_local':(['p','x'],['labels',[['goer',['x'],['unwind-protect',['v2','x',163],['uw_cleanup','p',167]]]],['goer','x']]),
 'uw_cleanup_fail_first':(['p'],['unwind-protect',['v2',173,179],['rplaca',['v1',7],5],['rplaca','p',181]]),
 'uw_before':(['p','f'],['progn',['rplaca','p',191],['unwind-protect',['funcall','f'],['rplacd','p',193]]]),
})


CATCHES=[]
class Transfer(Exception):
 def __init__(self,target,values):self.target=target;self.values=values
FORMS.update({
 'ct_raw_throw':(['tag','x'],['throw','tag','x']),
 'ct_raw_catch':(['tag','x'],['catch','tag',['ct_raw_throw','tag','x']]),
 'ct_state':(['p','state'],['rplaca','p','state']),
 'ct_state_normal':(['p'],['unwind-protect',['ct_state','p',0],['ct_state','p',0]]),
 'ct_state_exit':(['p'],['catch',7,['unwind-protect',['throw',7,11],['ct_state','p',1]]]),
 'ct_state_error':(['p','f'],['unwind-protect',['funcall','f'],['ct_state','p',2]]),
 'ct_state_nested':(['p'],['catch',7,['unwind-protect',['throw',7,11],['catch',13,['unwind-protect',['throw',13,17],['ct_state','p',1]]],['ct_state','p',1]]]),
 'ct_state_restored':(['p'],['progn',['catch',7,['unwind-protect',['rplaca',['v1',5],1],['ct_state','p',2],['throw',7,19]]],['ct_state','p',0]]),
 'ct_throw':(['tag','x'],['throw','tag',['v2','x',11]]),
 'ct_catch':(['tag','x'],['catch','tag',['ct_throw','tag','x']]),
 'ct_normal':(['tag','x'],['catch','tag',['v2','x',13]]),
 'ct_empty':(['tag'],['catch','tag']),
 'ct_zero':(['tag'],['catch','tag',['throw','tag',['v0']]]),
 'ct_many':(['tag','p'],['catch','tag',['throw','tag',['many','p']]]),
 'ct_dynamic':(['tag','f'],['catch','tag',['funcall','f','tag',17]]),
 'ct_apply':(['tag','f','xs'],['catch','tag',['apply','f','tag','xs']]),
 'ct_nested':(['a','b','x'],['catch','a',['values',['catch','b',['ct_throw','a','x']],23]]),
 'ct_same':(['tag','x'],['catch','tag',['v2',['catch','tag',['ct_throw','tag','x']],29]]),
 'ct_identity':(['a','b'],['catch','a',['throw','b',31]]),
 'ct_tag_effect':(['p','tag'],['catch',['progn',['rplaca','p',37],'tag'],['throw',['progn',['rplacd','p',41],'tag'],['values',['car','p'],['cdr','p']]]]),
 'ct_missing_effect':(['p','tag'],['throw','tag',['progn',['rplaca','p',43],['v2',47,53]]]),
 'ct_cleanup':(['p','tag'],['catch','tag',['unwind-protect',['ct_throw','tag','p'],['uw_cleanup','p',59]]]),
 'ct_cleanup_normal':(['p','tag'],['catch','tag',['unwind-protect',['v2',61,67],['throw','tag',['v2','p',71]]]]),
 'ct_cleanup_rethrow':(['p','tag'],['catch','tag',['v2',['catch','tag',['unwind-protect',['throw','tag',73],['rplaca','p',79],['throw','tag',83]]],89]]),
 'ct_cleanup_override':(['p','a','b'],['catch','a',['v2',['catch','b',['unwind-protect',['throw','b',97],['rplaca','p',101],['throw','a',103]]],107]]),
 'ct_cleanup_handled':(['p','a','b'],['catch','a',['unwind-protect',['throw','a',['v2','p',109]],['catch','b',['throw','b',['v2',113,127]]],['uw_cleanup','p',131]]]),
 'ct_cleanup_error':(['p','tag','f'],['catch','tag',['unwind-protect',['throw','tag',137],['rplaca','p',139],['funcall','f']]]),
 'ct_error_to_throw':(['p','tag'],['catch','tag',['unwind-protect',['rplaca',['v1',7],149],['throw','tag',['v2','p',151]]]]),
 'ct_dead_inner':(['p','a','b'],['catch','a',['unwind-protect',['catch','b',['throw','a',157]],['rplaca','p',163],['throw','b',167]]]),
 'ct_pending_values':(['p','tag'],['multiple-value-prog1',['catch','tag',['throw','tag',['v2','p',173]]],['rplaca','p',179]]),
 'ct_let':(['tag','x'],['let',[['v',['catch','tag',['ct_throw','tag','x']]]],['v2','v',181]]),
 'ct_default':(['tag','&optional',['x',['catch','tag',['throw','tag',191]]]],['v2','x',193]),
 'ct_capture':(['tag','x'],['catch','tag',['funcall',['lambda',[],['throw','tag',['v2','x',197]]]]]),
 'ct_local':(['tag','x'],['labels',[['exit',['x'],['throw','tag',['v2','x',199]]]],['catch','tag',['exit','x']]]),
 'ct_factory':(['tag'],['lambda',['x'],['throw','tag',['v2','x',211]]]),
 'ct_escaped':(['tag','x'],['let',[['f',['ct_factory','tag']]],['catch','tag',['funcall','f','x']]]),
 'ct_retired':(['tag','x'],['let',[['f',['catch','tag',['ct_factory','tag']]]],['funcall','f','x']]),
 'ct_tail':(['tag','xs'],['if','xs',['ct_tail','tag',['cdr','xs']],['throw','tag',['v2',223,227]]]),
 'ct_tail_start':(['tag','xs'],['catch','tag',['ct_tail','tag','xs']]),
 'ct_recursive':(['xs'],['if','xs',['catch',['car','xs'],['v2',['ct_recursive',['cdr','xs']],229]],['v0']]),
 'ct_two_cleanups':(['p','tag'],['catch','tag',['unwind-protect',['unwind-protect',['ct_throw','tag','p'],['rplaca','p',233]],['rplacd','p',['car','p']],['rplaca','p',239]]]),
})

SPECIAL_NAMES=('dyn_a','dyn_b','dyn_u')
SPECIAL_VALUES={}
UNBOUND=object()

def special(body):
 def declarations(x):
  if not isinstance(x,list):return x
  result=[declarations(y) for y in x]
  if x and x[0] in ('let','let*'):
   names=[b[0] if isinstance(b,list) else b for b in x[1]]
   names=[n for n in names if n in SPECIAL_NAMES]
   if names:result.insert(2,['declare',['special',*names]])
  return result
 return ['locally',['declare',['special','dyn_a','dyn_b','dyn_u']],declarations(body)]
FORMS.update({
 'sd_read':([],special(['values','dyn_a','dyn_b'])),
 'sd_read_a':([],special('dyn_a')),
 'sd_read_u':([],special('dyn_u')),
 'sd_set':(['x'],special(['setq','dyn_a','x'])),
 'sd_set_u':(['x'],special(['setq','dyn_u','x'])),
 'sd_bind':(['x'],special(['let',[['dyn_a','x']],['sd_read']])),
 'sd_parallel':(['x'],special(['let',[['dyn_a','x'],['dyn_b','dyn_a']],['sd_read']])),
 'sd_sequential':(['x'],special(['let*',[['dyn_a','x'],['dyn_b','dyn_a']],['sd_read']])),
 'sd_duplicate':(['x'],special(['let*',[['dyn_a','x'],['dyn_a',['v1',107]]],['sd_read']])),
 'sd_local_decl':(['x'],['let',[['dyn_a','x']],['declare',['special','dyn_a']],['sd_read']]),
 'sd_nil':([],special(['let',['dyn_a'],['sd_read']])),
 'sd_nested':(['x','y'],special(['let',[['dyn_a','x']],['values',['sd_bind','y'],'dyn_a']])),
 'sd_assign':(['x','y'],special(['let',[['dyn_a','x']],['progn',['sd_set','y'],['sd_read']]])),
 'sd_after':(['x'],special(['progn',['sd_bind','x'],['sd_read']])),
 'sd_unbound':(['x'],special(['let',[['dyn_u','x']],['sd_read_u']])),
 'sd_unbound_after':(['x'],special(['progn',['sd_unbound','x'],['sd_read_u']])),
 'sd_failure_init':(['p','x'],special(['let*',[['dyn_a','x'],['dyn_b',['progn',['rplaca','p','dyn_a'],['sd_read_u']]]],['sd_read']])),
 'sd_throw':(['tag','x'],special(['let',[['dyn_a','x']],['throw','tag',['sd_read']]])),
 'sd_catch':(['tag','x'],special(['catch','tag',['sd_throw','tag','x']])),
 'sd_cleanup_inside':(['p','tag','x'],special(['let',[['dyn_a','x']],['unwind-protect',['throw','tag',['sd_read']],['rplaca','p',['sd_read_a']]]])),
 'sd_cleanup_outside':(['p','tag','x'],special(['unwind-protect',['sd_throw','tag','x'],['rplaca','p',['sd_read_a']]])),
 'sd_clean_catch':(['p','tag','x'],special(['catch','tag',['sd_cleanup_inside','p','tag','x']])),
 'sd_outer_catch':(['p','tag','x'],special(['catch','tag',['sd_cleanup_outside','p','tag','x']])),
 'sd_replace':(['p','tag','x'],special(['catch','tag',['unwind-protect',['sd_throw','tag','x'],['throw','tag',['sd_read']]]])),
 'sd_error_cleanup':(['p','x'],special(['unwind-protect',['let',[['dyn_a','x']],['rplaca',['v1',7],1]],['rplaca','p',['sd_read_a']]])),
 'sd_closure':(['x'],special(['let',[['dyn_a','x']],['lambda',[],['sd_read_a']]])),
 'sd_escape':(['x'],['funcall',['sd_closure','x']]),
 'sd_closure_bound':(['x','y'],special(['let',[['dyn_a','y']],['funcall',['sd_closure','x']]])),
 'sd_local':(['x'],special(['flet',[['readit',[],['sd_read']]],['let',[['dyn_a','x']],['readit']]])),
 'sd_apply':(['x','xs'],special(['let',[['dyn_a','x']],['apply',['function','sd_read'],'xs']])),
 'sd_default':(['x','&optional',['y',['sd_bind','x']]],special(['values','y','dyn_a'])),
 'sd_values':(['x'],special(['let',[['dyn_a','x']],['many','dyn_a']])),
 'sd_zero':(['x'],special(['let',[['dyn_a','x']],['v0']])),
 'sd_recursive':(['xs'],special(['if','xs',['let',[['dyn_a',['car','xs']]],['sd_recursive',['cdr','xs']]],['sd_read']])),
 'sd_tail_child':(['x','xs'],special(['let',[['dyn_a','x']],['walk_list','xs']])),
 'sd_global_after':(['x'],special(['progn',['sd_set','x'],['sd_bind',109],['sd_read']])),
 'sd_declaration_shadow':(['x'],['locally',['declare',['special','dyn_a']],['let',[['dyn_a','x']],['values','dyn_a',['sd_read_a']]]]),
 'sd_lexical_shadow':(['x'],['let',[['dyn_a','x']],['values','dyn_a',special(['sd_read_a'])]]),
})

def evaluate(name,inputs,nodes):
 if isinstance(name,Closure):vs,body=name.parameters,name.body;env=Environment(name.env);functions=name.functions
 else:
  if name not in FORMS:raise Condition('DESIGNATOR')
  vs,body=FORMS[name];env=Environment();functions={}
 declared=set(getattr(name,'specials',()))
 def single(expr):
  values=run(expr);return values[0] if values else 'nil'
 def run(expr):
  nonlocal functions,declared
  if not isinstance(expr,list):
   if expr in declared:
    value=SPECIAL_VALUES[expr]
    if value is UNBOUND:raise Condition('UNBOUND')
    return [value]
   return [env.get(expr,expr)]
  op,*args=expr
  if isinstance(op,list):return evaluate(single(op),[single(x) for x in args],nodes)
  if op=='locally':
   old=declared;declared=declared|set(args[0][1][1:])
   try:
    result=['nil']
    for x in args[1:]:result=run(x)
    return result
   finally:declared=old
  if op in ('flet','labels'):
   old=functions;new=dict(old)
   for fname,params,body in args[0]:
    new[fname]=Closure(params,body,env,new if op=='labels' else old);new[fname].specials=set(declared)
   functions=new
   try:return run(args[1])
   finally:functions=old
  if op=='lambda':
   c=Closure(args[0],args[1],env,functions);c.specials=set(declared);return [c]
  if op=='function' and isinstance(args[0],list):return run(args[0])
  if op in ('let','let*'):
   saved=env.copy();old_declared=declared;forms=args[1:];local=set()
   while forms and isinstance(forms[0],list) and forms[0][0]=='declare':
    for declaration in forms[0][1:]:local.update(declaration[1:])
    forms=forms[1:]
   dynamic=local;undo=[]
   def bind(var,value):
    nonlocal declared
    if var in dynamic:undo.append((var,SPECIAL_VALUES[var]));SPECIAL_VALUES[var]=value;declared=declared|{var}
    else:env[var]=value;declared=declared-{var}
   try:
    pending=[]
    for binding in args[0]:
     var,init=binding if isinstance(binding,list) else (binding,'nil')
     value=single(init)
     if op=='let*':bind(var,value)
     else:pending.append((var,value))
    for var,value in pending:bind(var,value)
    declared=declared|local;result=['nil']
    for form in forms:result=run(form)
    return result
   finally:
    for var,value in reversed(undo):SPECIAL_VALUES[var]=value
    declared=old_declared;env.clear();dict.update(env,saved)
  if op=='setq':
   value='nil'
   for var,expr in zip(args[::2],args[1::2]):
    value=single(expr)
    if var in declared:SPECIAL_VALUES[var]=value
    else:env.assign(var,value)
   return [value]
  if op=='function' and args[0] in functions:return [functions[args[0]]]
  if op in ('quote','function'):return [('s:'+args[0] if op=='quote' else 'f:'+BINDINGS.get(args[0],args[0]))]
  if op=='catch':
   tag=single(args[0]);frame=(object(),tag);CATCHES.append(frame)
   try:
    result=['nil']
    for expr in args[1:]:result=run(expr)
    return result
   except Transfer as e:
    if e.target is frame:return e.values
    raise
   finally:assert CATCHES.pop() is frame
  if op=='throw':
   tag=single(args[0]);values=run(args[1]);target=next((f for f in reversed(CATCHES) if f[1]==tag),None)
   if target is None:raise Condition('CONTROL')
   raise Transfer(target,values)
  if op=='unwind-protect':
   try:return run(args[0])
   finally:
    for cleanup in args[1:]:run(cleanup)
  if op=='values':return [single(x) for x in args]
  if op=='if':return run(args[1] if single(args[0])!='nil' else args[2])
  if op=='progn':
   result=[]
   for x in args:result=run(x)
   return result
  if op in ('prog1','multiple-value-prog1'):
   result=run(args[0]);saved=([result[0] if result else 'nil'] if op=='prog1' else result[:])
   for x in args[1:]:run(x)
   return saved
  if op in ('car','cdr','rplaca','rplacd'):
   pair=single(args[0]);value=single(args[1]) if len(args)==2 else None
   if pair=='nil' and op in ('car','cdr'):return ['nil']
   if not isinstance(pair,str) or not (pair.startswith('n') and pair[1:].isdigit()):raise Condition('TYPE')
   i=int(pair[1:]);offset=0 if op in ('car','rplaca') else 1
   if len(args)==1:return [nodes[i][offset]]
   nodes[i][offset]=value;return [pair]
  if op=='apply':
   designator=single(args[0]);actual=[single(x) for x in args[1:-1]];tail=single(args[-1]);seen=set()
   while tail!='nil':
    if not isinstance(tail,str) or not(tail.startswith('n') and tail[1:].isdigit()):raise Condition('TYPE')
    if tail in seen:raise Condition('CIRCULAR')
    seen.add(tail);car,tail=nodes[int(tail[1:])];actual.append(car)
   if isinstance(designator,Closure):return evaluate(designator,actual,nodes)
   if not isinstance(designator,str) or not designator.startswith(('f:','s:')):raise Condition('DESIGNATOR')
   return evaluate(BINDINGS.get(designator[2:],designator[2:]) if designator.startswith('s:') else designator[2:],actual,nodes)
  if op=='funcall':
   designator=single(args[0]);actual=[single(x) for x in args[1:]]
   if isinstance(designator,Closure):return evaluate(designator,actual,nodes)
   if not isinstance(designator,str) or not designator.startswith(('f:','s:')):raise Condition('DESIGNATOR')
   return evaluate(BINDINGS.get(designator[2:],designator[2:]) if designator.startswith('s:') else designator[2:],actual,nodes)
  return evaluate(functions.get(op,BINDINGS.get(op,op)),[single(x) for x in args],nodes)
 # Parse this declared corpus independently of compiler IR. Bind in order.
 mode='required';required=[];optional=[];keywords=[];allow=False;has_keys=False;rest=None
 for x in vs:
  if x=='&optional':mode='optional';continue
  if x=='&rest':mode='rest';continue
  if mode=='rest':rest=x;mode='after-rest';continue
  if x=='&key':mode='key';has_keys=True;continue
  if x=='&allow-other-keys':allow=True;continue
  if mode=='required':required.append(x)
  else:
   spec=x if isinstance(x,list) else [x];var=spec[0];default=spec[1] if len(spec)>1 else 'nil';sp=spec[2] if len(spec)>2 else None
   if mode=='optional':optional.append((var,default,sp))
   else:
    key,var=(var[0],var[1]) if isinstance(var,list) else (':'+var,var)
    keywords.append((key,var,default,sp))
 if len(inputs)<len(required) or (not has_keys and rest is None and len(inputs)>len(required)+len(optional)):raise Condition('ARITY')
 env.update(zip(required,inputs));at=len(required)
 for var,default,sp in optional:
  present=at<len(inputs);env[var]=inputs[at] if present else single(default)
  if sp:env[sp]='t' if present else 'nil'
  at+=1
 if rest is not None:
  head='nil'
  for value in reversed(inputs[at:]):nodes.append([value,head]);head='n'+str(len(nodes)-1)
  env[rest]=head
 if has_keys:
  tail=inputs[at:]
  if len(tail)%2:raise Condition('ARITY')
  first={}
  for k,v in zip(tail[::2],tail[1::2]):first.setdefault(k,v)
  if not allow and first.get(':allow-other-keys','nil')=='nil' and any(k not in [x[0] for x in keywords]+[':allow-other-keys'] for k in first):raise Condition('ARITY')
  for key,var,default,sp in keywords:
   env[var]=first[key] if key in first else single(default)
   if sp:env[sp]='t' if key in first else 'nil'
 return run(body)
def normalize(values,nodes,original):
 # Preserve original graph identities; name new reachable cells by discovery,
 # so the three oracles need not allocate lists in the same physical order.
 order=list(range(original));names={i:i for i in order};closures={}
 def token(x):
  if isinstance(x,Closure):
   if x not in closures:closures[x]='c'+str(len(closures))
   return closures[x]
  if isinstance(x,str) and x.startswith('n') and x[1:].isdigit():
   i=int(x[1:])
   if i not in names:names[i]=len(order);order.append(i)
   return 'n'+str(names[i])
  return x
 result=[token(x) for x in values];pairs=[];i=0
 while i<len(order):pairs.append([token(x) for x in nodes[order[i]]]);i+=1
 return result,pairs

def cases():
 out=[]
 def add(name,args,nodes=None,capacity=64,bindings=None,closure_bytes=0):
  global BINDINGS
  SPECIAL_VALUES.clear();SPECIAL_VALUES.update(dyn_a=101,dyn_b=103,dyn_u=UNBOUND)
  BINDINGS=dict(bindings or {})
  before=[p[:] for p in (nodes or [])];after=[p[:] for p in before]
  try:expected={'status':'RETURN','values':evaluate(name,args,after),'nodes':after}
  except Condition as e:expected={'status':e.kind,'values':[],'nodes':after}
  assert not CATCHES,'model leaked a catch extent'
  nvalues=len(expected['values']);values,visible=normalize(expected['values']+[('unbound' if SPECIAL_VALUES[n] is UNBOUND else SPECIAL_VALUES[n]) for n in SPECIAL_NAMES],after,len(before));expected.update(values=values[:nvalues],specials=values[nvalues:],nodes=visible)
  out.append(dict(id=f'{name}-{len(out):03}',function=name,args=args,capacity=capacity,bindings=BINDINGS,nodes=before,expected=expected,allocated_cells=len(after)-len(before),closure_bytes=closure_bytes))
 for n in (0,1,2,3,4,5,6,16,32,64):
  args=[(-1 if i%2 else 1)*(i+1) for i in range(n)]
  for name in (f'v{n}',f'call{n}'):add(name,args);add(name,['nil','t','n0',-536870912,536870911,7][:n]+args[6:] if n>=6 else ['n0']*n,[[19,'nil']])
  add(f'v{n}',args+[9])
 for name in ('side_order','mutation_call','keep_many','keep_zero','keep_one'):
  add(name,['n0'],[[13,29]]);add(name,['nil']);add(name,[5])
 add('advance',['n0'],[['n1','nil'],[7,'n2'],[8,'nil']])
 add('nested',[71,93]);add('nested',['n0','n1'],[[2,'n1'],[3,'nil']]);add('scalar_zero',[])
 for p in ('nil','t','n0'):add('choose',[p,7,9],[[11,'nil']])
 for f in ('f:v2','f:mutate',5,'nil','f:v1'):add('dynamic2',[f,'n0',17],[[3,5]])
 for p in ('nil',5):add('dynamic2',['f:mutate',p,17])
 for f in ('f:v0','f:v2',3):add('dynamic0',[f])
 for f in ('f:v0','f:v2',3):add('nested_fail',['n0',f],[[8,9]])
 for p in ('n0','nil',7):add('type_fail',[p],[[4,6]])
 for args in ([],[1],[1,2],[1,2,3],[1,2,3,4],['nil'],['t','nil'],['n0','n1','n0']):add('opt',args,[[4,5],[6,7]])
 for args in ([],[7],[7,8],[7,8,9]):add('opt_nil',args)
 for args in (['n0'],['n0',3],['n0',3,5],['n0',3,5,7],['nil']):add('opt_effect',args,[[2,4]])
 for f in ('f:v0','f:v2',3):
  add('opt_failure',['n0',f],[[3,4]]);add('opt_failure',['n0',f,91],[[3,4]])
  add('key_failure',['n0',f],[[3,4]]);add('key_failure',['n0',f,':a',91],[[3,4]])
 for a in (['n0'],['n0',19]):add('opt_forward',a,[[7,9]])
 keyargs=[[],[':a',5],[':b',7],[':b',7,':a',5],[':a','nil'],[':a',5,':a',9],[':b','nil',':b',7],[':bad',7],[':a'],[':bad',7,':allow-other-keys','t'],[':allow-other-keys','t',':bad',7],[':allow-other-keys','nil',':bad',7,':allow-other-keys','t'],[':allow-other-keys','t',':bad',7,':allow-other-keys','nil'],[7,9],[7,9,':allow-other-keys','t'],[':allow-other-keys','nil'],[':a',':b'],[':a','n0',':b','n1']]
 for args in keyargs:
  for name in ('key','key_allow','key_empty','key_empty_allow','key_bind_allow'):add(name,args,[[3,4],[5,6]])
  add('key_effect',['n0']+args,[[3,4],[5,6]])
 for args in ([],[':external',7],[':external','nil'],[':external',7,':external',9],[':b',13],[':a',7]):add('key_alias',[29]+args)
 for args in ([7],[7,9],[7,9,':a',11],[7,9,':b',13],[7,9,':b',13,':a',11],[7,':a',11],[7,9,':bad',11],[7,9,':bad',11,':allow-other-keys','t']):add('opt_key',args)
 for name in ('key_caller','opt_key_caller'):add(name,['n0'],[[61,67]])
 for f in ('f:key_effect','f:key_allow',7):add('key_dynamic',[f,'n0'],[[3,4]])
 # Full 64-word incoming region and first/last duplicate semantics.
 add('key',[':a',7]+[':a',9]*31);add('key',[':bad',3]*31+[':allow-other-keys','t'])
 for n in (0,1,2,63,64,65,129,1024):add('rest_all',list(range(n)))
 for args in ([7],[7,9],[7,9,11,13],['n0','n1','n0','n1']):add('rest_parts',args,[[1,2],[3,4]])
 for args in ([],[':a',7],[':b',9,':a',7],[':a',7,':a',9],[':bad',7],[':a'],[':bad',7,':allow-other-keys','t']):add('rest_key',args)
 for args in (['n0'],['n0',31],['n0',31,41,43]):add('rest_default',args,[[5,6]])
 for name in ('rest_copies','rest_escape'):add(name,['n0'],[[3,4]])
 add('rest_mutate',[1,2,3]);add('rest_mutate',[])
 for f in ('f:v0','f:v2',3):add('rest_key_fail',['n0',f,':b',7],[[3,4]])
 def chain(values,tail='nil'):
  return [[x,('n'+str(i+1) if i+1<len(values) else tail)] for i,x in enumerate(values)]
 for n in (0,1,2,6,65,129,1024):
  nodes=chain(list(range(n)));xs='n0' if n else 'nil'
  for f in ('f:rest_all','f:v0','f:v2'):
   add('apply0',[f,xs],nodes);add('apply2',[f,71,73,xs],nodes)
 for xs,nodes in [(7,[]),('n0',[[11,7]]),('n0',[[11,'n1'],[13,7]])]:add('apply0',['f:rest_all',xs],nodes)
 for f in ('f:rest_all','f:v2',7):add('apply_effect',['n0',f,'n1'],[[8,9],[11,'nil']])
 add('apply_rest',['f:rest_all',7,9,11]);add('apply_rest',['f:v0']);add('apply_rest',['f:v2',1])
 for name in ('apply_nested','apply_keep'):add(name,['f:v6','n0'],chain(list(range(6))))
 add('apply_nil',['f:v2',17,19]);add('apply_built_list',['f:v2','n0'],[[3,4]])
 for f in ('f:v1','f:rest_all'):add('apply_type_fail',[f,'n0'],[[5,'nil']])
 add('call_long',[]);add('call_required_long',[])
 add('key',[':a',7]*512);add('key',[':bad',7]*511+[':allow-other-keys','t'])
 add('apply0',['f:key','n0'],chain([':a',7]*512))
 for n in (65,128,129,257,512,1024):
  cap=4*((n+3)//4);args=[(-i if i%2 else i) for i in range(n)]
  add(f'v{n}',args,capacity=cap)
  if n<=512:
   add(f'call{n}',args,capacity=cap)
   add('apply0',[f'f:v{n}','n0'],chain(args),capacity=cap)
   add('apply_keep',[f'f:v{n}','n0'],chain(args),capacity=max(64,cap))
 for cap in (132,256):
  for name in ('many','keep_large','keep_large_nested','many_optional','many_keyword','many_scalar','large_prog1','large_effects','bound_after_many'):
   add(name,['n0'],[[17,23]],capacity=cap)
  for flag in ('nil','t'):add('many_if',['n0',flag],[[17,23]],capacity=cap)
  for f in ('f:v0','f:v2',3):add('many_failure',['n0',f],[[17,23]],capacity=cap)
 add('bound_after_full',['n0'],[[17,23]],capacity=128)
 add('discard_values',[],capacity=132)
 for cap in (0,4,8,68,132,512):
  add('v0',[],capacity=cap)
  if cap:add('v1',[37],capacity=cap)
 for x in ('nil',7,'n0'):
  for name in ('quoted_call','function_call','self_named'):add(name,[x],[[17,19]])
 for name in ('function_value','quoted_value'):add(name,[])
 for name in ('quoted_apply','function_apply'):add(name,['n0'],chain([31,37]))
 for name in ('walk_list','mutual_a','mutual_b','recursive_keep'):
  for n in (0,1,2,8,16):add(name,['n0' if n else 'nil'],chain(list(range(n))))
 for f in ('s:v2','s:mutate','s:v1'):add('dynamic2',[f,'n0',17],[[3,5]])
 add('apply0',['s:v6','n0'],chain(list(range(6))))
 for target in ('alternate','v0','v2'):
  for name,args in [('call1',[37]),('quoted_call',[37]),('function_call',[37]),('function_value',[]),('dynamic_one',['s:v1',37]),('dynamic_one',['f:v1',37])]:add(name,args,bindings={'v1':target})
 # Literal byte accounting: each captured cell 8; function 24; one/two/three
 # capture environments 8/16/16. Rest-list cells are counted separately.
 for x in (7,'nil','t','n0',-536870912,536870911):
  add('closure_call',[x],[[3,5]],closure_bytes=40)
  add('closure_set',[x,23],[[3,5]],closure_bytes=40)
  add('closure_siblings',[x,23,'n0'],[[3,5]],closure_bytes=72)
  add('closure_distinct',[x,29],[[3,5]],closure_bytes=80)
  add('closure_nested',[x],[[3,5]],closure_bytes=72)
  for name in ('closure_shadow','closure_parallel','closure_parent_write','closure_local_write','closure_default'):
   add(name,[x],[[3,5]],closure_bytes=40)
  add('closure_sequential',[x],[[3,5]],closure_bytes=40)
  add('closure_nested_mutate',[x,31],[[3,5]],closure_bytes=72)
  add('closure_same',[x],[[3,5]],closure_bytes=40)
  add('closure_keep',[x,37],[[3,5]],closure_bytes=40)
  add('closure_fail_escape',['n0',x,7],[[3,5]],closure_bytes=40)
  add('closure_apply',[x,'nil'],[[3,5]],closure_bytes=40)
  add('closure_apply',[x,'n0'],[[43,'nil']],closure_bytes=40)
 add('closure_empty',[],closure_bytes=24)
 add('closure_optional',[],closure_bytes=112)
 add('closure_key',[],closure_bytes=56)
 add('closure_rest',[],closure_bytes=40)
 add('closure_many_captures',[7,11,13],closure_bytes=64)
 add('closure_multiset',[7,11])
 for name in ('closure_capture_closure','closure_function_syntax','closure_default_capture','closure_three_levels'):
  add(name,['n0'],[[17,19]],closure_bytes={'closure_capture_closure':80,'closure_three_levels':104}.get(name,40))
 for name in ('closure_optional_empty','closure_optional_full','closure_key_empty'):add(name,[],closure_bytes=56)
 add('closure_bad_default',[17,5],closure_bytes=8)
 add('closure_let_order',['n0'],[[3,5]],closure_bytes=64)
 add('closure_wide',list(range(129)),capacity=132,closure_bytes=1576)
 for x in (7,'nil','n0',-536870912,536870911):
  for name,extra in [('local_flet',40),('local_flet_use',40),('local_flet_siblings',72),('local_self_identity',56),('local_lexical_shadow',40),('local_flet_outer',88),('local_transitive_use',128),('local_inline',0),('local_inline_full',0),('local_inline_rest',0),('local_inline_rest_empty',0),('local_inline_escape_use',56),('local_direct_lambda',0),('local_key',40)]:
   args=[x]+([31] if name=='local_flet_use' else ['n0'] if name=='local_flet_siblings' else [])
   add(name,args,[[17,19]],closure_bytes=extra)
 for name in ('local_labels','local_mutual','local_mutual_escape','local_optional_recursive'):
  for n in (0,1,2,8,20):
   add(name,[37,'n0' if n else 'nil'],chain(list(range(n))),capacity=4,closure_bytes={'local_labels':40,'local_mutual':104,'local_mutual_escape':104,'local_optional_recursive':40}[name])
 for name in ('local_apply_literal','local_apply_function_literal'):
  for v in ('nil','t',7,'n1'):add(name,[37,'n0'],[[v,'nil'],[11,13]],closure_bytes=8)
 add('local_inline_order',['n0'],[[3,5]])
 for n in (0,1,8):add('local_apply_self',[37,'n0' if n else 'nil'],chain(list(range(n))),capacity=4,closure_bytes=40)
 add('local_labels_defaults',[37],closure_bytes=88)
 add('local_labels_pair_use',[37,'n0'],[[11,13]],closure_bytes=120)
 add('local_inline_defaults',[23])
 add('local_inline_long',[29])
 add('local_literal_apply_order',['n0'],[[3,5]],closure_bytes=8)
 add('local_apply_variable',[37],closure_bytes=40)
 add('local_apply_parameter',[37],closure_bytes=40)
 for name in ('local_apply_literal','local_apply_function_literal'):
  add(name,[37,'nil'],closure_bytes=8)
  add(name,[37,'n0'],chain([11,13]),closure_bytes=8)
 for name in ('tail_apply_nocapture','tail_apply_tail_out'):
  for value in (7,'nil','t','n1'):add(name,['n0'],[[value,'nil'],[11,13]])
 for name,extra in [('tail_apply_non_tail',8),('tail_apply_escape_use',56),('tail_apply_mutate',8)]:
  add(name,[37,'n0'],[[17,'nil']],closure_bytes=extra)
 add('tail_apply_nested',['n0','n1'],[[13,'nil'],[17,'nil']],closure_bytes=16)
 add('tail_apply_key',[37,'nil'],closure_bytes=8)
 add('tail_apply_key',[37,'n0'],chain([':y',41]),closure_bytes=8)
 for n in (0,1,2,7,30):
  xs='n0' if n else 'nil'
  add('tail_apply_loop',[xs],chain(list(range(n))),capacity=4)
  add('tail_local_apply_loop',[37,xs],chain(list(range(n))),capacity=4,closure_bytes=40)
  add('tail_indirect',['f:tail_indirect',xs],chain(list(range(n))),capacity=4)
  add('tail_vary_a',[xs],chain(list(range(n))),capacity=4)
  add('tail_failure',[xs,7],chain(list(range(n))),capacity=4)
 for n in (0,1,5):
  nodes=chain(list(range(n)));nodes.append([17,19])
  add('non_tail_effect',['n0' if n else 'nil','n'+str(n)],nodes,capacity=4)
 for n in (0,1,2,7):
  for name in ('tail_wide_a','tail_zero','tail_many'):
   add(name,['n0' if n else 'nil'],chain(list(range(n))),capacity=132 if name=='tail_many' else 4)
 for n in (1,2,3,6,32,64):
  nodes=chain(list(range(1,n)));nodes.append([3,5])
  add('ordinary_apply_prefix',['f:v'+str(n),'n0' if n>1 else 'nil','n'+str(n-1)],nodes)
 for value in (7,'nil','t','n1'):
  add('ordinary_apply_mixed',['f:v2',value,'n0'],[[23,'nil'],[11,13]])
  add('ordinary_apply_closure',[value,'n0'],[[23,'nil'],[11,13]],closure_bytes=40)
  add('ordinary_literal_apply_prefix',[value,'n0','n1'],[[23,'nil'],[11,13]],closure_bytes=8)
 add('ordinary_apply_prefix',['f:v3','nil','n0'],[[3,5]])
 add('ordinary_apply_prefix',['f:v2','n0','n1'],[[3,5],[11,13]])
 add('uw_order',['n0'],[['n1','nil'],[11,'n2'],[13,'n3'],[17,'nil']])
 # Cleanup order, exception replacement, roots, retained values and dynamic calls.
 for p in ('n0','nil',7):
  for name in ('uw_zero','uw_normal_nested','uw_mutate_result','uw_no_cleanup','uw_cleanup_fail_first'):
   add(name,[p],[[11,13]])
  for x in ('nil','t',-536870912,536870911,'n0'):
   add('uw_one',[p,x],[[11,13]])
 for name in ('uw_call','uw_argument','uw_replace','uw_replace_outer','uw_cleanup_extent','uw_before'):
  for f in ('f:v0','f:v1',7,'nil','f:scalar_zero'):
   add(name,['n0',f],[[11,13]])
 for f in ('f:v0','f:v1',7):
  for g in ('f:v0','f:v1',7):add('uw_nested',['n0',f,g],[[11,13]])
 add('uw_heap',['n0'],[[11,13]])
 for x in ('n0',7,'nil'):add('uw_datum',['n0',x],[[11,13]])
 add('uw_capacity',['n0'],[[11,13]],capacity=132)
 for n in (132,256,512):add('uw_many',['n0'],[[11,13]],capacity=n)
 for x in ('nil','t',7,'n0'):
  add('uw_capture',['n0',x],[[11,13]],closure_bytes=40)
  add('uw_literal_apply',['n0',x],[[11,13]])
  add('uw_local',['n0',x],[[11,13]],closure_bytes=40)
 for args in ([],[11],[11,13],list(range(129))):add('uw_rest',['n0',*args],[[11,13]],capacity=256)
 for f in ('f:v0','f:v2',7):
  for xs in ('nil','n1',7):add('uw_apply',['n0',f,xs],[[11,13],[17,'n2'],[19,'nil']])
 for n in (0,1,8,40):add('uw_walk',['n0' if n else 'nil'],chain(list(range(n))),capacity=4)
 for n in (0,1,100,3000):add('uw_tail_child',['n0','n1' if n else 'nil'],[[11,13]]+[[i,'n'+str(i+2) if i+1<n else 'nil'] for i in range(n)],capacity=4)
 for name in ('uw_default','uw_key'):
  add(name,['n0'],[[11,13]])
  add(name,['n0',17] if name=='uw_default' else ['n0',':x',17],[[11,13]])

 for name in ('ct_state_normal','ct_state_exit','ct_state_nested','ct_state_restored'):add(name,['n0'],[[11,13]])
 for f in (7,'f:v1'):add('ct_state_error',['n0',f],[[11,13]])
 add('ct_raw_catch',[7,11]);add('ct_raw_throw',[7,11])
 for tag in ('nil','t',7,'n0','f:v0',':a'):
  for x in ('nil','t',-536870912,536870911,'n0'):
   for name in ('ct_catch','ct_normal','ct_same','ct_let'):add(name,[tag,x],[[11,13]])
  for name in ('ct_empty','ct_zero'):add(name,[tag],[[11,13]])
  add('ct_many',[tag,'n0'],[[11,13]],capacity=132)
 for a,b in [(7,7),(7,11),('nil','nil'),('n0','n0'),('n0','n1'),('f:v0','f:v1')]:
  add('ct_identity',[a,b],[[11,13],[11,13]])
  add('ct_nested',[a,b,'n0'],[[11,13],[11,13]])
  add('ct_cleanup_override',['n0',a,b],[[11,13],[11,13]])
  add('ct_cleanup_handled',['n0',a,b],[[11,13],[11,13]])
  add('ct_dead_inner',['n0',a,b],[[11,13],[11,13]])
 for name in ('ct_tag_effect','ct_missing_effect','ct_cleanup','ct_cleanup_normal','ct_cleanup_rethrow','ct_error_to_throw','ct_pending_values','ct_two_cleanups'):
  for tag in ('nil',7,'n0'):add(name,['n0',tag],[[11,13]])
 for f in ('f:ct_throw','f:v2','f:v0',7):
  add('ct_dynamic',[7,f]);add('ct_apply',[7,f,'n0'],[[17,'nil']])
  add('ct_cleanup_error',['n0',7,f],[[11,13]])
 for name,extra in [('ct_capture',0),('ct_local',40),('ct_escaped',40),('ct_retired',40)]:
  for tag in ('nil',7,'n0'):add(name,[tag,'n0'],[[11,13]],closure_bytes=extra)
 add('ct_default',[7]);add('ct_default',[7,17])
 for n in (0,1,10,3000):add('ct_tail_start',[7,'n0' if n else 'nil'],chain(list(range(n))),capacity=4)
 for n in (0,1,10,40):add('ct_recursive',['n0' if n else 'nil'],chain(list(range(n))),capacity=4)

 for x in (7,'nil','t','n0',-536870912,536870911):
  for name in ('sd_bind','sd_parallel','sd_sequential','sd_duplicate','sd_local_decl','sd_after','sd_unbound','sd_unbound_after','sd_global_after','sd_values','sd_zero','sd_default','sd_lexical_shadow','sd_declaration_shadow'):
   add(name,[x],[[11,13]],capacity=256 if name=='sd_values' else 64)
  for name in ('sd_nested','sd_assign'):add(name,[x,17],[[11,13]])
  add('sd_escape',[x],[[11,13]],closure_bytes=24)
  add('sd_closure_bound',[x,19],[[11,13]],closure_bytes=24)
  add('sd_local',[x],[[11,13]],closure_bytes=24)
  for tag in ('nil',7,'n0'):
   add('sd_catch',[tag,x],[[11,13]])
   for name in ('sd_clean_catch','sd_outer_catch','sd_replace'):add(name,['n0',tag,x],[[11,13]])
  for name in ('sd_failure_init','sd_error_cleanup'):add(name,['n0',x],[[11,13]])
  add('sd_apply',[x,'nil'],[[11,13]])
 for name in ('sd_read','sd_read_u','sd_nil'):add(name,[])
 for name in ('sd_set','sd_set_u'):add(name,[211]);add(name,['n0'],[[11,13]])
 add('sd_recursive',['n0'],[[i,'n'+str(i+1) if i<39 else 'nil']for i in range(40)],capacity=4)
 add('sd_tail_child',[17,'n0'],[[i,'n'+str(i+1) if i<2999 else 'nil']for i in range(3000)],capacity=4)
 return out

def lisp_input():
 def lit(x):
  if isinstance(x,list):return '('+' '.join(map(lit,x))+')'
  return json.dumps(x) if isinstance(x,str) else str(x)
 return '(in-package "CL-USER")\n(defparameter *call-sources* \''+lit([[m['name'],m['source']] for m in modules()])+')\n(defparameter *call-cases* \''+lit([[c['id'],c['function'],c['nodes'],c['args'],[list(pair) for pair in c['bindings'].items()]] for c in cases()])+')\n'
REFUSALS=[('escaped-key-literal','(lambda () (values :A :|a|))'),('escaped-key-parameter','(lambda (&key ((:|a| x))) x)'),('host-macro','(lambda (p) (typep p \'fixnum))'),('missing-rest-var','(lambda (&rest) nil)'),('rest-extra-var','(lambda (&rest p q) p)'),('aux','(lambda (&aux p) p)'),('bad-key','(lambda (&key ((p x))) x)'),('bad-order','(lambda (&key a &optional b) a)'),('duplicate-var','(lambda (a &optional a) a)'),('forward-default','(lambda (&optional (a b) b) a)'),('macro-default','(lambda (&optional (a (typep nil \'fixnum))) a)'),('apply-missing-tail','(lambda (p) (apply p))'),('local-function','(lambda (p) (flet ((f () p)) (f)))'),('unknown','(lambda (p) (unlinked p))'),('empty-prog1','(lambda () (prog1))'),('heap-constant','(lambda () \'(1 2))'),('cycle','(lambda (p) #1=(progn . #1#))'),('dotted','(lambda (p) (v1 . p))'),('extra-form','(lambda (p) p) 2')]
REFUSALS += [('inlined-lambda-bind','(lambda (x) (funcall (lambda () x)))'),('unbound-setq','(lambda (x) (setq y x))'),('special-declaration','(lambda (x) (let ((y x)) (declare (special y)) (lambda () y)))'),('inner-host-macro',"(lambda (x) (lambda () (typep x 'fixnum)))"),('duplicate-let','(lambda (x) (let ((a x) (a 7)) a))'),('inner-aux','(lambda (x) (lambda (&aux y) x))'),('inner-forward-default','(lambda (x) (lambda (&optional (a b) b) x))'),('setf-place','(lambda (x) (setf x 7))'),('labels','(lambda (x) (labels ((f () x)) (f)))'),('do-loop','(lambda (x) (loop repeat 3 do (setq x nil)))')]
REFUSALS=[r for r in REFUSALS if r[0] not in ('local-function','labels','inlined-lambda-bind')]
REFUSALS += [('local-return-from','(lambda (x) (flet ((f () (return-from f x))) (f)))'),('duplicate-local','(lambda () (flet ((f () 1) (f () 2)) (f)))'),('flet-outside-scope','(lambda (x) (flet ((g () (f)) (f () x)) (g)))'),('labels-unbound','(lambda () (labels ((f () (g))) (f)))'),('local-macro','(lambda () (flet ((when (x) x)) (when 7)))'),('local-declaration','(lambda () (flet ((f () 7)) (declare (inline f)) (f)))')]
old_input=lisp_input
def lisp_input():return old_input()+'(defparameter *call-refusals* \''+'('+' '.join('('+json.dumps(n)+' '+json.dumps(s)+')' for n,s in REFUSALS)+'))\n'

REFUSALS += [('empty-unwind','(lambda () (unwind-protect))'),('unwind-handler','(lambda () (unwind-protect 7 (handler-case 1 (error () 2))))'),('unwind-special','(lambda (x) (unwind-protect 7 (let ((y x)) (declare (special y)) y)))')]

REFUSALS += [('empty-catch','(lambda () (catch))'),('throw-arity','(lambda () (throw 7))'),('catch-return-from','(lambda (x) (catch x (return-from missing 7)))')]

REFUSALS=[r for r in REFUSALS if r[0] not in ('special-declaration','unwind-special')]
REFUSALS += [('special-parameter','(lambda (dyn_a) (declare (special dyn_a)) dyn_a)'),('other-declaration','(lambda (x) (locally (declare (fixnum x)) x))'),('progv-not-yet','(lambda (x) (progv x nil nil))')]

REFUSALS += [('escaped-special-name','(lambda () (locally (declare (special |dyn_a|)) |dyn_a|))')]

REFUSALS += [('foreign-special-package','(lambda () (locally (declare (special cl-user::dyn_a)) cl-user::dyn_a))'),('special-package-collision','(lambda () (locally (declare (special dyn_a cl-user::dyn_a)) (values dyn_a cl-user::dyn_a)))')]
