#!/usr/bin/env python
'''
handling mpicbg transforms in python

Currently only implemented to facilitate Affine, Polynomial2D,
    and LensCorrection used in Khaled Khairy's EM aligner workflow
TODO:
    interpolation functions
    Affine as subset of Polynomial2D
    approximation of other functions(TPS, meshtechniques) to Polynomial2D
'''
import json
import numpy as np


class EstimationError(Exception):
    pass


def _load_dict(obj, d):
    obj.__dict__.update({k: v for k, v in d.items()})


def _load_json(obj, j):
    with open(j, 'r') as f:
        jd = json.load(f)
    _load_dict(obj, jd)


class TransformList:
    def __init__(self, tforms):
        self.tforms = tforms

    def to_dict(self):
        return {'type': 'list',
                'specList': [tform.to_dict() for tform in self.tforms]}

    def to_json(self):
        return json.dumps(self.to_dict())


class ReferenceTransform:
    def __init__(self, refId=None, json=None):
        if json is not None:
            self.from_dict(json)
        else:
            self.refId = refId

    def to_dict(self):
        d = {}
        d['type'] = 'ref'
        d['refId'] = self.refId
        return d

    def from_dict(self, d):
        self.refId = d['refId']

    def __str__(self):
        return 'ReferenceTransform(%s)' % self.refId

    def __repr__(self):
        return self.__str__()


class Transform:
    def __init__(self, className=None, dataString=None,
                 transformId=None, json=None):
        if json is not None:
            self.from_dict(json)
        else:
            self.className = className
            self.dataString = dataString
            self.transformId = transformId

    def to_dict(self):
        d = {}
        d['type'] = 'leaf'
        d['className'] = self.className
        d['dataString'] = self.dataString
        if self.transformId is not None:
            d['transformId'] = self.transformId
        return d

    def from_dict(self, d):
        self.dataString = d['dataString']
        self.className = d['className']
        self.transformId = d.get('transformId', None)

    def __str__(self):
        return 'className:%s\ndataString:%s' % (
            self.className, self.dataString)

    def __repr__(self):
        return self.__str__()


class AffineModel(Transform):
    className = 'mpicbg.trakem2.transform.AffineModel2D'

    def __init__(self, M00=1.0, M01=0.0, M10=0.0, M11=1.0, B0=0.0, B1=0.0):
        self.M00 = M00
        self.M01 = M01
        self.M10 = M10
        self.M11 = M11
        self.B0 = B0
        self.B1 = B1
        self.className = 'mpicbg.trakem2.transform.AffineModel2D'
        self.load_M()

    def load_M(self):
        self.M = np.identity(3, np.double)
        self.M[0, 0] = self.M00
        self.M[0, 1] = self.M01
        self.M[1, 0] = self.M10
        self.M[1, 1] = self.M11
        self.M[0, 2] = self.B0
        self.M[1, 2] = self.B1

    def to_dict(self):
        d = {}
        d['type'] = 'leaf'
        d['className'] = self.className
        d['dataString'] = "%.10f %.10f %.10f %.10f %.10f %.10f" % (
            self.M[0, 0], self.M[1, 0], self.M[0, 1],
            self.M[1, 1], self.M[0, 2], self.M[1, 2])
        return d

    def from_dict(self, d):
        ds = d['dataString'].split()
        (self.M00, self.M10, self.M01, self.M11, self.B0, self.B1) = map(
            float, ds)
        self.load_M()

    def invert(self):
        Ai = AffineModel()
        Ai.M = np.linalg.inv(self.M)
        return Ai

    def convert_to_point_vector(self, points):
        Np = points.shape[0]

        zerovec = np.zeros((Np, 1), np.double)
        onevec = np.ones((Np, 1), np.double)

        assert(points.shape[1] == 2)
        Nd = 2
        points = np.concatenate((points, zerovec), axis=1)
        return points, Nd

    def convert_points_vector_to_array(self, points, Nd):
        points = points[:, 0:Nd] / np.tile(points[:, 2], (Nd, 1)).T
        return points

    def tform(self, points):
        points, Nd = self.convert_to_point_vector(points)
        pt = np.dot(self.M, points.T).T
        return self.convert_points_vector_to_array(pt, Nd)

    def concatenate(self, model):
        '''
        concatenate a model to this model -- ported from trakEM2 below:
            final double a00 = m00 * model.m00 + m01 * model.m10;
            final double a01 = m00 * model.m01 + m01 * model.m11;
            final double a02 = m00 * model.m02 + m01 * model.m12 + m02;

            final double a10 = m10 * model.m00 + m11 * model.m10;
            final double a11 = m10 * model.m01 + m11 * model.m11;
            final double a12 = m10 * model.m02 + m11 * model.m12 + m12;
        '''
        a00 = self.M[0, 0] * model.M[0, 0] + self.M[0, 1] * model.M[1, 0]
        a01 = self.M[0, 0] * model.M[0, 1] + self.M[0, 1] * model.M[1, 1]
        a02 = (self.M[0, 0] * model.M[0, 2] + self.M[0, 1] * model.M[1, 2] +
               self.M[0, 2])

        a10 = self.M[1, 0] * model.M[0, 0] + self.M[1, 1] * model.M[1, 0]
        a11 = self.M[1, 0] * model.M[0, 1] + self.M[1, 1] * model.M[1, 1]
        a12 = (self.M[1, 0] * model.M[0, 2] + self.M[1, 1] * model.M[1, 2] +
               self.M[1, 2])

        newmodel = AffineModel(a00, a01, a10, a11, a02, a12)
        return newmodel

    def inverse_tform(self, points):
        points, Nd = self.convert_to_point_vector(points)
        pt = np.dot(np.linalg.inv(self.M), points.T).T
        return self.convert_points_vector_to_array(pt, Nd)

    def __str__(self):
        return "M=[[%f,%f],[%f,%f]] B=[%f,%f]" % (
            self.M[0, 0], self.M[0, 1], self.M[1, 0],
            self.M[1, 1], self.M[0, 2], self.M[1, 2])


class Polynomial2DTransform(Transform):
    '''
    Polynomial2DTransform implemented as in skimage
    TODO:
        fall back to Affine Model in special cases
        robustness in estimation
    '''
    className = 'mpicbg.trakEM2.transform.PolynomialTransform2D'

    def __init__(self, dataString=None, src=None, dst=None, order=2,
                 force_polynomial=True):
        self.className = 'mpicbg.trakEM2.transform.PolynomialTransform2D'
        if dataString is not None:
            self._process_dataString(dataString)
        if src is not None and dst is not None:
            self._process_params(self.estimate(src, dst, order))

        if not force_polynomial and self.is_affine:
            # TODO try implement affine from poly (& vice versa)
            return AffineTransform(poly_params=self.params)

    @property
    def is_affine(self):
        '''TODO allow default to Affine'''
        return False

    def estimate(self, src, dst, order=2, convergence_test=None):
        '''This is unreliable -- add tests to ensure repeatability'''
        xs = src[:, 0]
        ys = src[:, 1]
        xd = dst[:, 0]
        yd = dst[:, 1]
        rows = src.shape[0]
        no_coeff = (order + 1) * (order + 2)

        if len(src) != len(dst):
            raise EstimationError(
                'source has {} points, but dest has {}!'.format(
                    len(src), len(dst)))
        if no_coeff > len(src):
            raise EstimationError(
                'order {} is too large to fit {} points!'.format(
                    order, len(src)))

        A = np.empty([rows * 2, no_coeff + 1])
        pidx = 0
        for j in range(order + 1):
            for i in range(j + 1):
                A[:rows, pidx] = xs ** (j - i) * ys ** i
                A[rows:, pidx + no_coeff // 2] = xs ** (j - i) * ys ** i
                pidx += 1

        A[:rows, -1] = xd
        A[rows:, -1] = yd

        # right singular vector corresponding to smallest singular value
        # TODO implement tests for this
        _, _, V = np.linalg.svd(A)
        return (-V[-1, :-1] / V[-1, -1]).reshape((2, no_coeff // 2))

    def _process_params(self, params):
        '''
        generate datastring and param attributes from params
        '''
        self.params = params
        self.dataString = self._dataStringfromParams(params)

    def _dataStringfromParams(self, params=None):
        return ' '.join([str(i) for i in params.flatten()]).replace('e', 'E')

    def _process_dataString(self, datastring):
        '''
        generate datastring and param attributes from datastring
        '''
        dsList = datastring.split(' ')
        self.params = numpy.array(
            [[float(d) for d in dsList[:len(dsList)/2]],
             [float(d) for d in dsList[len(dsList)/2]]])
        self.dataString = datastring

    def tform(self, points):
        dst = np.zeros(points.shape)
        x = points[:, 0]
        y = points[:, 1]

        o = int((-3 + np.sqrt(9 - 4 * (2 - len(self.params.ravel())))) / 2)
        pidx = 0
        for j in range(o + 1):
            for i in range(j + 1):
                dst[:, 0] += self.params[0, pidx] * x ** (j - i) * y ** i
                dst[:, 1] += self.params[1, pidx] * x ** (j - i) * y ** i
                pidx += 1
        return dst


def transformsum(transformlist):
    '''
    summation of all transforms in a list of transforms.
        Will force affines as polynomials.  Does not support LC.
    Returns:
        AffineTransform or Polynomial2DTransform representing the sum of the
            input list
    '''
    pass
