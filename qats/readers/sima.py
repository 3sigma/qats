import fnmatch
import os
import re
from struct import unpack
import numpy as np


def read_keys(path):
    """
    Read key-files associated with .bin and .asc time-series files exported from SIMA/RIFLEX Dynmod.

    Parameters
    ----------
    path : str
        Keyfile path

    Returns
    -------
    list
        List of key entries on key-file.

    Warnings
    --------
    This function is under development, and does not presently handle all
    kinds of response listings. If an unknown response description is
    encountered, the key suffix will be `DOF<xx>`.

    """
    # Line id. for pure digit line entries
    linid = 'Lin'
    # zero padding width
    nlin = 2
    nseg = 3
    nnod = 3  # for elements/nodes

    # extract 'noddis', 'elmsfo', 'elmfor' (asc), ...
    keyfiletype = os.path.splitext(path.split('_')[-1])[0].lower()

    # open and read
    with open(path, 'r') as f:
        lines = f.readlines()

    # define parameters
    if keyfiletype == 'noddis':
        elkey = 'No'
    elif keyfiletype in ('elmsfo', 'elmfor'):
        elkey = 'El'
    else:
        elkey = ''
    suffices = _riflex_key_suffices(lines)

    # find start line for storage information
    i_start = 1 + lines.index(fnmatch.filter(lines, "*------------------------------------------------------*")[0])
    # extract storage info lines
    p = re.compile(r'ignore*')
    key_lines = [l for l in lines[i_start:] if l.strip() and not p.search(l)]

    # determine number of keys on each line, and in total
    nkeys = [int(line.split()[3]) for line in key_lines]
    nkeystot = sum(nkeys)

    # parse keys
    keys = [''] * nkeystot
    i = 0
    for nk, kl in zip(nkeys, key_lines):
        l = kl.split()
        # Line id.
        if l[0].isdigit():
            a = linid + str(l[0]).zfill(nlin)
        else:
            a = l[0]
        # Segment id.
        b = 'Seg' + str(l[1]).zfill(nseg)
        # El./Node id.
        c = elkey + str(l[2]).zfill(nnod)
        # define key entries
        for suff in suffices[:nk]:
            keys[i] = '_'.join([a, b, c, suff])
            i += 1
    return keys


def read_bin_data(path, ind=None, verbose=False):
    """
    Read binary .bin time-series file from RIFLEX Dynmod.

    Parameters
    ----------
    path : str
        Name of the binary file (incl. extension).
    ind : list of integers, optional
        Defines which responses to include in returned array. Each of the indices in `ind` refer the sequence number
        of the reponses. Note that `0` is the index of the time array.
    verbose : bool, optional
        Write info to screen?

    Returns
    -------
    array
        Array with time and responses.

    Notes
    -----
    If ``ind`` is specified, time array is only included if `0` is included in the specified indices.

    If ``ind`` is specified, the response arrays (1-D) are stored in the returned 2-D array in the same order as
    specified. I.e. if ``ind=[0,10,2,3]``, then the response array with index `10` on .ts file is obtained from
    ``arr[1,:]``.

    """
    if verbose:
        print('Reading %s ...' % path)

    # read
    nbytes = 4
    intfmt = 'i'  # integer format
    with open(path, 'rb') as f:
        # parse no. of records
        nbytesrec = unpack('i', f.read(4))[0]
        nrec = int(nbytesrec / nbytes + 2)  # plus 2 due to first and last cols.
        nts = int(nrec - 2 - 1)             # no. time series (excl. time array)

        # parse no. of time steps
        f.seek(0, 2)                        # go to end
        nbytestot = f.tell()                # get position
        f.seek(0)                           # go back to start
        ndat = int(nbytestot / (nbytes * nrec))

        # which keys/indices to extract
        if ind is None:
            ind = range(nts + 1)            # (including time array)

        # info
        if verbose:
            print('---------------------------------------')
            print('nts (no. of responses on file) : %d' % nts)
            print('ndat (no. of time steps)       : %d' % ndat)
            print('number of keys to read         : %d  (%s)' % (len(ind), "including time array index 0 is specified"))

        # prepare for reading
        basefmt = intfmt + 'f' + 'f' * nts + intfmt
        fmt = basefmt * ndat
        # read, unpack, reshape and transpose (ignoring first and last row
        s = f.read(nbytestot)
        arr = np.array(unpack(fmt, s)).reshape((ndat, nrec))[:, 1:-1].T

    # return specified indices
    return arr[ind, :]


def read_ascii_data(path, ind=None, skiprows=None, verbose=False):
    """
    Read time series arranged column wise on ascii formatted file exported from SIMA/RIFLEX Dynmod.

    Parameters
    ----------
    path : str
        Name of the binary file (incl. extension).
    ind : list or tuple, optional
        Which columns to read, with 0 being the first. For example, usecols = (1,4,5) will extract the 2nd, 5th and
        6th columns. The default, None, results in all columns being read.
    skiprows : int, optional
        Skip the first `skiprows` lines; default: 0.
    verbose : bool, optional
        Write info to screen?

    Returns
    -------
    array
        Array with time and responses.

    Notes
    -----
    If ``ind`` is specified, time array is only included if `0` is included in the specified indices.

    If ``ind`` is specified, the response arrays (1-D) are stored in the returned 2-D array in the same order as
    specified. I.e. if ``ind=[0,10,2,3]``, then the response array with index `10` on ascii file is obtained from
    ``arr[1,:]``.

    """
    if verbose:
        print('Reading %s ...' % path)

    # read
    with open(path) as f:
        # skip commmented lines at start of file
        pos = f.tell()
        while True:
            line = f.readline()
            if not line:
                # reached EOF
                raise IOError("reached EOF - uncommented lines not found")
            if line.startswith("#"):
                pos = f.tell()
                continue
            f.seek(pos)
            break
        # load arrays
        arr = np.loadtxt(f, skiprows=skiprows, usecols=ind, unpack=True)

    # info
    if verbose:
        nts, ndat = arr.shape
        print('---------------------------------------')
        print('nts (no. of responses read) : %d' % nts)
        print('ndat (no. of time steps)    : %d' % ndat)

    return arr


def _riflex_key_suffices(txt):
    """
    Defines response key suffices.

    The response suffices, as e.g. "Te", "Mx1", etc. are based on parsing the RIFLEX DYNMOD key-file, more specifically
    the lines containing "DOF" information.

    Parameters
    ----------
    txt : list of strings
        Each string is the line of a key-file.

    Returns
    -------
    list
        The suffices, e.g. 'Xd', 'Yd', or 'Te', 'Sy1', 'Sy2', etc.
    """
    # extract indices for blocks with DOF descriptions
    p = re.compile("following applies")
    inds = [txt.index(line) for line in [line for line in txt if p.search(line)]]

    # Always choose the last block:
    #   If there are two blocks, the first will be bar elements, for which only the axial tension is stored.
    #   This dof will also be the first dof for beam elements, if there are any. Hence, only the last block needs
    #   to be parsed.
    ind = inds[-1]
    p = re.compile("DOF")
    # list of DOF (...) strings
    dofstrings = [line for line in txt[ind:] if p.search(line)]

    # extract DOF descriptions by splitting on '='
    dofdescr = [x.split('=')[-1].strip() for x in dofstrings]

    # define suffices
    suffices = [''] * len(dofdescr)
    for i, ds in enumerate(dofdescr):
        # displacements
        if re.match('displacement', ds):
            # extract direction : x, y, z
            suff = ds.split()[2].upper() + 'd'
        # forces, moments
        elif re.match('Axial', ds):
            suff = 'Te'
        elif re.match('Torsional', ds):
            suff = 'Mx'
        elif re.match('Mom.', ds):
            dsp = ds.split()
            suff = 'M'
            # which axis
            suff += fnmatch.filter(dsp, '*axis*')[0][0]
            # which end
            suff += str(dsp[-1])
        elif re.match('Shear', ds):
            dsp = ds.split()
            suff = 'S'
            # which axis
            suff += fnmatch.filter(dsp, '*direction*')[0][0]
            # which end
            suff += str(dsp[-1])

        else:  # unknown description, use DOFxx
            suff = 'DOF' + str(i + 1).zfill(2)

        suffices[i] = suff

    return suffices


