import json
import renderapi
import numpy as np
import scipy.linalg
import rendersettings


def test_affine_rot_90():
    am = renderapi.transform.AffineModel()
    # setup a 90 degree clockwise rotation
    points_in = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], np.float)
    points_out = np.array([[0, 0], [1, 0], [0, -1], [1, -1]], np.float)
    am.estimate(points_in, points_out)

    assert(np.abs(am.scale[0] - 1.0) < .00001)
    assert(np.abs(am.scale[1] - 1.0) < .00001)
    assert(np.abs(am.rotation + np.pi / 2) < .000001)
    assert(np.abs(am.translation[0]) < .000001)
    assert(np.abs(am.translation[1]) < .000001)
    assert(np.abs(am.shear) < .000001)

    points = np.array([[20, 30], [1, 2], [10, -5], [-4, 3], [5.6, 2.3]])
    new_points = am.tform(points)

    old_points = am.inverse_tform(new_points)
    assert(np.sum(np.abs(points - old_points)) < (.0001 * len(points.ravel())))

    am_inverse = renderapi.transform.AffineModel()
    am_inverse.estimate(points_out, points_in)

    identity = am.concatenate(am_inverse)
    assert(np.abs(identity.scale[0] - 1.0) < .00001)
    assert(np.abs(identity.scale[1] - 1.0) < .00001)
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

    assert(np.sum(np.abs(am.M.ravel() - am_fit.M.ravel())) < (.001 * 6))


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


def test_load_polynomial():
    datastring = ('67572.7356991 0.972637082773 -0.0266434803369 '
                  '-3.08962731867E-06 3.52672451824E-06 1.36924119761E-07 '
                  '5446.85340052 0.0224047626583 0.961202608454 '
                  '-3.36753624487E-07 -8.97219078255E-07 -5.49854010072E-06')
    pt = renderapi.transform.Polynomial2DTransform(
        dataString=datastring)
    pt_dict = renderapi.transform.Polynomial2DTransform(json=pt.to_dict())
    pt_dataString = renderapi.transform.Polynomial2DTransform(
        dataString=pt.dataString)
    pt_params = renderapi.transform.Polynomial2DTransform(params=pt.params)
    assert (pt_dict.to_dict() == pt_dataString.to_dict() ==
            pt_params.to_dict() == pt.to_dict())


def test_Polynomial_from_affine():
    am1 = renderapi.transform.AffineModel(M00=.9,
                                          M10=-0.2,
                                          M01=0.3,
                                          M11=.85,
                                          B0=245.3,
                                          B1=-234.1)
    pt = renderapi.transform.Polynomial2DTransform.fromAffine(am1)
    pt_params_raveled = pt.params.ravel()
    assert pt.order == 1
    assert pt_params_raveled[0] == am1.B0
    assert pt_params_raveled[1] == am1.M00
    assert pt_params_raveled[2] == am1.M01
    assert pt_params_raveled[3] == am1.B1
    assert pt_params_raveled[4] == am1.M10
    assert pt_params_raveled[5] == am1.M11


def test_interpolated_transform():
    with open(rendersettings.INTERPOLATED_TRANSFORM_TILESPEC, 'r') as f:
        j = json.load(f)
    ts = renderapi.tilespec.TileSpec(json=j)
    it_ts = [tform for tform in ts.tforms
             if isinstance(
                 tform, renderapi.transform.InterpolatedTransform)][0]
    it_args = renderapi.transform.InterpolatedTransform(
        it_ts.a, it_ts.b, it_ts.lambda_)
    it_dd = renderapi.transform.InterpolatedTransform(
        json=it_ts.to_dict())

    assert (dict(it_args) == it_args.to_dict() == dict(it_ts) ==
            it_ts.to_dict() == dict(it_dd) == it_dd.to_dict())


def test_reference_transform():
    with open(rendersettings.REFERENCE_TRANSFORM_TILESPEC, 'r') as f:
        j = json.load(f)
    ts = renderapi.tilespec.TileSpec(json=j)
    ref_ts = [tform for tform in ts.tforms
              if isinstance(
                  tform, renderapi.transform.ReferenceTransform)][0]
    ref_args = renderapi.transform.ReferenceTransform(ref_ts.refId)
    ref_dd = renderapi.transform.ReferenceTransform(json=ref_ts.to_dict())

    assert (dict(ref_args) == ref_args.to_dict() == dict(ref_ts) ==
            ref_ts.to_dict() == dict(ref_dd) == ref_dd.to_dict())


def test_transform_hash_eq():
    t1 = renderapi.transform.Transform(
        **rendersettings.NONLINEAR_TRANSFORM_KWARGS)
    t2 = renderapi.transform.Transform(
        **rendersettings.NONLINEAR_TRANSFORM_KWARGS)

    assert t1 is not t2
    assert t1 == t2
    assert len({t1, t2}) == 1

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
                                          B0=245.3,
                                          B1=-234.1)
    assert am1 is not am2
    assert am1 == am2
    assert len({am1, am2}) == 1


def test_polynomial_transform_asorder_identity():
    srcpts = np.random.rand(50, 2)
    pt1 = renderapi.transform.Polynomial2DTransform(identity=True)
    pt2 = renderapi.transform.Polynomial2DTransform(identity=True).asorder(2)

    dstpts1 = pt1.tform(srcpts)
    dstpts2 = pt2.tform(srcpts)

    assert pt1.order != pt2.order
    assert np.allclose(dstpts1, dstpts2)


def test_transformsum_identity_polynomial():
    srcpts = np.random.rand(50, 2)
    pt = renderapi.transform.Polynomial2DTransform(identity=True)
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
    tformlist = [pt, am1, am2]
    new_tform = renderapi.transform.estimate_transformsum(
        tformlist, src=srcpts, order=1)

    new_srcpts = np.random.rand(50, 2)
    new_dstpts_comp = new_tform.tform(new_srcpts)
    new_dstpts = am2.concatenate(am1).tform(new_srcpts)
    assert np.allclose(new_dstpts_comp, new_dstpts)


def estimate_homography_transform(
        do_scale=True, do_translate=True, do_rotate=True, transformclass=None):
    scale = np.random.rand()
    random_scale = (renderapi.transform.AffineModel(
        M00=scale, M11=scale)
        if do_scale else renderapi.transform.AffineModel())

    random_translate = (renderapi.transform.AffineModel(
        B0=np.random.rand(), B1=np.random.rand())
        if do_translate else renderapi.transform.AffineModel())

    theta = np.random.rand() * 2 * np.pi
    random_rotate = (renderapi.transform.AffineModel(
        M00=np.cos(theta), M01=-np.sin(theta),
        M10=np.sin(theta), M11=np.cos(theta))
        if do_rotate else renderapi.transform.AffineModel())

    target_tform = random_translate.concatenate(
        random_rotate.concatenate(random_scale))

    src_pts = np.random.rand(50, 2)
    dst_pts = target_tform.tform(src_pts)
    tform = transformclass()
    tform.estimate(src_pts, dst_pts, return_params=False)

    assert np.allclose(target_tform.M, tform.M)
    if do_scale:
        assert np.isclose(tform.scale[0], scale)
    if do_translate:
        assert np.allclose(tform.translation, random_translate.translation)
    if do_rotate:
        assert np.isclose(tform.rotation, random_rotate.rotation)
    # currently forces as affines
    am = renderapi.transform.AffineModel(json=tform.to_dict())
    assert am.to_dict() == tform.to_dict()


def test_estimate_similarity_transform():
    estimate_homography_transform(
        transformclass=renderapi.transform.SimilarityModel)


def test_estimate_rigid_transform():
    estimate_homography_transform(
        do_scale=False, transformclass=renderapi.transform.RigidModel)


def test_estimate_translation_transform():
    estimate_homography_transform(
        do_scale=False, do_rotate=False,
        transformclass=renderapi.transform.TranslationModel)


def test_non_linear_transform():
    lens_tform = renderapi.transform.NonLinearTransform(dataString=\
                                               ("6 28 535.9261337198133 -0.07156495284083819 "
                                               "1.5429761616475304 482.5391851962856 -1.3964665434772456 "
                                               "-6.442573400985017 -2.9852709783360574 4.123111145658342 "
                                               "-11.540309826482599 5.014980246618293 13.616409494909078 "
                                               "6.8938038217739255 -2.580163142352532 -5.848702515778433 "
                                               "11.520166623181623 -0.26414636893418164 17.725654626324285 "
                                               "-3.6910106603259862 -5.747999298096374 6.850067634843171 "
                                               "16.792611164648633 7.81339608279572 -1.6748576247746882 "
                                               "7.294185157592906 -8.213479728551924 -5.181177837004834 "
                                               "-2.363460931085683 2.9307897710181123 -19.60977878575318 "
                                               "-5.626357722731385 -3.8857454141075323 -15.21120604177655 "
                                               "-21.23967741658828 -7.433492911261084 5.986054967656173 "
                                               "-0.2472470831304605 -4.252500955671167 6.285397956497022 "
                                               "-10.087631670227893 -2.936382384586807 13.850132289055523 "
                                               "-1.6230114467674603 -6.137660325940608 12.358797331540874 "
                                               "15.361852639613971 -7.395509537102164 -3.4680250777444144 "
                                               "11.543534617091353 2.1153010560743724 -6.1108581863128535 "
                                               "2.4532196427825284 -1.6047644982741716 5.190795110418094 "
                                               "0.40139303958456196 11.96302944378589 12.660577579061767 "
                                               "1196.3041637890071 1266.0596612286872 1719846.5445062846 "
                                               "1485783.6202875 1838252.7229766874 2.714668570418218E9 "
                                               "2.106666890772152E9 2.1421214796751451E9 2.8349699962925887E9 "
                                               "4.528468416208078E12 3.2949497103892886E12 3.0161488655484473E12 "
                                               "3.2930355498080786E12 4.550261299826646E12 7.824367950003595E15 "
                                               "5.464560367850104E15 4.686502506566912E15 4.616510470870998E15 "
                                               "5.276444951800235E15 7.530553575860649E15 1.3844135530148071E19 "
                                               "9.408014352057864E18 7.7275759384866017E18 7.1369460697416591E18 "
                                               "7.373674200122966E18 8.7221483757320745E18 1.277368891891578E19 "
                                               "100.0 537.4423453941299 485.2431449404924 1253541.1543424227 "
                                               "899439.7598253534 1082433.2436210443 2.5451681382231455E9 "
                                               "1.814150348079708E9 1.6692374367919033E9 2.1769137889095693E9 "
                                               "4.992425732284977E12 3.5258872445513765E12 3.074020072484778E12 "
                                               "3.1163128442286265E12 4.266956980967905E12 9.700243843041522E15 "
                                               "6.781968704541316E15 5.745611297869626E15 5.443791159762913E15 "
                                               "5.856309886603154E15 8.280136088463922E15 1.8821205899653665E19 "
                                               "1.3042150458228838E19 1.0829624014456685E19 9.899910593314652E18 "
                                               "9.885988268659214E18 1.1051253229808925E19 1.6002173610912907E19 "
                                               "0.0 2048 2048 "),
                                               transformId="testing")

    ticks = np.arange(0,2048,64,np.float)
    xx,yy = np.meshgrid(ticks,ticks)
    x = np.ravel(xx).T
    y = np.ravel(yy).T
    xy = np.vstack((x,y)).T

    xyp=lens_tform.tform(xy)
    dv = xyp-xy
    mean_disp= np.mean(np.sqrt(np.sum(dv**2,axis=1)))
    assert((mean_disp-0.7570507)<.01)