import renderapi
import numpy as np
import scipy.linalg


def test_affine_rot_90():
    am = renderapi.transform.AffineModel()
    # setup a 90 degree clockwise rotation
    points_in = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], np.float)
    points_out = np.array([[0, 0], [1, 0], [0, -1], [1, -1]], np.float)
    am.estimate(points_in, points_out)

    assert(np.abs(am.scale[0]-1.0) < .00001)
    assert(np.abs(am.scale[1]-1.0) < .00001)
    assert(np.abs(am.rotation + np.pi/2) < .000001)
    assert(np.abs(am.translation[0]) < .000001)
    assert(np.abs(am.translation[1]) < .000001)
    assert(np.abs(am.shear) < .000001)

    points = np.array([[20, 30], [1, 2], [10, -5], [-4, 3], [5.6, 2.3]])
    new_points = am.tform(points)

    old_points = am.inverse_tform(new_points)
    assert(np.sum(np.abs(points-old_points)) < (.0001*len(points.ravel())))

    am_inverse = renderapi.transform.AffineModel()
    am_inverse.estimate(points_out, points_in)

    identity = am.concatenate(am_inverse)
    assert(np.abs(identity.scale[0]-1.0) < .00001)
    assert(np.abs(identity.scale[1]-1.0) < .00001)
    assert(np.abs(identity.rotation) < .000001)
    assert(np.abs(identity.translation[0]) < .000001)
    assert(np.abs(identity.translation[1]) < .000001)
    assert(np.abs(identity.shear) < .000001)
    print(str(am))


def test_affine_random():
        am = renderapi.transform.AffineModel(M00=.9,
                                             M10=-0.2,
                                             M01=0.3,
                                             M11=.85,
                                             B0=245.3,
                                             B1=-234.1)

        points_in = np.random.rand(10, 2)
        points_out = am.tform(points_in)

        am_fit = renderapi.transform.AffineModel()
        am_fit.estimate(points_in, points_out)

        assert(np.sum(np.abs(am.M.ravel()-am_fit.M.ravel())) < (.001*6))


def test_invert_Affine():
    am = renderapi.transform.AffineModel(M00=.9,
                                         M10=-0.2,
                                         M01=0.3,
                                         M11=.85,
                                         B0=245.3,
                                         B1=-234.1)
    Iam = am.invert()
    assert(np.allclose(Iam.concatenate(am).M, np.eye(3)))
    assert(np.allclose(am.concatenate(Iam).M, np.eye(3)))


def test_Polynomial_estimation(use_numpy=False):
    if use_numpy:
        try:
            import builtins
        except ImportError:
            import __builtin__ as builtins
        realimport = builtins.__import__

        def noscipy_import(name, globals=None, locals=None,
                           fromlist=(), level=0):
            if 'scipy' in name:
                raise ImportError
            return realimport(name, globals, locals, fromlist, level)
        builtins.__import__ = noscipy_import
    reload(renderapi.transform)
    assert(renderapi.transform.svd is np.linalg.svd
           if use_numpy else renderapi.transform.svd is scipy.linalg.svd)

    # TODO now that import framework is good, do actual test

    if use_numpy:
        builtins.__import__ = realimport
    reload(renderapi.transform)
    assert(renderapi.transform.svd is scipy.linalg.svd)


def test_Polynomial_estimation_numpy():
    test_Polynomial_estimation(use_numpy=True)


def test_transformsum():
    pass
