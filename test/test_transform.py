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

    datastring = ('67572.7356991 0.972637082773 -0.0266434803369 '
                  '-3.08962731867E-06 3.52672451824E-06 1.36924119761E-07 '
                  '5446.85340052 0.0224047626583 0.961202608454 '
                  '-3.36753624487E-07 -8.97219078255E-07 -5.49854010072E-06')
    default_pt = renderapi.transform.Polynomial2DTransform(
        dataString=datastring)
    srcpts = np.random.rand(30, 2)
    dstpts = default_pt.tform(srcpts)
    derived_pt = renderapi.transform.Polynomial2DTransform(
        src=srcpts, dst=dstpts)
    assert(np.allclose(derived_pt.params, default_pt.params))

    if use_numpy:
        builtins.__import__ = realimport
    reload(renderapi.transform)
    assert(renderapi.transform.svd is scipy.linalg.svd)


def test_Polynomial_estimation_numpy():
    test_Polynomial_estimation(use_numpy=True)


def notatest_transformsum_polynomial_identity():
    # test not used currently in favor of more reproducible affine
    srcpts = np.random.rand(50, 2)
    am = renderapi.transform.AffineModel(M00=.9,
                                         M10=-0.2,
                                         M01=0.3,
                                         M11=.85,
                                         B0=245.3,
                                         B1=-234.1)
    invam = am.invert()

    datastring = ('67572.7356991 0.972637082773 -0.0266434803369 '
                  '-3.08962731867E-06 3.52672451824E-06 1.36924119761E-07 '
                  '5446.85340052 0.0224047626583 0.961202608454 '
                  '-3.36753624487E-07 -8.97219078255E-07 -5.49854010072E-06')
    pt = renderapi.transform.Polynomial2DTransform(
        dataString=datastring)
    ptest_dstpts = pt.tform(srcpts)
    invpt = renderapi.transform.Polynomial2DTransform(
        src=ptest_dstpts, dst=srcpts)

    tformlist = [am, [pt, invpt], invam]
    new_tform = renderapi.transform.estimate_transformsum(
        tformlist, src=srcpts)

    poly_identity = renderapi.transform.Polynomial2DTransform(
        identity=True).asorder(new_tform.order)
    assert all([i < 1e-3 for i in
                (new_tform.params[:, 0] - poly_identity.params[:, 0]).ravel()])

    assert np.allclose(
        new_tform.params[:, 1:-1],
        poly_identity.params[:, 1:-1], atol=1e-5)


def test_transformsum_affine_concatenate():
    srcpts = np.random.rand(50, 2)
    am1 = renderapi.transform.AffineModel(M00=.9,
                                          M10=-0.2,
                                          M01=0.3,
                                          M11=.85,
                                          B0=245.3,
                                          B1=-234.1)
    am2 = renderapi.transform.AffineModel(M00=.9,
                                          M10=-0.2,
                                          M01=0.3,
                                          M11=.85,
                                          B0=-100,
                                          B1=3)
    am3 = renderapi.transform.AffineModel(M00=1.9,
                                          M10=-0.2,
                                          M01=0.3,
                                          M11=1.85,
                                          B0=-25.3,
                                          B1=60.1)
    am4 = renderapi.transform.AffineModel(M00=.9,
                                          M10=-0.2,
                                          M01=0.3,
                                          M11=.85,
                                          B0=2.3,
                                          B1=100.1)

    tformlist = [am1, [[am2, am3], am4]]
    new_tform = renderapi.transform.estimate_transformsum(
        tformlist, src=srcpts)
    concat_tform = am4.concatenate(am3.concatenate(am2)).concatenate(am1)
    assert np.allclose(new_tform.M, concat_tform.M)
