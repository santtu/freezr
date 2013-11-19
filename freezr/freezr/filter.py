from pyparsing import Word, alphanums, Keyword, Group, Combine, Forward, Suppress, Optional, OneOrMore, oneOf, alphas, dblQuotedString, sglQuotedString, Literal, ParseException, removeQuotes, operatorPrecedence, opAssoc, infixNotation, printables, StringEnd, StringStart
import re
import logging

log = logging.getLogger('freezr.filter')

def dump(w, t):
    log.debug("============ {0}".format(w))
    for i in range(len(t)):
        log.debug("#{0} = {1!r}".format(i, t[i]))

def dumper(w):
    def func(s, l, t):
        dump(w, t)
        return t

    return func

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

class Literal(Element):
    SIMPLE_LITERAL_RE = re.compile(r'^[-a-zA-Z0-9]+$')

    def __init__(self, s, loc, toks):
        self.value = toks[0]
        #print("Literal: toks={0!r}".format(toks[0]))

    def __unicode__(self):
        if (self.value in Variable.VARIABLES or
            not self.SIMPLE_LITERAL_RE.match(self.value)):
            return "'{0}'".format(self.value)

        return unicode(self.value)

    def evaluate(self, env):
        log.debug('Literal: => {0!r}'.format(self.value))
        return self.value

class Variable(Element):
    VARIABLES = ('region', 'storage', 'type', 'vpc')

    def __init__(self, s, loc, toks):
        self.variable = toks[0]

    def __unicode__(self):
        return self.variable

    def evaluate(self, env):
        value = env[self.variable]
        log.debug("Variable: {0} => {1!r}".format(self.variable, value))
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
        log.debug("Tag: {0!r} => {1!r}".format(self.key, value))
        return value

class Logical(Element):
    def quoted(self, expr):
        if isinstance(expr, Logical):
            return "({0})".format(expr)

        return "{0}".format(expr)

class Not(Logical):
    def __init__(self, s, loc, toks):
        #dump(toks)
        self.expr = toks[0][0]

    def __unicode__(self):
        return "not {0}".format(self.quoted(self.expr))

    def evaluate(self, env):
        return not self.expr.evaluate(env)

class And(Logical):
    def __init__(self, s, loc, toks):
        #dump(toks)
        self.ands = toks[0]

    def __unicode__(self):
        return " and ".join(map(lambda a: self.quoted(a), self.ands))

    def evaluate(self, env):
        for expr in self.ands:
            if expr.evaluate(env) == False:
                return False
        return True

class Or(Logical):
    def __init__(self, s, loc, toks):
        #dump(toks)
        self.ors = toks[0]

    def __unicode__(self):
        return " or ".join(map(lambda a: self.quoted(a), self.ors))

    def evaluate(self, env):
        for expr in self.ors:
            value = expr.evaluate(env)
            log.debug("Or: {0!r}|{0} => {1}".format(expr, value))

            if value == True:
                return True

        return False

class Comparison(Element):
    ops = {
        '=': (lambda a, b: a == b),
        '!=': (lambda a, b: a != b),
        '~': (lambda a, b: re.search(b, a) is not None),
        '!~': (lambda a, b: not (re.search(b, a) is not None)),
        }

    def __init__(self, s, loc, toks):
        self.op = toks[1]
        self.lhs = toks[0]
        self.rhs = toks[2]

    def __unicode__(self):
        return "{0} {1} {2}".format(self.lhs, self.op, self.rhs)

    def evaluate(self, env):
        lhs = self.lhs.evaluate(env)
        rhs = self.rhs.evaluate(env)
        value = self.ops[self.op](lhs, rhs)
        log.debug("Compare: {0!r} {1} {2!r} => {3!r}".format(lhs, self.op, rhs, value))
        return value

class NotNull(Element):
    def __init__(self, s, loc, toks):
        #dump("NotNull", toks)
        self.expr = toks[0]

    def __unicode__(self):
        return "{0}".format(self.expr)

    def evaluate(self, env):
        value = self.expr.evaluate(env)
        log.debug("NotNull: {0!r}{0} => {1}".format(self.expr, value))
        return value is not None and value != ""

def get_parser():
    op_literal = (Word(alphanums + ",.-_") | dblQuotedString.setParseAction(removeQuotes) | sglQuotedString.addParseAction(removeQuotes)).addParseAction(Literal)

    op_tag = (Keyword('tag') + Suppress('[') + op_literal + Suppress(']')).setParseAction(Tag)
    op_value = op_tag | oneOf(" ".join(Variable.VARIABLES)).setParseAction(Variable)

    op_lhs = op_value
    op_rhs = op_value | op_literal
    op_compare = (Keyword("=") | Keyword("~") | Keyword("!=") | Keyword("!~"))
    op_and = Keyword("and")
    op_or = Keyword("or")
    op_not = Keyword("not")

    op_compare_expression = ((op_lhs + op_compare + op_rhs).addParseAction(Comparison))
    op_test_expression = Group(op_lhs).addParseAction(lambda s, l, t: t[0]).addParseAction(NotNull)
    op_value_expression = op_compare_expression | op_test_expression


    op_expression = (StringStart()
                     + infixNotation(op_value_expression,
                                     [(Suppress(op_not), 1, opAssoc.RIGHT, Not),
                                      (Suppress(op_and), 2, opAssoc.LEFT, And),
                                      (Suppress(op_or), 2, opAssoc.LEFT, Or)])
                     + StringEnd())

    return op_expression

class Filter(object):
    parser = get_parser()

    def __init__(self, text):
        self._expression = self.parser.parseString(text)[0]

    @property
    def expression(self):
        return self._expression

    def format(self):
        return unicode(self.expression)

    def evaluate(self, env):
        return self.expression.evaluate(env)

def format(exp):
    assert isinstance(exp, Element), "{0!r} is not of type Element".format(exp)
    #print("exp={0!r}".format(exp))
    return unicode(exp)

if __name__ == "__main__":
    tests = (
        'region',
        'tag[class]',
        'not region',
        'not tag[class]',
        '(region)',
        '(tag[class])',
        'not (region)',
        'not (tag[class])',
        '((region))',
        '((tag[class]))',
        'region = "region"', # this should be valid
        'region = us-east-1',
        'region = "us-east-1"',
        'tag[class] = production',
        'tag[class] = "pre production"',
        'tag[master] = tag[owner]',
        'tag[master] != tag[owner]',
        'region != tag[region]',
        'region and region',
        'region and (region or region)',
        'not region and (region or region)',
        'not (region and (region or region))',
        'region or region or region or region',
        'region and region and region and region',
        'region or region and region or region',
        'not (region or region and region or region)',
        '((region) and (type)) or (tag[class])',
        '(region and type) or (tag[class])',
        '(region and type) or tag[class]',
        'region and (type or tag[class])',
        'region and type or tag[class]',
        'region or type',
        'storage = ebs',
        'storage != ebs',
        'storage ~ e.s',
        'storage ~ \'^e[b]{1,1}s$\'',
        'storage ~ "e\.s"',
        'region = us-east-1 and storage = ebs',
        'tag[production]',
        'tag[production] = on',
        '(region = us-east-1 and storage = ebs) and tag[production]'
        )

    for test in tests:
        print("-----------------: " + test)
        try:
            ret = Filter(test).expression
            #print(repr(ret))
            fmt = format(ret)
            print("=================: " + fmt)
            ret2 = Filter(fmt).expression
            fmt2 = format(ret2)
            assert fmt == fmt2, "Results don't match:\n 1. {0}\n 2. {1}".format(fmt, fmt2)
        except ParseException as ex:
            print("Error:" + str(ex))
