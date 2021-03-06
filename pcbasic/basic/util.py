"""
PC-BASIC - util.py
Token stream utilities

(c) 2013, 2014, 2015, 2016 Rob Hagemans
This file is released under the GNU GPL version 3 or later.
"""

from functools import partial
import string

from . import error
from . import vartypes
from . import basictoken as tk

###############################################################################
# stream utilities

def peek(ins, n=1):
    """Peek next char in stream."""
    d = ins.read(n)
    ins.seek(-len(d), 1)
    return d

def skip_read(ins, skip_range, n=1):
    """Skip chars in skip_range, then read next."""
    while True:
        d = ins.read(1)
        # skip_range must not include ''
        if d == '' or d not in skip_range:
            return d + ins.read(n-1)

def skip(ins, skip_range, n=1):
    """Skip chars in skip_range, then peek next."""
    d = skip_read(ins, skip_range, n)
    ins.seek(-len(d), 1)
    return d

def backskip_white(ins):
    """Skip whitespace backwards, then peek next."""
    while True:
        ins.seek(-1, 1)
        d = peek(ins)
        # skip_range must not include ''
        if d == '' or d not in tk.whitespace:
            return d

# skip whitespace, then read next
skip_white_read = partial(skip_read, skip_range=tk.whitespace)
# skip whitespace, then peek next
skip_white = partial(skip, skip_range=tk.whitespace)

def skip_white_read_if(ins, in_range):
    """Skip whitespace, then read if next char is in range."""
    return read_if(ins, skip_white(ins, n=len(in_range[0])), in_range)

def read_if(ins, d, in_range):
    """Read if next char is in range."""
    if d != '' and d in in_range:
        ins.read(len(d))
        return True
    return False

def skip_to(ins, findrange, break_on_first_char=True):
    """Skip until character is in findrange."""
    literal = False
    rem = False
    while True:
        c = ins.read(1)
        if c == '':
            break
        elif c == '"':
            literal = not literal
        elif c == tk.REM:
            rem = True
        elif c == '\0':
            literal = False
            rem = False
        if literal or rem:
            continue
        if c in findrange:
            if break_on_first_char:
                ins.seek(-1, 1)
                break
            else:
                break_on_first_char = True
        # not elif! if not break_on_first_char, c needs to be properly processed.
        if c == '\0':  # offset and line number follow
            literal = False
            off = ins.read(2)
            if len(off) < 2 or off == '\0\0':
                break
            ins.read(2)
        elif c in tk.plus_bytes:
            ins.read(tk.plus_bytes[c])

def skip_to_read(ins, findrange):
    """Skip until character is in findrange, then read."""
    skip_to(ins, findrange)
    return ins.read(1)

###############################################################################
# parsing utilities

def require_read(ins, in_range, err=error.STX):
    """Skip whitespace, read and raise error if not in range."""
    if not skip_white_read_if(ins, in_range):
        raise error.RunError(err)

def require(ins, rnge, err=error.STX):
    """Skip whitespace, peek and raise error if not in range."""
    a = skip_white(ins, n=len(rnge[0]))
    if a not in rnge:
        raise error.RunError(err)

def parse_line_number(ins):
    """Parse line number and leave pointer at first char of line."""
    # if end of program or truncated, leave pointer at start of line number C0 DE or 00 00
    off = ins.read(2)
    if off == '\0\0' or len(off) < 2:
        ins.seek(-len(off), 1)
        return -1
    off = ins.read(2)
    if len(off) < 2:
        ins.seek(-len(off)-2, 1)
        return -1
    else:
        return vartypes.integer_to_int_unsigned(vartypes.bytes_to_integer(off))

def parse_jumpnum(ins, allow_empty=False, err=error.STX):
    """Parses a line number pointer as in GOTO, GOSUB, LIST, RENUM, EDIT, etc."""
    if skip_white_read_if(ins, (tk.T_UINT,)):
        return vartypes.integer_to_int_unsigned(vartypes.bytes_to_integer(ins.read(2)))
    else:
        if allow_empty:
            return -1
        # Syntax error
        raise error.RunError(err)

def read_name(ins, allow_empty=False, err=error.STX):
    """Read a variable name """
    name = ''
    d = skip_white_read(ins)
    if not d:
        pass
    elif d not in string.ascii_letters:
        # variable name must start with a letter
        ins.seek(-len(d), 1)
    else:
        while d and d in tk.name_chars:
            name += d
            d = ins.read(1)
        if d in vartypes.sigils:
            name += d
        else:
            ins.seek(-len(d), 1)
    if not name and not allow_empty:
        raise error.RunError(err)
    return name

def range_check(lower, upper, *allvars):
    """Check if all variables in list are within the given inclusive range."""
    for v in allvars:
        if v is not None and not (lower <= v <= upper):
            raise error.RunError(error.IFC)

def range_check_err(lower, upper, v, err=error.IFC):
    """Check if variable is within the given inclusive range."""
    if v is not None and not (lower <= v <= upper):
        raise error.RunError(err)
