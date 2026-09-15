"""Function-cell lookup results with finite symbol-name arguments.

This qualifies the selected cells, not their contents. A local function called
FDEFINITION, an arbitrary package's homonym and a function-valued name do not
satisfy the Common Lisp lookup operation.
"""
from lexical import Resolver as LexicalResolver
from finite import Unbounded,require


class Resolver(LexicalResolver):
    def resolve(self,value,owner,site,stack=()):
        g=self.graph;n=g.node(value)
        if n and n.get('operator')=='CCL::CALL':
            args=g.items(n['operands'])
            if len(args)==3 and args[2] is None:
                operator=g.node(args[0])
                form=g.items(operator['operands']) if operator and operator.get('operator')=='CCL::IMMEDIATE' else []
                if len(form)==1 and isinstance(form[0],dict) and form[0].get('symbol') in (
                        'COMMON-LISP::FDEFINITION','COMMON-LISP::SYMBOL-FUNCTION'):
                    require(set(form[0])=={'symbol','identity'},'LOOKUP_OPERATOR_IDENTITY')
                    if n['id'] in stack or len(stack)>=128:raise Unbounded('lookup-expression-cycle')
                    parts=g.items(args[1]);require(len(parts)==2,'LOOKUP_ARGUMENT_PARTS')
                    actual=g.items(parts[0])+list(reversed(g.items(parts[1])))
                    if len(actual)!=1:raise Unbounded('lookup-arity')
                    values,trace=self.resolve(actual[0],owner,site,stack+(n['id'],))
                    if any(kind!='symbol' or mode!='symbol-designator' for kind,ident,mode in values):
                        raise Unbounded('lookup-name-not-symbol-designator')
                    return ({('symbol',ident,'captured-function-cell-value') for kind,ident,mode in values},
                        [dict(node=n['id'],operator=form[0]['symbol'],operator_symbol=form[0]['identity'],
                              argument=actual[0],value_semantics='function-cell-value-at-lookup')]+trace)
        return super().resolve(value,owner,site,stack)
