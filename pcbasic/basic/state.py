"""
PC-BASIC - state.py
Emulator state

(c) 2014, 2015, 2016 Rob Hagemans
This file is released under the GNU GPL version 3 or later.
"""

try:
    import cPickle as pickle
except ImportError:
    import pickle
try:
    import cStringIO
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import copy_reg
import os
import zlib
import logging
import Queue


class ResumeFailed(Exception):
    """Failed to resume session."""
    def __str__(self):
        return self.__doc__


def unpickle_file(name, mode, pos):
    """Unpickle a file object."""
    try:
        if 'w' in mode and pos > 0:
            # preserve existing contents of writable file
            with open(name, 'rb') as f:
                buf = f.read(pos)
            f = open(name, mode)
            f.write(buf)
        else:
            f = open(name, mode)
            if pos > 0:
                f.seek(pos)
    except IOError:
        logging.warning('Could not re-open file %s. Replacing with null file.', name)
        f = open(os.devnull, mode)
    return f

def pickle_file(f):
    """Pickle a file object."""
    try:
        return unpickle_file, (f.name, f.mode, f.tell())
    except IOError:
        # not seekable
        return unpickle_file, (f.name, f.mode, -1)

def unpickle_StringIO(value, pos):
    """Unpickle a cStringIO object."""
    # needs to be called without arguments or it's a StringI object without write()
    csio = StringIO()
    csio.write(value)
    csio.seek(pos)
    return csio

def pickle_StringIO(csio):
    """Pickle a cStringIO object."""
    value = csio.getvalue()
    pos = csio.tell()
    return unpickle_StringIO, (value, pos)

# register the picklers for file and cStringIO
copy_reg.pickle(file, pickle_file)
copy_reg.pickle(cStringIO.OutputType, pickle_StringIO)


def unpickle_Queue(self, dummy):
    """Dummy unpickler for Queue."""
    return Queue.Queue()

def pickle_Queue(self):
    """Dummy pickler for queue - nothing is saved except the type."""
    return None

# copy_reg does not work with old-style classes, so we inject pickling methods
Queue.Queue.__setstate__ = unpickle_Queue
Queue.Queue.__getstate__ = pickle_Queue


def save(session, state_file):
    """Save emulator state to file."""
    if not state_file:
        return
    # pickle and compress
    try:
        with open(state_file, 'wb') as f:
            f.write(zlib.compress(pickle.dumps(session, 2)))
    except EnvironmentError:
        logging.warning("Could not write to state file %s. Emulator state not saved.", state_file)

def load(state_file):
    """Load emulator state from file."""
    if not state_file:
        raise ResumeFailed()
    # decompress and unpickle
    try:
        with open(state_file, 'rb') as f:
            return pickle.loads(zlib.decompress(f.read()))
    except EnvironmentError:
        logging.warning("Could not read state file %s. Emulator state not loaded.", state_file)
        raise ResumeFailed()
