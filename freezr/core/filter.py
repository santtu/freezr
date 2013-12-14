from pyparsing import (Word, alphanums, Keyword, Group, Suppress,
                       oneOf, dblQuotedString, sglQuotedString,
                       removeQuotes,
                       opAssoc, infixNotation, StringEnd, StringStart)
import pyparsing
import re
import logging

log = logging.getLogger('freezr.filter')
TRACE = False


# reprovide ParseException as an exception from our own namespace
ParseException = pyparsing.ParseException


# monkeypatch for low-level trace
def _trace(self, *args, **kwargs):
    if TRACE:
        self.debug(*args, **kwargs)
log.trace = _trace
del _trace


def dump(w, t):
    log.trace("============ {0}".format(w))
    for i in range(len(t)):
        log.trace("#{0} = {1!r}".format(i, t[i]))


def dumper(w):
    def func(s, l, t):
        dump(w, t)
        return t

    return func


def toksz(cls):
    return lambda s, l, t: cls()


def toks(cls):
    return lambda s, l, t: cls(t)


def toks0(cls):
    return lambda s, l, t: cls(t[0])


def toks00(cls):
    return lambda s, l, t: cls(t[0][0])

# def reorderInlineOperation(s, l, t):
#     ret = (t[1], t[0], t[2])
#     print("reorder: s={0!r} l={1!r} t={2!r} => {3!r}".format(s, l, t, ret))
#     return ret

# def makeLiteral(s, l, t):
#     ret = ('literal', t[0])
#     print("literal: s={0!r} l={1!r} t={2!r} => {3!r}".format(s, l, t, ret))
#     return ret


class Element(object):
    def __str__(self):
        return unicode(self)


class AlwaysFalse(Element):
    def evaluate(self, env):
        return False

    def __unicode__(self):
        return "false"


class AlwaysTrue(Element):
    def evaluate(self, env):
        return True

    def __unicode__(self):
        return "true"


class Literal(Element):
    SIMPLE_LITERAL_RE = re.compile(r'^[-a-zA-Z0-9]+$')

    def __init__(self, value):
        self.value = value

    def __unicode__(self):
        if ((self.value in Variable.VARIABLES or
             not self.SIMPLE_LITERAL_RE.match(self.value))):
            return "'{0}'".format(self.value)

        return unicode(self.value)

    def evaluate(self, env):
        log.trace('Literal: => {0!r}'.format(self.value))
        return self.value


class Variable(Element):
    VARIABLES = ('region', 'storage', 'type', 'vpc')

    def __init__(self, variable):
        self.variable = variable

    def __unicode__(self):
        return self.variable

    def evaluate(self, env):
        value = env.get(self.variable)
        log.trace("Variable: {0} => {1!r}".format(self.variable, value))
        return value


class Tag(Element):
    def __init__(self, s, loc, toks):
        # note, the key should always be a literal, so we directly
        # evaluate it in empty environment to fix its value
        self.key = toks[1].evaluate({})

    def __unicode__(self):
        return "tag[{0!s}]".format(self.key)

    def evaluate(self, env):
        value = env.get('tags', dict()).get(self.key, '')
        log.trace("Tag: {0!r} => {1!r}".format(self.key, value))
        return value


class Logical(Element):
    def quoted(self, expr):
        if isinstance(expr, Logical):
            return "({0})".format(expr)

        return "{0}".format(expr)


class Not(Logical):
    def __init__(self, expr):
        self.expr = expr

    def __unicode__(self):
        return "not {0}".format(self.quoted(self.expr))

    def evaluate(self, env):
        return not self.expr.evaluate(env)


class And(Logical):
    def __init__(self, exprs):
        #dump(toks)
        #self.ands = toks[0]
        self.ands = exprs

    def __unicode__(self):
        return " and ".join(map(lambda a: self.quoted(a), self.ands))

    def evaluate(self, env):
        for expr in self.ands:
            if not expr.evaluate(env):
                return False
        return True


class Or(Logical):
    def __init__(self, exprs):
        self.ors = exprs

    def __unicode__(self):
        return " or ".join(map(lambda a: self.quoted(a), self.ors))

    def evaluate(self, env):
        for expr in self.ors:
            value = expr.evaluate(env)
            log.trace("Or: {0!r}|{0} => {1}".format(expr, value))

            if value is True:
                return True

        return False


class Comparison(Element):
    ops = {
        '=': (lambda a, b: a == b),
        '!=': (lambda a, b: a != b),
        '~': (lambda a, b: re.search(b, a) is not None),
        '!~': (lambda a, b: not (re.search(b, a) is not None)),
        }

    def __init__(self, exprs):
        self.op = exprs[1]
        self.lhs = exprs[0]
        self.rhs = exprs[2]

    def __unicode__(self):
        return "{0} {1} {2}".format(self.lhs, self.op, self.rhs)

    def evaluate(self, env):
        lhs = self.lhs.evaluate(env)
        rhs = self.rhs.evaluate(env)
        value = self.ops[self.op](lhs, rhs)
        log.trace(
            "Compare: {0!r} {1} {2!r} => {3!r}".format(
                lhs, self.op, rhs, value))
        return value


class NotNull(Element):
    def __init__(self, s, loc, toks):
        #dump("NotNull", toks)
        self.expr = toks[0]

    def __unicode__(self):
        return "{0}".format(self.expr)

    def evaluate(self, env):
        value = self.expr.evaluate(env)
        log.trace("NotNull: {0!r}{0} => {1}".format(self.expr, value))
        return value is not None and value != ""


def get_parser():
    op_literal = ((Word(alphanums + ",.-_")
                   | dblQuotedString.setParseAction(removeQuotes)
                   | sglQuotedString.addParseAction(removeQuotes)).
                  addParseAction(toks0(Literal)))

    op_tag = (Keyword('tag')
              + Suppress('[')
              + op_literal
              + Suppress(']')).setParseAction(Tag)

    op_value = (op_tag
                | (oneOf(" ".join(Variable.VARIABLES))
                   .setParseAction(toks0(Variable))))

    op_lhs = op_value
    op_rhs = op_value | op_literal
    op_compare = (Keyword("=") | Keyword("~") | Keyword("!=") | Keyword("!~"))
    op_and = Keyword("and")
    op_or = Keyword("or")
    op_not = Keyword("not")

    op_true = Suppress(Keyword("true")).setParseAction(toksz(AlwaysTrue))
    op_false = Suppress(Keyword("false")).setParseAction(toksz(AlwaysFalse))

    op_compare_expression = ((op_lhs
                              + op_compare
                              + op_rhs)
                             .addParseAction(toks(Comparison)))

    op_test_expression = (Group(op_lhs)
                          .addParseAction(lambda s, l, t: t[0])
                          .addParseAction(NotNull))

    op_value_expression = (op_false
                           | op_true
                           | op_compare_expression
                           | op_test_expression)

    op_expression = (
        StringStart()
        + infixNotation(
            op_value_expression,
            [(Suppress(op_not), 1, opAssoc.RIGHT, toks00(Not)),
             (Suppress(op_and), 2, opAssoc.LEFT, toks0(And)),
             (Suppress(op_or), 2, opAssoc.LEFT, toks0(Or))])
        + StringEnd())

    return op_expression


class Filter(object):
    parser = get_parser()

    def __init__(self, expression=AlwaysFalse()):
        self._expression = expression

    @classmethod
    def parse(cls, text):
        return cls(cls.parser.parseString(text)[0])

    def AND(self, other):
        return Filter(And([self.expression, other.expression]))

    def OR(self, other):
        return Filter(Or([self.expression, other.expression]))

    def NOT(self):
        return Filter(Not(self))

    @property
    def expression(self):
        return self._expression

    def format(self):
        return unicode(self.expression)

    def evaluate(self, env):
        return self.expression.evaluate(env)


def format(exp):
    assert(isinstance(exp, Element),
           "{0!r} is not of type Element".format(exp))

    return unicode(exp)
