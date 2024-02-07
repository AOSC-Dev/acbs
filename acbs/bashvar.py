#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import collections
import logging
import re
import subprocess
import tempfile
import warnings

import pyparsing as pp  # type: ignore

pp.ParserElement.enablePackrat()

re_variable = re.compile('^\\s*([a-zA-Z_][a-zA-Z0-9_]*)=')

whitespace = pp.White(ws=' \t').suppress().setName("whitespace")
optwhitespace = pp.Optional(whitespace).setName("optwhitespace")
comment = ('#' + pp.CharsNotIn('\n')).setName("comment")
integer = (pp.Word(pp.nums) | pp.Combine('-' + pp.Word(pp.nums)))

varname = pp.Word(pp.alphas + '_', pp.alphanums +
                  '_').setResultsName("varname")
# ${parameter/pattern/string}
substsafe = pp.CharsNotIn('/#%*?[}\'"`\\')

expansion_param = pp.Group(
    pp.Literal('$').setResultsName("expansion") +
    # we don't want to parse all the expansions
    ((
        pp.Literal('{').suppress() +
        varname +
        pp.Optional(
            (pp.Literal(':').setResultsName("exptype") + pp.Group(
                pp.Word(pp.nums) |
                (whitespace + pp.Combine('-' + pp.Word(pp.nums)))
            ).setResultsName("offset") +
                pp.Optional(pp.Literal(':') + integer.setResultsName("length")))
            ^ (pp.oneOf('/ // /# /%').setResultsName("exptype") +
                pp.Optional(substsafe.setResultsName("pattern") +
                            pp.Optional(pp.Literal('/') +
                                        pp.Optional(substsafe, '').setResultsName("string")))
               )
            ^ (pp.oneOf("# ## % %%").setResultsName("exptype") +
                pp.Optional(substsafe.setResultsName("pattern"))
               )
        ) +
        pp.Literal('}').suppress()
    ) | varname)
)

singlequote = pp.Group(
    pp.Literal("'").setResultsName("quote") +
    pp.Optional(pp.CharsNotIn("'"), '').setResultsName("value") +
    pp.Literal("'").suppress()
).setName("singlequote")
doublequote_escape = (
    (pp.Literal('\\').suppress() + pp.Word('$`"\\', exact=1)) |
    pp.Literal('\\\n').suppress()
)
doublequote = pp.Group(
    pp.Literal('"').setResultsName("quote") +
    pp.Group(pp.ZeroOrMore(
        doublequote_escape | expansion_param | pp.CharsNotIn('$`\\*"')
    )).setResultsName("value") +
    pp.Literal('"').suppress()
).setName("doublequote")

texttoken = (
    singlequote | doublequote | expansion_param |
    pp.CharsNotIn('~{}()$\'"`\\*?[] \t\n')
)
varvalue = pp.Group(pp.ZeroOrMore(texttoken)).setResultsName('varvalue')
varassign = (
    varname +
    (pp.Literal('=') | pp.Literal('+=')).setResultsName('operator') +
    varvalue
).setName('varassign').leaveWhitespace()

line = pp.Group(
    pp.lineStart + optwhitespace +
    pp.Optional(varassign) + optwhitespace +
    pp.Optional(comment).suppress() +
    pp.lineEnd.suppress()
).setName('line').leaveWhitespace()

bashvarfile = pp.ZeroOrMore(line)

ParseException = pp.ParseException


class VariableWarning(UserWarning):
    pass


class BashErrorWarning(UserWarning):
    pass


class ParseError(Exception):
    pass


def combine_value(tokens, variables):
    val = ''
    if tokens.get('quote') == '"':
        val += combine_value(tokens['value'], variables)
    elif tokens.get('quote') == "'":
        val += tokens['value']
    elif tokens.get('expansion') == '$':
        varname = tokens['varname']
        if varname in variables:
            var = variables[varname]
            exptype = tokens.get('exptype')
            if exptype is None:
                pass
            elif exptype == ':':
                if 'offset' in tokens:
                    offset = int(tokens['offset'][0].strip())
                    if 'length' in tokens:
                        length = int(tokens['length'])
                        if length >= 0:
                            var = var[offset:offset+length]
                        else:
                            var = var[offset:length]
                    else:
                        var = var[offset:]
            elif exptype[0] == '/':
                pattern = tokens.get('pattern', '')
                newstring = tokens.get('string', '')
                if exptype == '/':
                    var = var.replace(pattern, newstring, 1)
                elif exptype == '//':
                    var = var.replace(pattern, newstring)
                elif exptype == '/#':
                    if var.startswith(pattern):
                        var = newstring + var[len(pattern):]
                elif var.endswith(pattern):  # /%
                    var = var[:-len(pattern)] + newstring
            elif exptype[0] == '#':
                pattern = tokens.get('pattern', '')
                if var.startswith(pattern):
                    var = var[len(pattern):]
            elif exptype[0] == '%':
                pattern = tokens.get('pattern', '')
                if var.endswith(pattern):
                    var = var[:-len(pattern)]
            val += var
        else:
            warnings.warn('variable "%s" is undefined' %
                          varname, VariableWarning)
    else:
        for tok in tokens:
            if isinstance(tok, str):
                val += tok
            else:
                val += combine_value(tok, variables)
    return ''.join(val)


def eval_bashvar_literal(source):
    parsed = bashvarfile.parseString(source, parseAll=True)
    variables = collections.OrderedDict()
    for line in parsed:
        if not line:
            continue
        val = combine_value(line['varvalue'], variables)
        if line['operator'] == '=':
            variables[line['varname']] = val
        elif line['operator'] == '+=':
            if line['varname'] in variables:
                variables[line['varname']] += val
            else:
                warnings.warn(
                    'variable "%s" is undefined' % line['varname'], VariableWarning)
                variables[line['varname']] = val
    return variables


def uniq(seq):  # Dave Kirby
    # Order preserving
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]


def eval_bashvar_ext(source, filename=None):
    # we don't specify encoding here because the env will do.
    var = []
    stdin = []
    for ln in source.splitlines(True):
        match = re_variable.match(ln)
        if match:
            var.append(match.group(1))
        stdin.append(ln)
    stdin.append('\n')
    var = uniq(var)
    for v in var:
        # workaround variables containing newlines
        stdin.append('echo "${%s//$\'\\n\'/\\\\n}"\n' % v)
    with tempfile.TemporaryDirectory() as tmpdir:
        outs, errs = subprocess.Popen(
            ('bash', '-r'), cwd=tmpdir, env={},
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE).communicate(''.join(stdin).encode('utf-8'))
    if errs:
        warnings.warn(errs.decode('utf-8', 'backslashreplace').rstrip(),
                      BashErrorWarning)
    lines = [l.replace('\\n', '\n') for l in outs.decode('utf-8').splitlines()]
    if len(var) != len(lines) and not errs:
        warnings.warn('bash output not expected', BashErrorWarning)
    return collections.OrderedDict(zip(var, lines))


def eval_bashvar(source: str, filename=None, msg=False):
    with warnings.catch_warnings(record=True) as wns:
        try:
            ret = eval_bashvar_literal(source)
        except pp.ParseException:
            ret = eval_bashvar_ext(source)
        msgs = []
        for w in wns:
            if issubclass(w.category, VariableWarning):
                logging.debug('%s: %s', filename, w.message)
            elif issubclass(w.category, BashErrorWarning):
                msgs.append(str(w.message))
                logging.error('%s: %s', filename, w.message)
        if msg:
            return ret, '\n'.join(msgs) if msgs else None
        else:
            return ret


def read_bashvar(fp, filename=None, msg=False):
    return eval_bashvar(
        fp.read(), filename or getattr(fp, 'name', None), msg)
