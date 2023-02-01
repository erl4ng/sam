import scipy.sparse
import pytest
import os
import math
import torch
from sam.onyx.generate_matrices import *

from sam.sim.src.base import *
from sam.sim.test.test import *

KDIM = 256

cwd = os.getcwd()
ss_formatted_dir = os.getenv('SUITESPARSE_FORMATTED_PATH', default=os.path.join(cwd, 'mode-formats'))
frostt_dir = os.getenv('FROSTT_PATH', default=os.path.join(cwd, 'mode-formats'))
validate_dir = os.getenv('VALIDATION_OUTPUT_PATH', default=os.path.join(cwd, 'mode-formats'))

tnsLoader = TnsFileLoader(False)


def _shiftLastMode(tensor):
    dok = scipy.sparse.dok_matrix(tensor)
    result = scipy.sparse.dok_matrix(tensor.shape)
    for coord, val in dok.items():
        newCoord = list(coord[:])
        newCoord[-1] = (newCoord[-1] + 1) % tensor.shape[-1]
        # result[tuple(newCoord)] = val
        # TODO (rohany): Temporarily use a constant as the value.
        result[tuple(newCoord)] = 2
    return scipy.sparse.coo_matrix(result)


def check_gold_matmul(ssname, debug_sim, out_crds, out_segs, out_val, out_format="ss01"):
    # CSR
    B_dirname = os.path.join(ss_formatted_dir, ssname, "orig", "ds01")
    B_shape_filename = os.path.join(B_dirname, "B_shape.txt")
    B_shape = read_inputs(B_shape_filename)

    B1_seg_filename = os.path.join(B_dirname, "B1_seg.txt")
    B1_seg = read_inputs(B1_seg_filename)
    B1_crd_filename = os.path.join(B_dirname, "B1_crd.txt")
    B1_crd = read_inputs(B1_crd_filename)

    B_vals_filename = os.path.join(B_dirname, "B_vals.txt")
    B_vals = read_inputs(B_vals_filename, float)

    # CSC
    C_dirname = os.path.join(ss_formatted_dir, ssname, "shift-trans", "ds10")
    C_shape_filename = os.path.join(C_dirname, "C_shape.txt")
    C_shape = read_inputs(C_shape_filename)

    C0_seg_filename = os.path.join(C_dirname, "C0_seg.txt")
    C0_seg = read_inputs(C0_seg_filename)
    C0_crd_filename = os.path.join(C_dirname, "C0_crd.txt")
    C0_crd = read_inputs(C0_crd_filename)

    C_vals_filename = os.path.join(C_dirname, "C_vals.txt")
    C_vals = read_inputs(C_vals_filename, float)

    B_scipy = scipy.sparse.csr_matrix((B_vals, B1_crd, B1_seg), shape=B_shape)
    C_scipy = scipy.sparse.csc_matrix((C_vals, C0_crd, C0_seg), shape=C_shape)

    gold_nd = (B_scipy * C_scipy).toarray()
    transpose = out_format[-2:] == "10"
    if transpose:
        gold_nd = gold_nd.transpose()

    gold_tup = convert_ndarr_point_tuple(gold_nd)

    if debug_sim:
        print("Out segs:", out_segs)
        print("Out crds:", out_crds)
        print("Out vals:", out_val)
        print("Dense Mat1:\n", B_scipy.toarray())
        print("Dense Mat2:\n", C_scipy.toarray())
        print("Dense Gold:", gold_nd)
        print("Gold:", gold_tup)

    if not out_val:
        assert out_val == gold_tup
    elif not gold_tup:
        assert all([v == 0 for v in out_val])
    else:
        out_tup = convert_point_tuple(get_point_list(out_crds, out_segs, out_val))
        out_tup = remove_zeros(out_tup)
        if debug_sim:
            print("Out:", out_tup)
        assert (check_point_tuple(out_tup, gold_tup))


def check_gold_mat_elemmul(ssname, debug_sim, out_crds, out_segs, out_val, format_str):
    # CSR
    B_dirname = os.path.join(ss_formatted_dir, ssname, "orig", "ds01")
    B_shape_filename = os.path.join(B_dirname, "B_shape.txt")
    B_shape = read_inputs(B_shape_filename)

    B1_seg_filename = os.path.join(B_dirname, "B1_seg.txt")
    B1_seg = read_inputs(B1_seg_filename)
    B1_crd_filename = os.path.join(B_dirname, "B1_crd.txt")
    B1_crd = read_inputs(B1_crd_filename)

    B_vals_filename = os.path.join(B_dirname, "B_vals.txt")
    B_vals = read_inputs(B_vals_filename, float)

    # CSR
    C_dirname = os.path.join(ss_formatted_dir, ssname, "shift", "ds01")
    C_shape_filename = os.path.join(C_dirname, "C_shape.txt")
    C_shape = read_inputs(C_shape_filename)

    C1_seg_filename = os.path.join(C_dirname, "C1_seg.txt")
    C1_seg = read_inputs(C1_seg_filename)
    C1_crd_filename = os.path.join(C_dirname, "C1_crd.txt")
    C1_crd = read_inputs(C1_crd_filename)

    C_vals_filename = os.path.join(C_dirname, "C_vals.txt")
    C_vals = read_inputs(C_vals_filename, float)

    B_scipy = scipy.sparse.csr_matrix((B_vals, B1_crd, B1_seg), shape=B_shape)
    C_scipy = scipy.sparse.csr_matrix((C_vals, C1_crd, C1_seg), shape=C_shape)

    gold_nd = (B_scipy.multiply(C_scipy)).toarray()
    transpose = format_str[-2:] == "10"
    if transpose:
        gold_nd = gold_nd.transpose()

    gold_tup = convert_ndarr_point_tuple(gold_nd)

    if debug_sim:
        print("Dense Mat1:\n", B_scipy.toarray())
        print("Dense Mat2:\n", C_scipy.toarray())
        print("Dense Gold:", gold_nd)
        print("Gold:", gold_tup)

    if not out_val:
        assert out_val == gold_tup
    elif not gold_tup:
        assert all([v == 0 for v in out_val])
    else:
        out_tup = convert_point_tuple(get_point_list(out_crds, out_segs, out_val))
        out_tup = remove_zeros(out_tup)
        assert (check_point_tuple(out_tup, gold_tup))


def check_gold_mat_identity(ssname, debug_sim, out_crds, out_segs, out_val, format_str):
    B_dirname = os.path.join(ss_formatted_dir, ssname, "orig", "ds01")
    B_shape_filename = os.path.join(B_dirname, "B_shape.txt")
    B_shape = read_inputs(B_shape_filename)

    B1_seg_filename = os.path.join(B_dirname, "B1_seg.txt")
    B1_seg = read_inputs(B1_seg_filename)
    B1_crd_filename = os.path.join(B_dirname, "B1_crd.txt")
    B1_crd = read_inputs(B1_crd_filename)

    B_vals_filename = os.path.join(B_dirname, "B_vals.txt")
    B_vals = read_inputs(B_vals_filename, float)

    B_scipy = scipy.sparse.csr_matrix((B_vals, B1_crd, B1_seg), shape=B_shape)

    gold_nd = B_scipy.toarray()
    gold_tup = convert_ndarr_point_tuple(gold_nd)

    if debug_sim:
        print("Dense Mat1:\n", B_scipy.toarray())
        print("Dense Gold:", gold_nd)
        print("Gold:", gold_tup)

    if not out_val:
        assert out_val == gold_tup
    elif not gold_tup:
        assert all([v == 0 for v in out_val])
    else:
        out_tup = convert_point_tuple(get_point_list(out_crds, out_segs, out_val))
        out_tup = remove_zeros(out_tup)
        assert (check_point_tuple(out_tup, gold_tup))


def check_gold_mat_elemadd(ssname, debug_sim, out_crds, out_segs, out_val, format_str):
    # CSR
    B_dirname = os.path.join(ss_formatted_dir, ssname, "orig", "ds01")
    B_shape_filename = os.path.join(B_dirname, "B_shape.txt")
    B_shape = read_inputs(B_shape_filename)

    B1_seg_filename = os.path.join(B_dirname, "B1_seg.txt")
    B1_seg = read_inputs(B1_seg_filename)
    B1_crd_filename = os.path.join(B_dirname, "B1_crd.txt")
    B1_crd = read_inputs(B1_crd_filename)

    B_vals_filename = os.path.join(B_dirname, "B_vals.txt")
    B_vals = read_inputs(B_vals_filename, float)

    # CSR
    C_dirname = os.path.join(ss_formatted_dir, ssname, "shift", "ds01")
    C_shape_filename = os.path.join(C_dirname, "C_shape.txt")
    C_shape = read_inputs(C_shape_filename)

    C1_seg_filename = os.path.join(C_dirname, "C1_seg.txt")
    C1_seg = read_inputs(C1_seg_filename)
    C1_crd_filename = os.path.join(C_dirname, "C1_crd.txt")
    C1_crd = read_inputs(C1_crd_filename)

    C_vals_filename = os.path.join(C_dirname, "C_vals.txt")
    C_vals = read_inputs(C_vals_filename, float)

    B_scipy = scipy.sparse.csr_matrix((B_vals, B1_crd, B1_seg), shape=B_shape)
    C_scipy = scipy.sparse.csr_matrix((C_vals, C1_crd, C1_seg), shape=C_shape)

    gold_nd = (B_scipy + C_scipy).toarray()
    transpose = format_str[-2:] == "10"
    if transpose:
        gold_nd = gold_nd.transpose()

    gold_tup = convert_ndarr_point_tuple(gold_nd)

    if debug_sim:
        print("Out segs:", out_segs)
        print("Out crds:", out_crds)
        print("Out vals:", out_val)
        print("Dense Mat1:\n", B_scipy.toarray())
        print("Dense Mat2:\n", C_scipy.toarray())
        print("Dense Gold:", gold_nd)
        print("Gold:", gold_tup)

    if not out_val:
        assert out_val == gold_tup
    elif not gold_tup:
        assert all([v == 0 for v in out_val])
    else:
        out_tup = convert_point_tuple(get_point_list(out_crds, out_segs, out_val))
        out_tup = remove_zeros(out_tup)
        assert (check_point_tuple(out_tup, gold_tup))


def check_gold_mat_vecmul_ji(ssname, debug_sim, out_crds, out_segs, out_val, format_str):
    return check_gold_mat_vecmul(ssname, debug_sim, out_crds, out_segs, out_val, format_str)


def check_gold_mat_vecmul_ij(ssname, debug_sim, out_crds, out_segs, out_val, format_str):
    return check_gold_mat_vecmul(ssname, debug_sim, out_crds, out_segs, out_val, format_str)


def check_gold_mat_vecmul(ssname, debug_sim, out_crds, out_segs, out_val, format_str):
    # CSR
    B_dirname = os.path.join(ss_formatted_dir, ssname, "orig", "ds01")
    B_shape_filename = os.path.join(B_dirname, "B_shape.txt")
    B_shape = read_inputs(B_shape_filename)

    B1_seg_filename = os.path.join(B_dirname, "B1_seg.txt")
    B1_seg = read_inputs(B1_seg_filename)
    B1_crd_filename = os.path.join(B_dirname, "B1_crd.txt")
    B1_crd = read_inputs(B1_crd_filename)

    B_vals_filename = os.path.join(B_dirname, "B_vals.txt")
    B_vals = read_inputs(B_vals_filename, float)

    c_dirname = os.path.join(ss_formatted_dir, ssname, "other")
    c_fname = [f for f in os.listdir(c_dirname) if ssname + "-vec_mode1" in f]
    assert len(c_fname) == 1, "Should only have one 'other' folder that matches"
    c_fname = c_fname[0]
    c_dirname = os.path.join(c_dirname, c_fname)

    c_shape = B_shape[1]

    c0_seg_filename = os.path.join(c_dirname, "C0_seg.txt")
    c_seg0 = read_inputs(c0_seg_filename)
    c0_crd_filename = os.path.join(c_dirname, "C0_crd.txt")
    c_crd0 = read_inputs(c0_crd_filename)

    c_vals_filename = os.path.join(c_dirname, "C_vals.txt")
    c_vals = read_inputs(c_vals_filename, float)

    B_scipy = scipy.sparse.csr_matrix((B_vals, B1_crd, B1_seg), shape=B_shape)
    c_nd = np.zeros(c_shape)

    for i in range(len(c_crd0)):
        val = c_vals[i]
        crd = c_crd0[i]
        c_nd[crd] = val

    gold_nd = (B_scipy @ c_nd)
    transpose = format_str[-2:] == "10"
    if transpose:
        gold_nd = gold_nd.transpose()

    gold_tup = convert_ndarr_point_tuple(gold_nd)

    if debug_sim:
        print("Out segs:", out_segs)
        print("Out crds:", out_crds)
        print("Out vals:", out_val)
        print("Dense Mat1:\n", B_scipy.toarray())
        print("Dense Vec2:\n", c_nd)
        print("Dense Gold:", gold_nd)
        print("Gold:", gold_tup)

    if not out_val:
        assert out_val == gold_tup
    elif not gold_tup:
        assert all([v == 0 for v in out_val])
    else:
        out_tup = convert_point_tuple(get_point_list(out_crds, out_segs, out_val))
        out_tup = remove_zeros(out_tup)
        assert (check_point_tuple(out_tup, gold_tup))


def check_gold_mat_sddmm(ssname, debug_sim, out_crds, out_segs, out_val, format_str):
    B_dirname = os.path.join(ss_formatted_dir, ssname, "orig", "ds01")
    B_shape_filename = os.path.join(B_dirname, "B_shape.txt")
    B_shape = read_inputs(B_shape_filename)

    B1_seg_filename = os.path.join(B_dirname, "B1_seg.txt")
    B1_seg = read_inputs(B1_seg_filename)
    B1_crd_filename = os.path.join(B_dirname, "B1_crd.txt")
    B1_crd = read_inputs(B1_crd_filename)

    B_vals_filename = os.path.join(B_dirname, "B_vals.txt")
    B_vals = read_inputs(B_vals_filename, float)

    C_shape = (B_shape[0], KDIM)
    C_vals = np.arange(math.prod(C_shape)).reshape(C_shape)

    D_shape = (KDIM, B_shape[1])
    D_vals = np.arange(math.prod(D_shape)).reshape(D_shape[::-1]).transpose()

    B_scipy = scipy.sparse.csr_matrix((B_vals, B1_crd, B1_seg), shape=B_shape)

    gold_nd = (B_scipy.multiply(C_vals @ D_vals)).toarray()
    transpose = format_str[-2:] == "10"
    if transpose:
        gold_nd = gold_nd.transpose()

    gold_tup = convert_ndarr_point_tuple(gold_nd)

    if debug_sim:
        print("Out segs:", out_segs)
        print("Out crds:", out_crds)
        print("Out vals:", out_val)
        print("Dense Mat1:\n", B_scipy.toarray())
        print("Dense Mat2:\n", C_vals)
        print("Dense Mat3:\n", D_vals)
        print("Dense Gold:", gold_nd)
        print("Gold:", gold_tup)

    if not out_val:
        assert out_val == gold_tup
    elif not gold_tup:
        assert all([v == 0 for v in out_val])
    else:
        out_tup = convert_point_tuple(get_point_list(out_crds, out_segs, out_val))
        out_tup = remove_zeros(out_tup)
        if debug_sim:
            print("Out:", out_tup)
        assert (check_point_tuple(out_tup, gold_tup))


def check_gold_mat_residual(ssname, debug_sim, out_crds, out_segs, out_val, format_str):
    # CSR
    B_dirname = os.path.join(ss_formatted_dir, ssname, "orig", "ds01")
    B_shape_filename = os.path.join(B_dirname, "B_shape.txt")
    B_shape = read_inputs(B_shape_filename)

    B1_seg_filename = os.path.join(B_dirname, "B1_seg.txt")
    B1_seg = read_inputs(B1_seg_filename)
    B1_crd_filename = os.path.join(B_dirname, "B1_crd.txt")
    B1_crd = read_inputs(B1_crd_filename)

    B_vals_filename = os.path.join(B_dirname, "B_vals.txt")
    B_vals = read_inputs(B_vals_filename, float)

    b_dirname = os.path.join(ss_formatted_dir, ssname, "other")
    b_fname = [f for f in os.listdir(b_dirname) if ssname + "-vec_mode0" in f]
    assert len(b_fname) == 1, "Should only have one 'other' folder that matches"
    b_fname = b_fname[0]
    b_dirname = os.path.join(b_dirname, b_fname)

    b_shape = B_shape[0]

    b0_crd_filename = os.path.join(b_dirname, "C0_crd.txt")
    b_crd0 = read_inputs(b0_crd_filename)

    b_vals_filename = os.path.join(b_dirname, "C_vals.txt")
    b_vals = read_inputs(b_vals_filename, float)

    c_dirname = os.path.join(ss_formatted_dir, ssname, "other")
    c_fname = [f for f in os.listdir(c_dirname) if ssname + "-vec_mode1" in f]
    assert len(c_fname) == 1, "Should only have one 'other' folder that matches"
    c_fname = c_fname[0]
    c_dirname = os.path.join(c_dirname, c_fname)

    c_shape = B_shape[1]

    c0_crd_filename = os.path.join(c_dirname, "C0_crd.txt")
    c_crd0 = read_inputs(c0_crd_filename)

    c_vals_filename = os.path.join(c_dirname, "C_vals.txt")
    c_vals = read_inputs(c_vals_filename, float)

    B_scipy = scipy.sparse.csr_matrix((B_vals, B1_crd, B1_seg), shape=B_shape)
    c_nd = np.zeros(c_shape)
    b_nd = np.zeros(b_shape)

    for i in range(len(c_crd0)):
        val = c_vals[i]
        crd = c_crd0[i]
        c_nd[crd] = val

    for i in range(len(b_crd0)):
        val = b_vals[i]
        crd = b_crd0[i]
        b_nd[crd] = val

    gold_nd = b_nd - (B_scipy @ c_nd)
    transpose = format_str[-2:] == "10"
    if transpose:
        gold_nd = gold_nd.transpose()

    gold_tup = convert_ndarr_point_tuple(gold_nd)

    if debug_sim:
        print("Out segs:", out_segs)
        print("Out crds:", out_crds)
        print("Out vals:", out_val)
        print("Dense Vec1:\n", b_nd)
        print("Dense Mat1:\n", B_scipy.toarray())
        print("Dense Vec2:\n", c_nd)
        print("Dense Gold:", gold_nd)
        print("Gold:", gold_tup)

    if not out_val:
        assert out_val == gold_tup
    elif not gold_tup:
        assert all([v == 0 for v in out_val])
    else:
        out_tup = convert_point_tuple(get_point_list(out_crds, out_segs, out_val))
        out_tup = remove_zeros(out_tup)
        assert (check_point_tuple(out_tup, gold_tup))


def check_gold_mat_mattransmul(ssname, debug_sim, out_crds, out_segs, out_val, format_str):
    # CSR
    B_dirname = os.path.join(ss_formatted_dir, ssname, "orig", "ds01")
    B_shape_filename = os.path.join(B_dirname, "B_shape.txt")
    B_shape = read_inputs(B_shape_filename)

    B1_seg_filename = os.path.join(B_dirname, "B1_seg.txt")
    B1_seg = read_inputs(B1_seg_filename)
    B1_crd_filename = os.path.join(B_dirname, "B1_crd.txt")
    B1_crd = read_inputs(B1_crd_filename)

    B_vals_filename = os.path.join(B_dirname, "B_vals.txt")
    B_vals = read_inputs(B_vals_filename, float)

    b_dirname = os.path.join(ss_formatted_dir, ssname, "other")
    b_fname = [f for f in os.listdir(b_dirname) if ssname + "-vec_mode1" in f]
    assert len(b_fname) == 1, "Should only have one 'other' folder that matches"
    b_fname = b_fname[0]
    b_dirname = os.path.join(b_dirname, b_fname)

    b_shape = B_shape[1]

    b0_crd_filename = os.path.join(b_dirname, "C0_crd.txt")
    b_crd0 = read_inputs(b0_crd_filename)

    b_vals_filename = os.path.join(b_dirname, "C_vals.txt")
    b_vals = read_inputs(b_vals_filename, float)

    c_dirname = os.path.join(ss_formatted_dir, ssname, "other")
    c_fname = [f for f in os.listdir(c_dirname) if ssname + "-vec_mode0" in f]
    assert len(c_fname) == 1, "Should only have one 'other' folder that matches"
    c_fname = c_fname[0]
    c_dirname = os.path.join(c_dirname, c_fname)

    c_shape = B_shape[0]

    c0_crd_filename = os.path.join(c_dirname, "C0_crd.txt")
    c_crd0 = read_inputs(c0_crd_filename)

    c_vals_filename = os.path.join(c_dirname, "C_vals.txt")
    c_vals = read_inputs(c_vals_filename, float)

    s1 = 2
    s2 = 2

    B_scipy = scipy.sparse.csr_matrix((B_vals, B1_crd, B1_seg), shape=B_shape)
    c_nd = np.zeros(c_shape)
    b_nd = np.zeros(b_shape)

    for i in range(len(c_crd0)):
        val = c_vals[i]
        crd = c_crd0[i]
        c_nd[crd] = val

    for i in range(len(b_crd0)):
        val = b_vals[i]
        crd = b_crd0[i]
        b_nd[crd] = val

    gold_nd = s1 * B_scipy.T @ c_nd + s2 * b_nd
    transpose = format_str[-2:] == "10"
    if transpose:
        gold_nd = gold_nd.transpose()

    gold_tup = convert_ndarr_point_tuple(gold_nd)

    if debug_sim:
        print("Out segs:", out_segs)
        print("Out crds:", out_crds)
        print("Out vals:", out_val)
        print("Dense Vec1:\n", b_nd)
        print("Dense Mat1:\n", B_scipy.transpose().toarray())
        print("Dense Vec2:\n", c_nd)
        print("Dense Gold:", gold_nd)
        print("Gold:", gold_tup)

    if not out_val:
        assert out_val == gold_tup
    elif not gold_tup:
        assert all([v == 0 for v in out_val])
    else:
        out_tup = convert_point_tuple(get_point_list(out_crds, out_segs, out_val))
        out_tup = remove_zeros(out_tup)
        assert (check_point_tuple(out_tup, gold_tup))


def check_gold_mat_elemadd3(ssname, debug_sim, out_crds, out_segs, out_val, format_str):
    # CSR
    B_dirname = os.path.join(ss_formatted_dir, ssname, "orig", "ds01")
    B_shape_filename = os.path.join(B_dirname, "B_shape.txt")
    B_shape = read_inputs(B_shape_filename)

    B1_seg_filename = os.path.join(B_dirname, "B1_seg.txt")
    B1_seg = read_inputs(B1_seg_filename)
    B1_crd_filename = os.path.join(B_dirname, "B1_crd.txt")
    B1_crd = read_inputs(B1_crd_filename)

    B_vals_filename = os.path.join(B_dirname, "B_vals.txt")
    B_vals = read_inputs(B_vals_filename, float)

    C_dirname = os.path.join(ss_formatted_dir, ssname, "shift", "ds01")
    C_shape_filename = os.path.join(C_dirname, "C_shape.txt")
    C_shape = read_inputs(C_shape_filename)

    C1_seg_filename = os.path.join(C_dirname, "C1_seg.txt")
    C_seg1 = read_inputs(C1_seg_filename)
    C1_crd_filename = os.path.join(C_dirname, "C1_crd.txt")
    C_crd1 = read_inputs(C1_crd_filename)

    C_vals_filename = os.path.join(C_dirname, "C_vals.txt")
    C_vals = read_inputs(C_vals_filename, float)

    D_shape = C_shape

    D_seg1 = copy.deepcopy(C_seg1)
    D_crd1 = copy.deepcopy(C_crd1)
    # Shift by one again
    D_crd1 = [x + 1 if (x + 1) < D_shape[1] else 0 for x in D_crd1]
    D_vals = copy.deepcopy(C_vals)

    B_scipy = scipy.sparse.csr_matrix((B_vals, B1_crd, B1_seg), shape=B_shape)
    C_scipy = _shiftLastMode(B_scipy)
    D_scipy = _shiftLastMode(C_scipy)

    C2_scipy = scipy.sparse.csr_matrix((C_vals, C_crd1, C_seg1), shape=C_shape)
    D2_scipy = scipy.sparse.csr_matrix((D_vals, D_crd1, D_seg1), shape=D_shape)

    assert np.array_equal(C_scipy.toarray(), C2_scipy.toarray())
    assert np.array_equal(D_scipy.toarray(), D2_scipy.toarray())

    gold_nd = (B_scipy + C_scipy + D_scipy).toarray()
    transpose = format_str[-2:] == "10"
    if transpose:
        gold_nd = gold_nd.transpose()

    gold_tup = convert_ndarr_point_tuple(gold_nd)

    if debug_sim:
        print("Out segs:", out_segs)
        print("Out crds:", out_crds)
        print("Out vals:", out_val)
        print("Dense Mat1:\n", B_scipy.toarray())
        print("Dense Mat2:\n", C_scipy.toarray())
        print("Dense Gold:", gold_nd)
        print("Gold:", gold_tup)

    if not out_val:
        assert out_val == gold_tup
    elif not gold_tup:
        assert all([v == 0 for v in out_val])
    else:
        out_tup = convert_point_tuple(get_point_list(out_crds, out_segs, out_val))
        out_tup = remove_zeros(out_tup)
        assert (check_point_tuple(out_tup, gold_tup))


def check_gold_tensor3_elemadd(frosttname, debug_sim, out_crds, out_segs, out_val, format_str):
    validation_path = os.path.join(validate_dir, "frostt-taco", frosttname + "-plus2-taco.tns")
    dims, coordinates, vals = tnsLoader.load(validation_path)
    coordinates.append(vals)
    gold_tup = convert_point_tuple(coordinates)
    if not out_val:
        assert out_val == gold_tup
    elif not gold_tup:
        assert all([v == 0 for v in out_val])
    else:
        out_tup = convert_point_tuple(get_point_list(out_crds, out_segs, out_val))
        out_tup = remove_zeros(out_tup)
        assert (check_point_tuple(out_tup, gold_tup))


def check_gold_tensor3_ttv(frosttname, debug_sim, out_crds, out_segs, out_val, format_str):
    validation_path = os.path.join(validate_dir, "frostt-taco", frosttname + "-ttv-taco.tns")
    dims, coordinates, vals = tnsLoader.load(validation_path)
    coordinates.append(vals)
    gold_tup = convert_point_tuple(coordinates)
    print(out_segs)
    print(out_crds)
    print(out_val)
    if not out_val:
        assert out_val == gold_tup
    elif not gold_tup:
        assert all([v == 0 for v in out_val])
    else:
        out_tup = convert_point_tuple(get_point_list(out_crds, out_segs, out_val))
        out_tup = remove_zeros(out_tup)
        assert (check_point_tuple(out_tup, gold_tup))


def check_gold_tensor3_ttm(frosttname, debug_sim, out_crds, out_segs, out_val, format_str):
    validation_path = os.path.join(validate_dir, "frostt-taco", frosttname + "-ttm-taco.tns")
    dims, coordinates, vals = tnsLoader.load(validation_path)
    coordinates.append(vals)
    gold_tup = convert_point_tuple(coordinates)
    print("GOLD:", gold_tup)
    if not out_val:
        assert out_val == gold_tup
    elif not gold_tup:
        assert all([v == 0 for v in out_val])
    else:
        out_tup = convert_point_tuple(get_point_list(out_crds, out_segs, out_val))
        out_tup = remove_zeros(out_tup)
        assert (check_point_tuple(out_tup, gold_tup))


def check_gold_tensor3_innerprod(frosttname, debug_sim, out_crds, out_segs, out_val, format_str):
    if frosttname == "fb1k":
        assert out_val == [1066.0]
    else:
        assert False, "Gold not entered yet"


def check_gold_tensor3_mttkrp(frosttname, debug_sim, out_crds, out_segs, out_val, format_str):
    validation_path = os.path.join(validate_dir, "frostt-taco", frosttname + "-mttkrp-taco.tns")
    dims, coordinates, vals = tnsLoader.load(validation_path)
    coordinates.append(vals)
    gold_tup = convert_point_tuple(coordinates)
    print("GOLD:", gold_tup)
    if not out_val:
        assert out_val == gold_tup
    elif not gold_tup:
        assert all([v == 0 for v in out_val])
    else:
        out_tup = convert_point_tuple(get_point_list(out_crds, out_segs, out_val))
        out_tup = remove_zeros(out_tup)
        assert (check_point_tuple(out_tup, gold_tup))


def remove_items(test_list, item):
 
    # using filter() + __ne__ to perform the task
    res = list(filter((item).__ne__, test_list))
 
    return res




def check_gold_tensor3_linear(frosttname, debug_sim, out_crds, out_segs, out_vals, format_str):
    formatted_dir = os.getenv('FROSTT_FORMATTED_PATH', default=os.path.join(cwd, 'mode-formats'))
    B_dirname = os.path.join(formatted_dir, frosttname, "orig", "ss01")
    C_dirname = os.path.join(formatted_dir, frosttname, "other", "sss021")
    D_dirname = os.path.join(formatted_dir, frosttname, "other", "s0")
    B_shape_filename = os.path.join(B_dirname, "B_shape.txt")
    B_shape = read_inputs(B_shape_filename)
    C_shape_filename = os.path.join(C_dirname, "C_shape.txt")
    C_shape = read_inputs(C_shape_filename)
    D_shape_filename = os.path.join(D_dirname, "D_shape.txt")
    D_shape = read_inputs(D_shape_filename)
    B_tens = get_tensor_from_files(name="B", files_dir=B_dirname, shape=B_shape, base=10, early_terminate='x')
    C_tens = get_tensor_from_files(name="C", files_dir=C_dirname, shape=C_shape, base=10, early_terminate='x')
    D_tens = get_tensor_from_files(name="D", files_dir=D_dirname, shape=D_shape, base=10, early_terminate='x')
    # B_dirname_trans = os.path.join(formatted_dir, frosttname, "orig", "ssss0213")
    # C_dirname_trans = os.path.join(formatted_dir, frosttname, "other", "sss021")
    # mode = (0,2,1)
    # B_tens.transpose_tensor(mode)
    # C_tens.transpose_tensor(mode)
    # B_tens.set_dump_dir(B_dirname_trans)
    # C_tens.set_dump_dir(C_dirname_trans)

    # B_tens.dump_outputs(format='CSF')
    # C_tens.dump_outputs(format='CSF')

    # pytest.set_trace()

    # pytest.set_trace()
    B_ref = torch.from_numpy(B_tens.get_matrix())
    C_ref = torch.from_numpy(C_tens.get_matrix())
    D_ref = torch.from_numpy(D_tens.get_matrix())
    # D_ref = torch.unsqueeze(D_ref, 0).unsqueeze(2)
    # D_ref = torch.broadcast_to(D_ref, (2, 10, 10))
    print(D_ref.shape)

    pytest.set_trace()

    gold_ref = torch.einsum('jl, ilk->ijk', B_ref, C_ref)
    gold_tup = convert_ndarr_point_tuple(gold_ref.numpy())
    print("Before add: ", gold_tup)
    gold_ref = D_ref + gold_ref
    gold_ref = gold_ref.numpy()
    # gold_ref = torch.einsum('jl, ilk->ijk', B_ref, C_ref).numpy()

    mat_g = MatrixGenerator("gold", shape=gold_ref.shape, sparsity=0.1, format='CSF', dump_dir='test', tensor=gold_ref)
    mat_g.dump_outputs(format='CSF')
    gold_tup = convert_ndarr_point_tuple(gold_ref)
    print("After add: ", gold_tup)
    pytest.set_trace()
    # mg = create_matrix_from_point_list("gold", gold_tup, gold_ref.shape)
    # print(mg.get_matrix())
    print("Out crds:", out_crds)
    print()
    print("Out segs:", out_segs)
    print()
    print("Out vals:", out_vals)
    print(len(out_vals))
    print("sizes:", [len(arr) for arr in out_crds])
    print("sizes:", [len(arr) for arr in out_segs])
    print(gold_ref.shape)
    pytest.set_trace()

    if debug_sim:
        print("Out crds:", out_crds)
        print("Out segs:", out_segs)
        print("Out vals:", out_vals)
        print("Dense Gold:", gold_ref)
        print("Gold:", gold_tup)

    if not out_vals:
        assert out_vals == gold_tup
    elif not gold_tup:
        assert all([v == 0 for v in out_vals])
    else:
        out_tup = convert_point_tuple(get_point_list(out_crds, out_segs, out_vals))
        out_tup = remove_zeros(out_tup)
        print("ref:", out_tup)
        print("gold:", gold_tup)
        assert (check_point_tuple(out_tup, gold_tup))


def check_gold_tensor4_multiply(frosttname, debug_sim, out_crds, out_segs, out_vals, format_str):
    formatted_dir = os.getenv('FROSTT_FORMATTED_PATH', default=os.path.join(cwd, 'mode-formats'))
    B_dirname = os.path.join(formatted_dir, frosttname, "orig", "ssss0123")
    C_dirname = os.path.join(formatted_dir, frosttname, "other", "ssss0123")
    B_shape_filename = os.path.join(B_dirname, "B_shape.txt")
    B_shape = read_inputs(B_shape_filename)
    C_shape_filename = os.path.join(C_dirname, "C_shape.txt")
    C_shape = read_inputs(C_shape_filename)
    B_tens = get_tensor_from_files(name="B", files_dir=B_dirname, shape=B_shape, base=10, early_terminate='x')
    C_tens = get_tensor_from_files(name="C", files_dir=C_dirname, shape=C_shape, base=10, early_terminate='x')
    # B_dirname_trans = os.path.join(formatted_dir, frosttname, "orig", "ssss0213")
    # C_dirname_trans = os.path.join(formatted_dir, frosttname, "other", "sss021")
    # mode = (0,2,1)
    # B_tens.transpose_tensor(mode)
    # C_tens.transpose_tensor(mode)
    # B_tens.set_dump_dir(B_dirname_trans)
    # C_tens.set_dump_dir(C_dirname_trans)

    # B_tens.dump_outputs(format='CSF')
    # C_tens.dump_outputs(format='CSF')

    # pytest.set_trace()

    # pytest.set_trace()
    B_ref = torch.from_numpy(B_tens.get_matrix())
    C_ref = torch.from_numpy(C_tens.get_matrix())

    gold_ref = torch.einsum('ikjm, iljm->ijkl', B_ref, C_ref).numpy()

    mat_g = MatrixGenerator("gold", shape=gold_ref.shape, sparsity=0.1, format='CSF', dump_dir='test', tensor=gold_ref)
    mat_g.dump_outputs(format='CSF')
    gold_tup = convert_ndarr_point_tuple(gold_ref)
    # mg = create_matrix_from_point_list("gold", gold_tup, gold_ref.shape)
    # print(mg.get_matrix())
    print("Out crds:", out_crds)
    print()
    print("Out segs:", out_segs)
    print()
    print("Out vals:", out_vals)
    print(len(out_vals))
    print("sizes:", [len(arr) for arr in out_crds])
    print("sizes:", [len(arr) for arr in out_segs])
    print(gold_ref.shape)
    # pytest.set_trace()

    if debug_sim:
        print("Out crds:", out_crds)
        print("Out segs:", out_segs)
        print("Out vals:", out_vals)
        print("Dense Gold:", gold_ref)
        print("Gold:", gold_tup)

    if not out_vals:
        assert out_vals == gold_tup
    elif not gold_tup:
        assert all([v == 0 for v in out_vals])
    else:
        out_tup = convert_point_tuple(get_point_list(out_crds, out_segs, out_vals))
        out_tup = remove_zeros(out_tup)
        print("ref:", out_tup)
        print("gold:", gold_tup)
        assert (check_point_tuple(out_tup, gold_tup))


def check_gold_tensor4_multiply2(frosttname, debug_sim, out_crds, out_segs, out_vals, format_str):
    formatted_dir = os.getenv('FROSTT_FORMATTED_PATH', default=os.path.join(cwd, 'mode-formats'))
    B_dirname = os.path.join(formatted_dir, frosttname, "orig", "ssss0123")
    C_dirname = os.path.join(formatted_dir, frosttname, "other", "ssss0123")
    B_shape_filename = os.path.join(B_dirname, "B_shape.txt")
    B_shape = read_inputs(B_shape_filename)
    C_shape_filename = os.path.join(C_dirname, "C_shape.txt")
    C_shape = read_inputs(C_shape_filename)
    B_tens = get_tensor_from_files(name="B", files_dir=B_dirname, shape=B_shape, base=10, early_terminate='x')
    C_tens = get_tensor_from_files(name="C", files_dir=C_dirname, shape=C_shape, base=10, early_terminate='x')
    B_dirname_trans = os.path.join(formatted_dir, frosttname, "orig", "ssss0213")
    C_dirname_trans = os.path.join(formatted_dir, frosttname, "other", "ssss0231")
    # mode1 = (0,2,1,3)
    # mode2 = (0,2,3,1)
    # B_tens.transpose_tensor(mode1)
    # C_tens.transpose_tensor(mode2)
    # B_tens.set_dump_dir(B_dirname_trans)
    # C_tens.set_dump_dir(C_dirname_trans)

    # B_tens.dump_outputs(format='CSF')
    # C_tens.dump_outputs(format='CSF')

    # pytest.set_trace()

    # pytest.set_trace()
    B_ref = torch.from_numpy(B_tens.get_matrix())
    C_ref = torch.from_numpy(C_tens.get_matrix())

    print(B_ref.shape)
    print(C_ref.shape)
    pytest.set_trace()

    gold_ref = torch.einsum('ijkl, iljm->ikjm', B_ref, C_ref).numpy()

    mat_g = MatrixGenerator("gold", shape=gold_ref.shape, sparsity=0.1, format='CSF', dump_dir='test', tensor=gold_ref)
    mat_g.dump_outputs(format='CSF')
    gold_tup = convert_ndarr_point_tuple(gold_ref)
    # mg = create_matrix_from_point_list("gold", gold_tup, gold_ref.shape)
    # print(mg.get_matrix())
    print("Out crds:", out_crds)
    print()
    print("Out segs:", out_segs)
    print()
    print("Out vals:", out_vals)
    print(len(out_vals))
    print("sizes:", [len(arr) for arr in out_crds])
    print("sizes:", [len(arr) for arr in out_segs])
    print(gold_ref.shape)
    pytest.set_trace()

    if debug_sim:
        print("Out crds:", out_crds)
        print("Out segs:", out_segs)
        print("Out vals:", out_vals)
        print("Dense Gold:", gold_ref)
        print("Gold:", gold_tup)

    if not out_vals:
        assert out_vals == gold_tup
    elif not gold_tup:
        assert all([v == 0 for v in out_vals])
    else:
        out_tup = convert_point_tuple(get_point_list(out_crds, out_segs, out_vals))
        out_tup = remove_zeros(out_tup)
        print("ref:", out_tup)
        print("gold:", gold_tup)
        assert (check_point_tuple(out_tup, gold_tup))


# ---------------- OTHER CHECKS (TODO later) ---------------- #
def check_gold_tensor3_identity(frosttname, debug_sim, out_crds, out_segs, out_val, format_str):
    pass


def check_gold_tensor3_relu(frosttname, debug_sim, out_crds, out_segs, out_val, format_str):
    pass
