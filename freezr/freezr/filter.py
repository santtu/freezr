from pyparsing import Word, alphanums, Keyword, Group, Combine, Forward, Suppress, Optional, OneOrMore, oneOf, alphas, dblQuotedString, sglQuotedString, Literal, ParseException, removeQuotes, operatorPrecedence, opAssoc, infixNotation, printables
import re

def dump(t):
    for i in range(len(t)):
        print("#{0} = {1!r}".format(i, t[i]))

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

class Variable(Element):
    VARIABLES = ('region', 'storage', 'type', 'vpc')

    def __init__(self, s, loc, toks):
        self.variable = toks[0]

    def __unicode__(self):
        return self.variable

class Tag(Element):
    def __init__(self, s, loc, toks):
        self.key = toks[1]

    def __unicode__(self):
        return "tag[{0!s}]".format(self.key)

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

class And(Logical):
    def __init__(self, s, loc, toks):
        #dump(toks)
        self.ands = toks[0]

    def __unicode__(self):
        return " and ".join(map(lambda a: self.quoted(a), self.ands))
#        return "{0} and {1}".format(self.quoted(self.lhs), self.quoted(self.rhs))

class Or(Logical):
    def __init__(self, s, loc, toks):
        #dump(toks)
        self.ors = toks[0]

    def __unicode__(self):
        return " or ".join(map(lambda a: self.quoted(a), self.ors))
        #return "{0} or {1}".format(self.quoted(self.lhs), self.quoted(self.rhs))

class Comparison(Element):
    def __init__(self, s, loc, toks):
        self.op = toks[1]
        self.lhs = toks[0]
        self.rhs = toks[2]

    def __unicode__(self):
        return "{0} {1} {2}".format(self.lhs, self.op, self.rhs)

class NotNull(Element):
    def __init__(self, s, loc, toks):
        self.expr = toks[0]

    def __unicode__(self):
        return "{0}".format(self.expr)

op_literal = (Word(alphanums + ",.-_") | dblQuotedString.setParseAction(removeQuotes) | sglQuotedString.addParseAction(removeQuotes)).addParseAction(Literal)

op_tag = (Keyword('tag') + Suppress('[') + op_literal + Suppress(']')).setParseAction(Tag)
op_value = op_tag | oneOf(" ".join(Variable.VARIABLES)).setParseAction(Variable)

op_lhs = op_value
op_rhs = op_value | op_literal
op_compare = (Keyword("=") | Keyword("~") | Keyword("!=") | Keyword("!~"))
op_and = Keyword("and")
op_or = Keyword("or")
op_not = Keyword("not")

op_compare_expression = ((op_lhs + op_compare +
                          op_rhs).setParseAction(Comparison) |
                         op_lhs.setParseAction(NotNull))

op_expression = infixNotation(op_compare_expression,
                              [(Suppress(op_not), 1, opAssoc.RIGHT, Not),
                               (Suppress(op_and), 2, opAssoc.LEFT, And),
                               (Suppress(op_or), 2, opAssoc.LEFT, Or)])

class Filter(object):
    def __init__(self, text):
        pass

def format(exp):
    assert isinstance(exp, Element), "{0!r} is not of type Element".format(exp)
    #print("exp={0!r}".format(exp))
    return unicode(exp)

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
        ret = op_expression.parseString(test)
        #print(repr(ret))
        fmt = format(ret[0])
        print("=================: " + fmt)
        ret2 = op_expression.parseString(fmt)
        fmt2 = format(ret2[0])
        assert fmt == fmt2, "Results don't match:\n 1. {0}\n 2. {1}".format(fmt, fmt2)
    except ParseException as ex:
        print("Error:" + str(ex))
