#!/usr/bin/env python
"""handling mpicbg transforms in python

Currently only implemented to facilitate Affine and Polynomial2D
    used in Khaled Khairy's EM aligner workflow
"""
import json
import logging
from collections import Iterable
import numpy as np
from .errors import ConversionError, EstimationError, RenderError
from .utils import NullHandler

logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())

try:
    from scipy.linalg import svd, LinAlgError
except ImportError as e:
    logger.info(e)
    logger.info('scipy-based linalg may or may not lead '
                'to better parameter fitting')
    from numpy.linalg import svd
    from numpy.linalg.linalg import LinAlgError


class TransformList:
    """A list of Transforms

    Attributes
    ----------
    tforms : :obj:`list` of :class:`Transform`
        transforms to apply
    transformId : str, optional
        uniqueId for this TransformList
    """

    def __init__(self, tforms=None, transformId=None, json=None):
        """Initialize TransformList

        Parameters
        ----------
        tforms : :obj:`list` of :class:`Transform`
            transforms to apply
        transformId : str, optional
            uniqueId for this TransformList
        json : dict, optional
            json compatible dictionary to create
            :class:`TransformList` via :method:`from_dict`
            (will supersede tforms and transformId if not None)
        """
        if json is not None:
            self.from_dict(json)
        else:
            if tforms is None:
                self.tforms = []
            else:
                if not isinstance(tforms, list):
                    raise RenderError(
                        'unexpected type {} for transforms!'.format(
                            type(tforms)))
                self.tforms = tforms
            self.transformId = transformId

    def to_dict(self):
        """serialization function

        Returns
        -------
        dict
            json & render compatible representation of this TransformList
        """
        d = {}
        d['type'] = 'list'
        d['specList'] = [tform.to_dict() for tform in self.tforms]
        if self.transformId is not None:
            d['id'] = self.transformId
        return d

    def to_json(self):
        """serialization function

        Returns
        -------
        str
            string representation of the json & render
            representation of this TransformList
        """
        return json.dumps(self.to_dict())

    def from_dict(self, d):
        """deserialization function

        Parameters
        ----------
        d : dict
            json compatible dictionary representation of this TransformList
        """
        self.tforms = []
        if d is not None:
            self.transformId = d.get('id')
            for td in d['specList']:
                self.tforms.append(load_transform_json(td))
        return self.tforms


def load_transform_json(d, default_type='leaf'):
    """function to get the proper deserialization function

    Parameters
    ----------
    d : dict
        json compatible representation of Transform
    default_type : str
        what kind of transform should we assume this
        if it is not specified in 'type' ('leaf','list','ref','interpolated')

    Returns
    -------
    func
        proper function to deserialize this transformation

    Raises
    ------
    RenderError
        if d['type'] isn't one of ('leaf','list','ref','interpolated')
    """
    handle_load_tform = {'leaf': load_leaf_json,
                         'list': lambda x: TransformList(json=x),
                         'ref': lambda x: ReferenceTransform(json=x),
                         'interpolated':
                             lambda x: InterpolatedTransform(json=x)}
    try:
        return handle_load_tform[d.get('type', default_type)](d)
    except KeyError as e:
        raise RenderError('Unknown Transform Type {}'.format(e))


def load_leaf_json(d):
    """function to get the proper deserialization function for leaf transforms

    Parameters
    ----------
    d : dict
        json compatible representation of leaf transform to deserialize

    Returns
    -------
    func
        proper function to deserialize this transformation

    Raises
    ------
    RenderError
        if d['type'] != leaf or is omitted

    """
    handle_load_leaf = {
        AffineModel.className: lambda x: AffineModel(json=x),
        Polynomial2DTransform.className:
            lambda x: Polynomial2DTransform(json=x),
        TranslationModel.className: lambda x: TranslationModel(json=x),
        RigidModel.className: lambda x: RigidModel(json=x),
        SimilarityModel.className: lambda x: SimilarityModel(json=x),
        NonLinearTransform.className lambda x: NonLinearTransform(json=x)}

    tform_type = d.get('type', 'leaf')
    if tform_type != 'leaf':
        raise RenderError(
            'Unexpected or unknown Transform Type {}'.format(tform_type))
    tform_class = d['className']
    try:
        return handle_load_leaf[tform_class](d)
    except KeyError as e:
        logger.info('Leaf transform class {} not defined in '
                    'transform module, using generic'.format(e))
        return Transform(json=d)


class InterpolatedTransform:
    """Transform spec defined by linear interpolation of
    two other transform specs

    Attributes
    ----------
    a : :class:`Transform` or :class:`TransformList` or :class:`InterpolatedTransform`
        transform at minimum weight
    b : :class:`Transform` or :class:`TransformList` or :class:`InterpolatedTransform`
        transform at maximum weight
    lambda_ : float
        value in interval [0.,1.] which defines evaluation of the
        linear interpolation between a (at 0) and b (at 1)
    """

    def __init__(self, a=None, b=None, lambda_=None, json=None):
        """Initialize InterpolatedTransform

        Parameters
        ----------
        a : :class:`Transform` or :class:`TransformList`
        or :class:`InterpolatedTransform`
            transform at minimum weight
        b : :class:`Transform` or :class:`TransformList`
        or :class:`InterpolatedTransform`
            transform at maximum weight
        lambda_ : float
            value in interval [0.,1.] which defines evaluation of the
            linear interpolation between a (at 0) and b (at 1)
        json : dict
            json compatible representation of this transform to
            initialize via :method:`self.from_dict`
            (will supersede a, b, and lambda_ if not None)

        """
        if json is not None:
            self.from_dict(json)
        else:
            self.a = a
            self.b = b
            self.lambda_ = lambda_

    def to_dict(self):
        """serialization routine

        Returns
        -------
        dict
            json compatible representation
        """
        return dict(self)

    def from_dict(self, d):
        """deserialization routine

        Parameters
        ----------
        d : dict
            json compatible representation
        """
        self.a = load_transform_json(d['a'])
        self.b = load_transform_json(d['b'])
        self.lambda_ = d['lambda']

    def __iter__(self):
        return iter([('type', 'interpolated'),
                     ('a', self.a.to_dict()),
                     ('b', self.b.to_dict()),
                     ('lambda', self.lambda_)])


class ReferenceTransform:
    """Transform which is simply a reference to a transform stored elsewhere

    Attributes
    ----------
    refId : str
        transformId of the referenced transform

    """

    def __init__(self, refId=None, json=None):
        """Initialize ReferenceTransform

        Parameters
        ----------
        refId : str
            transformId of the referenced transform
        json : dict
            json compatible representation of this transform
            (will supersede refId if not None)

        """
        if json is not None:
            self.from_dict(json)
        else:
            self.refId = refId

    def to_dict(self):
        """serialization routine

        Returns
        -------
        dict
            json compatible representation of this transform
        """
        d = {}
        d['type'] = 'ref'
        d['refId'] = self.refId
        return d

    def from_dict(self, d):
        """deserialization routine

        Parameters
        ----------
        d : dict
            json compatible representation of this transform
        """
        self.refId = d['refId']

    def __str__(self):
        return 'ReferenceTransform(%s)' % self.refId

    def __repr__(self):
        return self.__str__()

    def __iter__(self):
        return iter([('type', 'ref'), ('refId', self.refId)])


class Transform(object):
    """Base transformation class

    Attributes
    ----------
    className : str
        mpicbg java classname of this transform
    dataString : str
        string reprsentation of this transform as speced by
        mpicbg java class library
    transformId : str, optional
        unique Id for this transform (optional)
    """

    def __init__(self, className=None, dataString=None,
                 transformId=None, json=None):
        """Initialize Transform

        Parameters
        ----------
        className : str
            mpicbg java classname of this transform
        dataString : str
            string reprsentation of this transform as speced
            by mpicbg java class library
        transformId : str, optional
            unique Id for this transform (optional)
        json : dict
            json compatible representation of this transform
            (supersedes className, dataString, and transformId if not None)
        """
        if json is not None:
            self.from_dict(json)
        else:
            self.className = className
            self.dataString = dataString
            self.transformId = transformId

    def to_dict(self):
        """serialization routine

        Returns
        -------
        dict
            json compatible representation of this transform
        """
        d = {}
        d['type'] = 'leaf'
        d['className'] = self.className
        d['dataString'] = self.dataString
        if self.transformId is not None:
            d['transformId'] = self.transformId
        return d

    def from_dict(self, d):
        """deserialization routine

        Parameters
        ----------
        d : dict
            json compatible representation of this transform
        """
        self.className = d['className']
        self.transformId = d.get('transformId', None)
        self._process_dataString(d['dataString'])

    def _process_dataString(self, datastring):
        """method meant to set state of transform from datastring
        generic implementation only saves datastring at self.dataString.
        should rewrite for all transform classes that want to
        implement tform,fit,etc

        Parameters
        ----------
        dataString : str
            string which can be used to initialize mpicbg transforms in java
        """
        self.dataString = datastring

    def __str__(self):
        return 'className:%s\ndataString:%s' % (
            self.className, self.dataString)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.__str__() == other.__str__()

    def __hash__(self):
        return hash((self.__str__()))


class AffineModel(Transform):
    """Linear 2d Transformation
    mpicbg classname: mpicbg.trakem2.transform.AffineModel2D
    implements this simple math
    x'=M00*x + M01*x + B0
    y'=M10*x + M11*y + B1

    Attributes
    ----------
    M00 : float
        x'+=M00*x
    M01 : float
        x'+=M01*y
    M10 : float
        y'+=M10*x
    M11 : float
        y'+=M11*y
    B0 : float
        x'+=B0
    B1 : float
        y'+=B1
    transformId : str, optional
        unique transformId for this transform
    M : numpy.array
        3x3 numpy array representing 2d Affine with homogeneous coordinates
        populates with values from M00, M01, M10, M11, B0, B1 with load_M()

    """

    className = 'mpicbg.trakem2.transform.AffineModel2D'

    def __init__(self, M00=1.0, M01=0.0, M10=0.0, M11=1.0, B0=0.0, B1=0.0,
                 transformId=None, json=None):
        """Initialize AffineModel, defaulting to identity

        Parameters
        ----------
        M00 : float
            x'+=M00*x
        M01 : float
            x'+=M01*y
        M10 : float
            y'+=M10*x
        M11 : float
            y'+=M11*y
        B0 : float
            x'+=B0
        B1 : float
            y'+=B1
        transformId : str
            unique transformId for this transform (optional)
        json : dict
            json compatible representation of this transform
            (will supersede all other parameters if not None)

        """
        if json is not None:
            self.from_dict(json)
        else:
            self.M00 = M00
            self.M01 = M01
            self.M10 = M10
            self.M11 = M11
            self.B0 = B0
            self.B1 = B1
            self.className = 'mpicbg.trakem2.transform.AffineModel2D'
            self.load_M()
            self.transformId = transformId

    @property
    def dataString(self):
        """dataString string for this transform"""
        return "%.10f %.10f %.10f %.10f %.10f %.10f" % (
            self.M[0, 0], self.M[1, 0], self.M[0, 1],
            self.M[1, 1], self.M[0, 2], self.M[1, 2])

    def _process_dataString(self, datastring):
        """generate datastring and param attributes from datastring"""
        dsList = datastring.split()
        self.M00 = float(dsList[0])
        self.M10 = float(dsList[1])
        self.M01 = float(dsList[2])
        self.M11 = float(dsList[3])
        self.B0 = float(dsList[4])
        self.B1 = float(dsList[5])
        self.load_M()

    def load_M(self):
        """method to take the attribute of self and fill in self.M"""
        self.M = np.identity(3, np.double)
        self.M[0, 0] = self.M00
        self.M[0, 1] = self.M01
        self.M[1, 0] = self.M10
        self.M[1, 1] = self.M11
        self.M[0, 2] = self.B0
        self.M[1, 2] = self.B1

    @staticmethod
    def fit(A, B):
        """function to fit this transform given the corresponding sets of points A & B

        Parameters
        ----------
        A : numpy.array
            a Nx2 matrix of source points
        B : numpy.array
            a Nx2 matrix of destination points

        Returns
        -------
        numpy.array
            a 6x1 matrix with the best fit parameters
            ordered M00,M01,M10,M11,B0,B1
        """
        if not all([A.shape[0] == B.shape[0], A.shape[1] == B.shape[1] == 2]):
            raise EstimationError(
                'shape mismatch! A shape: {}, B shape {}'.format(
                    A.shape, B.shape))

        N = A.shape[0]  # total points

        M = np.zeros((2 * N, 6))
        Y = np.zeros((2 * N, 1))
        for i in range(N):
            M[2 * i, :] = [A[i, 0], A[i, 1], 0, 0, 1, 0]
            M[2 * i + 1, :] = [0, 0, A[i, 0], A[i, 1], 0, 1]
            Y[2 * i] = B[i, 0]
            Y[2 * i + 1] = B[i, 1]

        (Tvec, residuals, rank, s) = np.linalg.lstsq(M, Y)
        return Tvec

    def estimate(self, A, B, return_params=True, **kwargs):
        """method for setting this transformation with the best fit
        given the corresponding points A,B

        Parameters
        ----------
        A : numpy.array
            a Nx2 matrix of source points
        B : numpy.array
            a Nx2 matrix of destination points
        return_params : boolean
            whether to return the parameter matrix
        **kwargs
            keyword arguments to pass to self.fit

        Returns
        -------
        numpy.array
            a 2x3 matrix of parameters for this matrix,
            laid out (x,y) x (x,y,offset)
            (or None if return_params=False)
        """
        Tvec = self.fit(A, B, **kwargs)
        self.M00 = Tvec[0, 0]
        self.M10 = Tvec[2, 0]
        self.M01 = Tvec[1, 0]
        self.M11 = Tvec[3, 0]
        self.B0 = Tvec[4, 0]
        self.B1 = Tvec[5, 0]
        self.load_M()
        if return_params:
            return self.M

    def concatenate(self, model):
        """concatenate a model to this model -- ported from trakEM2 below:
            ::
                
                final double a00 = m00 * model.m00 + m01 * model.m10;
                final double a01 = m00 * model.m01 + m01 * model.m11;
                final double a02 = m00 * model.m02 + m01 * model.m12 + m02;

                final double a10 = m10 * model.m00 + m11 * model.m10;
                final double a11 = m10 * model.m01 + m11 * model.m11;
                final double a12 = m10 * model.m02 + m11 * model.m12 + m12;

        Parameters
        ----------
        model : AffineModel
            model to concatenate to this one

        Returns
        -------
        AffineModel
            model after concatenating model with this model
        """
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

    def invert(self):
        """return an inverted version of this transformation

        Returns
        -------
        AffineModel
            an inverted version of this transformation
        """
        inv_M = np.linalg.inv(self.M)
        Ai = AffineModel(inv_M[0, 0], inv_M[0, 1], inv_M[1, 0],
                         inv_M[1, 1], inv_M[0, 2], inv_M[1, 2])
        return Ai

    @staticmethod
    def convert_to_point_vector(points):
        """method to help reshape x,y points to x,y,1 vectors

        Parameters
        ----------
        points : numpy.array
            a Nx2 array of x,y points

        Returns
        -------
        numpy.array
            a Nx3 array of x,y,1 points used for transformations
        """
        Np = points.shape[0]
        onevec = np.ones((Np, 1), np.double)

        if points.shape[1] != 2:
            raise ConversionError('Points must be of shape (:, 2) '
                                  '-- got {}'.format(points.shape))
        Nd = 2
        points = np.concatenate((points, onevec), axis=1)
        return points, Nd

    @staticmethod
    def convert_points_vector_to_array(points, Nd=2):
        """method for convertion x,y,K points to x,y vectors

        Parameters
        ----------
        points : numpy.array
            a Nx3 vector of points after transformation
        Nd : int
            the number of dimensions to cutoff (should be 2)

        Returns
        -------
        numpy.array: a Nx2 array of x,y points
        """
        points = points[:, 0:Nd] / np.tile(points[:, 2], (Nd, 1)).T
        return points

    def tform(self, points):
        """transform a set of points through this transformation

        Parameters
        ----------
        points : numpy.array
            a Nx2 array of x,y points

        Returns
        -------
        numpy.array
            a Nx2 array of x,y points after transformation
        """
        points, Nd = self.convert_to_point_vector(points)
        pt = np.dot(self.M, points.T).T
        return self.convert_points_vector_to_array(pt, Nd)

    def inverse_tform(self, points):
        """transform a set of points through the inverse of this transformation

        Parameters
        ----------
        points : numpy.array
            a Nx2 array of x,y points

        Returns
        -------
        numpy.array
            a Nx2 array of x,y points after inverse transformation
        """
        points, Nd = self.convert_to_point_vector(points)
        pt = np.dot(np.linalg.inv(self.M), points.T).T
        return self.convert_points_vector_to_array(pt, Nd)

    @property
    def scale(self):
        """tuple of scale for x, y"""
        return tuple([np.sqrt(sum([i ** 2 for i in self.M[:, j]]))
                      for j in range(self.M.shape[1])])[:2]

    @property
    def shear(self):
        """counter-clockwise shear angle"""
        return np.arctan2(-self.M[0, 1], self.M[1, 1]) - self.rotation

    @property
    def translation(self):
        """tuple of translation in x, y"""
        return tuple(self.M[:2, 2])

    @property
    def rotation(self):
        """counter-clockwise rotation"""
        return np.arctan2(self.M[1, 0], self.M[0, 0])

    def __str__(self):
        return "M=[[%f,%f],[%f,%f]] B=[%f,%f]" % (
            self.M[0, 0], self.M[0, 1], self.M[1, 0],
            self.M[1, 1], self.M[0, 2], self.M[1, 2])


class TranslationModel(AffineModel):
    """Translation fitting and estimation as an :class:`AffineModel`
    Linear 2d Transformation
    mpicbg classname: mpicbg.trakem2.transform.AffineModel2D
    implements this simple math
    x'=M00*x + M01*x + B0
    y'=M10*x + M11*y + B1

    Attributes
    ----------
    M00 : float
        x'+=M00*x
    M01 : float
        x'+=M01*y
    M10 : float
        y'+=M10*x
    M11 : float
        y'+=M11*y
    B0 : float
        x'+=B0
    B1 : float
        y'+=B1
    transformId : str, optional
        unique transformId for this transform
    M : numpy.array
        3x3 numpy array representing 2d Affine with homogeneous coordinates
        populates with values from M00, M01, M10, M11, B0, B1 with load_M()
    """

    className = 'mpicbg.trakem2.transform.TranslationModel2D'

    def __init__(self, *args, **kwargs):
        super(TranslationModel, self).__init__(*args, **kwargs)
        # raise NotImplementedError(
        #     'TranslationModel not implemented. please use Affine')

    def _process_dataString(self, dataString):
        """expected dataString is 'tx ty'"""
        tx, ty = map(float(dataString.split(' ')))
        self.B0 = tx
        self.B1 = ty
        self.load_M()

    @staticmethod
    def fit(src, dst):
        """function to fit Translation transform given
        the corresponding sets of points src & dst

        Parameters
        ----------
        src : numpy.array
            a Nx2 matrix of source points
        dst : numpy.array
            a Nx2 matrix of destination points

        Returns
        -------
        numpy.array
            a 6x1 matrix with the best fit parameters
            ordered M00,M01,M10,M11,B0,B1
        """
        t = dst.mean(axis=0) - src.mean(axis=0)
        T = np.eye(3)
        T[:2, 2] = t
        return T

    def estimate(self, src, dst, return_params=True):
        """method for setting this transformation with the best fit
        given the corresponding points src,dst

        Parameters
        ----------
        src : numpy.array
            a Nx2 matrix of source points
        dst : numpy.array
            a Nx2 matrix of destination points
        return_params : bool
            whether to return the parameter matrix

        Returns
        -------
        numpy.array
            a 2x3 matrix of parameters for this matrix,
            laid out (x,y) x (x,y,offset)
            (or None if return_params=False)
        """
        self.M = self.fit(src, dst)
        if return_params:
            return self.M


class RigidModel(AffineModel):
    """model for fitting Rigid only transformations
    (rotation+translation)
    or
    (determinate=1, orthonormal eigenvectors)
    implemented as an :class:`AffineModel`


    Attributes
    ----------
    M00 : float
        x'+=M00*x
    M01 : float
        x'+=M01*y
    M10 : float
        y'+=M10*x
    M11 : float
        y'+=M11*y
    B0 : float
        x'+=B0
    B1 : float
        y'+=B1
    transformId : str, optional
        unique transformId for this transform
    M : numpy.array
        3x3 numpy array representing 2d Affine with homogeneous coordinates
        populates with values from M00, M01, M10, M11, B0, B1 with load_M()

    """
    className = 'mpicbg.trakem2.transform.RigidModel2D'

    def __init__(self, *args, **kwargs):
        super(RigidModel, self).__init__(*args, **kwargs)
        # raise NotImplementedError(
        #     'RigidModel not implemented. please use Affine')

    def _process_dataString(self, dataString):
        """expected datastring is 'theta tx ty'"""
        theta, tx, ty = map(float(dataString.split(' ')))
        self.M00 = np.cos(theta)
        self.M01 = -np.sin(theta)
        self.M10 = np.sin(theta)
        self.M11 = np.sin(theta)
        self.B0 = tx
        self.B1 = ty
        self.load_M()

    @staticmethod
    def fit(src, dst, rigid=True, **kwargs):
        """function to fit this transform given the corresponding
        sets of points src & dst
        Umeyama estimation of similarity transformation

        Parameters
        ----------
        src : numpy.array
            a Nx2 matrix of source points
        dst : numpy.array
            a Nx2 matrix of destination points
        rigid : bool
            whether to constrain this transform to be rigid

        Returns
        -------
        numpy.array
            a 6x1 matrix with the best fit parameters
            ordered M00,M01,M10,M11,B0,B1
        """
        # TODO shape assertion
        num, dim = src.shape
        src_cld = src - src.mean(axis=0)
        dst_cld = dst - dst.mean(axis=0)
        A = np.dot(dst_cld.T, src_cld) / num
        d = np.ones((dim, ), dtype=np.double)
        if np.linalg.det(A) < 0:
            d[dim - 1] = -1
        T = np.eye(dim + 1, dtype=np.double)

        rank = np.linalg.matrix_rank(A)
        if rank == 0:
            raise EstimationError('zero rank matrix A unacceptable -- '
                                  'likely poorly conditioned')

        U, S, V = svd(A)

        if rank == dim - 1:
            if np.linalg.det(U) * np.linalg.det(V) > 0:
                T[:dim, :dim] = np.dot(U, V)
            else:
                s = d[dim - 1]
                d[dim - 1] = -1
                T[:dim, :dim] = np.dot(U, np.dot(np.diag(d), V))
                d[dim - 1] = s
        else:
            T[:dim, :dim] = np.dot(U, np.dot(np.diag(d), V.T))

        fit_scale = (1.0 if rigid else
                     1.0 / src_cld.var(axis=0).sum() * np.dot(S, d))

        T[:dim, dim] = dst.mean(axis=0) - fit_scale * np.dot(
            T[:dim, :dim], src.mean(axis=0).T)
        T[:dim, :dim] *= fit_scale
        return T

    def estimate(self, A, B, return_params=True, **kwargs):
        """method for setting this transformation with the
        best fit given the corresponding points src,dst

        Parameters
        ----------
        A : numpy.array
            a Nx2 matrix of source points
        B : numpy.array
            a Nx2 matrix of destination points
        return_params : bool
            whether to return the parameter matrix

        Returns
        -------
        numpy.array
            a 2x3 matrix of parameters for this matrix,
            laid out (x,y) x (x,y,offset)
            (or None if return_params=False)
        """
        self.M = self.fit(A, B, **kwargs)
        if return_params:
            return self.M


class SimilarityModel(RigidModel):
    """class for fitting Similarity transformations
    (translation+rotation+scaling)
    or
    (orthogonal eigen vectors with equal eigenvalues)

    implemented as an :class:`AffineModel`

    Attributes
    ----------
    M00 : float
        x'+=M00*x
    M01 : float
        x'+=M01*y
    M10 : float
        y'+=M10*x
    M11 : float
        y'+=M11*y
    B0 : float
        x'+=B0
    B1 : float
        y'+=B1
    transformId : str, optional
        unique transformId for this transform
    M : numpy.array
        3x3 numpy array representing 2d Affine with homogeneous coordinates
        populates with values from M00, M01, M10, M11, B0, B1 with load_M()

    """
    className = 'mpicbg.trakem2.transform.SimilarityModel2D'

    def __init__(self, *args, **kwargs):
        super(SimilarityModel, self).__init__(*args, **kwargs)
        # raise NotImplementedError(
        #     'SimilarityModel not implemented. please use Affine')

    def _process_dataString(self, dataString):
        """expected datastring is 's theta tx ty'"""
        s, theta, tx, ty = map(float(dataString.split(' ')))
        self.M00 = s * np.cos(theta)
        self.M01 = -s * np.sin(theta)
        self.M10 = s * np.sin(theta)
        self.M11 = s * np.sin(theta)
        self.B0 = tx
        self.B1 = ty
        self.load_M()

    @staticmethod
    def fit(src, dst, rigid=False, **kwargs):
        """function to fit this transform given the corresponding
        sets of points src & dst
        Umeyama estimation of similarity transformation

        Parameters
        ----------
        src : numpy.array
            a Nx2 matrix of source points
        dst : numpy.array
            a Nx2 matrix of destination points
        rigid : bool
            whether to constrain this transform to be rigid

        Returns
        -------
        numpy.array
            a 6x1 matrix with the best fit parameters
            ordered M00,M01,M10,M11,B0,B1
        """
        return RigidModel.fit(src, dst, rigid=rigid)


class Polynomial2DTransform(Transform):
    """Polynomial2DTransform implemented as in skimage

    Attributes
    ----------
    params : numpy.array
        2xK matrix of polynomial coefficents up to order K

    """
    className = 'mpicbg.trakem2.transform.PolynomialTransform2D'

    def __init__(self, dataString=None, src=None, dst=None, order=2,
                 force_polynomial=True, params=None, identity=False,
                 json=None, **kwargs):
        """Initialize Polynomial2DTransform
        This provides 5 different ways to initialize the transform which are
        mutually exclusive and applied in the order specified here.
        1)json2)dataString,3)identity,4)params,5)(src,dst)

        Parameters
        ----------
        json : dict
            dictionary representation of the Polynomial2DTransform
            generally used by TransformList
        dataString : str
            dataString representation of transform from mpicpg
        identity : bool
            whether to make this transform the identity
        params : numpy.array
            2xK matrix of polynomial coefficents up to order K
        src : numpy.array
            Nx2 array of source points to use for fitting (used with dst)
        dst : numpy.array
            Nx2 array of destination points to use for fitting (used with src)
        order : int
            degree of polynomial to store
        force_polynomial : bool
            whether to force this representation to return a Polynomial
            regardless of degree (not implemented)


        """
        if json is not None:
            self.from_dict(json)
        else:
            self.className = 'mpicbg.trakem2.transform.PolynomialTransform2D'
            if dataString is not None:
                self._process_dataString(dataString)
            elif identity:
                self.params = np.array([[0, 1, 0], [0, 0, 1]])
            elif params is not None:
                self.params = params
            elif src is not None and dst is not None:
                self.estimate(src, dst, order, return_params=False, **kwargs)

            if not force_polynomial and self.is_affine:
                raise NotImplementedError('Falling back to Affine model is '
                                          'not supported {}')
            self.transformId = None

    @property
    def is_affine(self):
        """(boolean) TODO allow default to Affine"""
        return False
        # return self.order

    @property
    def order(self):
        """(int) order of polynomial"""
        no_coeffs = len(self.params.ravel())
        return int((abs(np.sqrt(4 * no_coeffs + 1)) - 3) / 2)

    @property
    def dataString(self):
        """dataString of polynomial"""
        return Polynomial2DTransform._dataStringfromParams(self.params)

    @staticmethod
    def fit(src, dst, order=2):
        """function to fit this transform given the corresponding sets
        of points src & dst
        polynomial fit

        Parameters
        ----------
        src : numpy.array
            a Nx2 matrix of source points
        dst : numpy.array
            a Nx2 matrix of destination points
        order : bool
            order of polynomial to fit

        Returns
        -------
        numpy.array
            a [2,(order+1)*(order+2)/2] array with the best fit parameters
        """
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

        A = np.zeros([rows * 2, no_coeff + 1])
        pidx = 0
        for j in range(order + 1):
            for i in range(j + 1):
                A[:rows, pidx] = xs ** (j - i) * ys ** i
                A[rows:, pidx + no_coeff // 2] = xs ** (j - i) * ys ** i
                pidx += 1

        A[:rows, -1] = xd
        A[rows:, -1] = yd

        # right singular vector corresponding to smallest singular value
        _, s, V = svd(A)
        Vsm = V[np.argmin(s), :]  # never trust computers
        return (-Vsm[:-1] / Vsm[-1]).reshape((2, no_coeff // 2))

    def estimate(self, src, dst, order=2,
                 test_coords=True, max_tries=100, return_params=True,
                 **kwargs):
        """method for setting this transformation with the
        best fit given the corresponding points src,dst

        Parameters
        ----------
        src : numpy.array
            a Nx2 matrix of source points
        dst : numpy.array
            a Nx2 matrix of destination points
        order : int
            order of polynomial to fit
        test_coords : bool
            whether to test model after fitting to
            make sure it is good (see fitgood)
        max_tries : int
            how many times to attempt to fit the model (see fitgood)
        return_params : bool
            whether to return the parameter matrix
        **kwargs
            dictionary of keyword arguments including those
            that can be passed to fitgood

        Returns
        -------
        numpy.array
            a (2,(order+1)*(order+2)/2) matrix of parameters for this matrix
            (or None if return_params=False)
        """
        def fitgood(src, dst, params, atol=1e-3, rtol=0, **kwargs):
            """check if model produces a 'good' result

            Parameters
            ----------
            src : numpy.array
                a Nx2 matrix of source points
            dst : numpy.array
                a Nx2 matrix of destination points
            params : numpy.array
                a Kx2 matrix of parameters
            atol : float
                absolute tolerance as in numpy.allclose for
                transformed sample points
            rtol : float
                relative tolerance as in numpy.allclose for
                transformed sample points

            Returns
            -------
            bool
                whether the goodness condition is met
            """
            result = Polynomial2DTransform(params=params).tform(src)
            t = np.allclose(
                result, dst,
                atol=atol, rtol=rtol)
            return t

        estimated = False
        tries = 0
        while (tries < max_tries and not estimated):
            tries += 1
            try:
                params = Polynomial2DTransform.fit(src, dst, order=order)
            except (LinAlgError, ValueError) as e:
                logger.debug('Encountered error {}'.format(e))
                continue
            estimated = (fitgood(src, dst, params, **kwargs) if
                         test_coords else True)

        if tries == max_tries and not estimated:
            raise EstimationError('Could not fit Polynomial '
                                  'in {} attempts!'.format(tries))
        logger.debug('fit parameters in {} attempts'.format(tries))
        self.params = params
        if return_params:
            return self.params

    @staticmethod
    def _dataStringfromParams(params=None):
        """method for producing a dataString from the parameters"""
        return ' '.join([str(i).replace('e-0', 'e-').replace('e+0', 'e+')
                         for i in params.flatten()]).replace('e', 'E')

    def _process_dataString(self, datastring):
        """generate datastring and param attributes from datastring"""
        dsList = datastring.split(' ')
        self.params = Polynomial2DTransform._format_raveled_params(dsList)

    @staticmethod
    def _format_raveled_params(raveled_params):
        """method to reshape linear parameters into parameter matrix

        Parameters
        ----------
        raveled_params : numpy.array
            an K long vector of parameters

        Returns
        -------
        numpy.array
            a (2,K/2) matrix of parameters, with
            first row for x and 2nd row for y
        """

        return np.array(
            [[float(d) for d in raveled_params[:len(raveled_params) / 2]],
             [float(d) for d in raveled_params[len(raveled_params) / 2:]]])

    def tform(self, points):
        """transform a set of points through this transformation

        Parameters
        ----------
        points : numpy.array
            a Nx2 array of x,y points

        Returns
        -------
        numpy.array
            a Nx2 array of x,y points after transformation
        """
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

    def coefficients(self, order=None):
        """determine number of coefficient terms in transform for a given order

        Parameters
        ----------
        order : int, optional
            order of polynomial,  defaults to self.order

        Returns
        -------
        int
            number of coefficient terms expected in transform

        """
        if order is None:
            order = self.order
        return (order + 1) * (order + 2)

    def asorder(self, order):
        '''return polynomial transform appoximation of this
        transformation with a lower order

        Parameters
        ----------
        order :int
            desired order (must have order> current order)

        Returns
        -------
        :class:`Polynomial2DTransform`
            transform of lower order

        Raises
        ------
        ConversionError
            if target order < input order
        '''
        if self.order > order:
            raise ConversionError(
                'transformation {} is order {} -- conversion to '
                'order {} not supported'.format(
                    self.dataString, self.order, order))
        new_params = np.zeros([2, self.coefficients(order) // 2])
        new_params[:self.params.shape[0], :self.params.shape[1]] = self.params
        return Polynomial2DTransform(params=new_params)

    @staticmethod
    def fromAffine(aff):
        """return a polynomial transformation equavalent to a given Affine

        Parameters
        ----------
        aff : AffineModel
            transform to become equivalent to

        Returns
        -------
        Polynomial2DTransform
            Order 1 transform equal in effect to aff

        Raises
        ------
        ConversionError
            if input model is not AffineModel
        """
        if not isinstance(aff, AffineModel):
            raise ConversionError('attempting to convert a nonaffine model!')
        return Polynomial2DTransform(order=1, params=np.array([
            [aff.M[0, 2], aff.M[0, 0], aff.M[0, 1]],
            [aff.M[1, 2], aff.M[1, 0], aff.M[1, 1]]]))


def estimate_dstpts(transformlist, src=None):
    """estimate destination points for list of transforms.  Recurses
    through lists.

    Parameters
    ----------
    transformlist : :obj:list of :obj:Transform
        transforms that have a tform method implemented
    src : numpy.array
        a Nx2  array of source points

    Returns
    -------
    numpy.array
        Nx2 array of destination points
    """
    dstpts = src
    for tform in transformlist:
        if isinstance(tform, list):
            dstpts = estimate_dstpts(tform, dstpts)
        else:
            dstpts = tform.tform(dstpts)
    return dstpts


class NonLinearTransform(Transform):
    """
    render-python class that implements the mpicbg.trakem2.transform.nonLinearTransform class
    
    Parameters
    ----------
    dataString:str or None
        data string of transformation
    json:dict or NOne
        json compatible dictionary representation of the transformation

    Returns
    -------
    :class:`NonLinearTransform`
        a transform instance


    """

    className = 'mpicbg.trakem2.transform.nonLinearTransform'




    def __init__(self, dataString=None, json=None,transformId=None):
        if json is not None:
            self.from_dict(json)
        else:
            if dataString is not None:
                self._process_dataString(dataString)
        self.transformId = transformId

    def _process_dataString(self, dataString):
        # trailing whitespace in string.... for some reason
        fields = dataString.split(" ")[:-1]
        
        self.dimension = int(fields[0])
        self.length = int(fields[1])

        # last 2 fields are width and height
        self.width = int(fields[-2])
        self.height = int(fields[-1])
        
        data = np.array(fields[2:-2],dtype='float32')
        self.beta=data[0:2*self.length].reshape(self.length,2)
        if not (self.beta.shape[0]==self.length):
            raise RenderError("not correct number of coefficents")

        # normMean and normVar follow
        self.normMean = data[self.length*2:self.length*3]
        self.normVar = data[self.length*3:self.length*4]
        if not (self.normMean.shape[0]==self.length):
            raise RenderError("incorrect number of normMean coefficents")
        if not (self.normVar.shape[0]==self.length):
            raise RenderError("incorrect number of normVar coefficents")

    def kernelExpand(self,src):
        """creates an expanded representation of the x,y src points in a polynomial form

        Parameters
        ----------
        points : numpy.array
            a Nx2 array of x,y points

        Returns
        -------
        numpy.array
            a (N x self.length) array of coefficents
        """
        x = src[:, 0]
        y = src[:, 1]
        
        expanded = np.zeros([len(x), self.length])
        pidx = 0
        for i in range(1, self.dimension + 1):
            for j in range(i, -1, -1):
                expanded[:, pidx] = (
                    np.power(x, j) * np.power(y, i - j))
                pidx += 1


        expanded[:, :-1] = (expanded[:, :-1] - self.normMean[:-1]) / self.normVar[:-1]
        expanded[:, -1] = 100.0
        return expanded

    def tform(self, src):
        """transform a set of points through this transformation

        Parameters
        ----------
        points : numpy.array
            a Nx2 array of x,y points

        Returns
        -------
        numpy.array
            a Nx2 array of x,y points after transformation
        """

        # final double[] featureVector = kernelExpand(position);
        # return multiply(beta, featureVector);
        nsrc = np.array(src,dtype=np.float64)
        featureVector = self.kernelExpand(nsrc)

        dst = np.zeros(src.shape)
        for i in range(0, featureVector.shape[1]):
            dst[:, 0] =  dst[:, 0] + (featureVector[:, i] * self.beta[i,0])
            dst[:, 1] = dst[:, 1] + (featureVector[:, i] * self.beta[i,1])
        return np.array(dst,dtype=src.dtype)
    
    @property
    def dataString(self):
        shapestring = '{} {}'.format(self.dimension, self.length)
        betastring = ' '.join([str(i).replace('e-0', 'e-').replace('e+0', 'e+')
                                for i in self.beta.ravel()]).replace('e', 'E')
        meanstring = ' '.join([str(i).replace('e-0', 'e-').replace('e+0', 'e+')
                                for i in self.normMean]).replace('e', 'E')
        varstring = ' '.join([str(i).replace('e-0', 'e-').replace('e+0', 'e+')
                              for i in self.normVar]).replace('e', 'E')
        dimstring = '{} {}'.format(self.height, self.width)
        return '{} {} {} {} {} '.format(
            shapestring, betastring, meanstring, varstring, dimstring)


def estimate_transformsum(transformlist, src=None, order=2):
    """pseudo-composition of transforms in list of transforms
    using source point transformation and a single estimation.
    Will produce an Affine Model if all input transforms are Affine,
    otherwise will produce a Polynomial of specified order

    Parameters
    ----------
    transformlist : :obj:`list` of :obj:`Transform`
        list of transform objects that implement tform
    src : numpy.array
        Nx2 array of source points for estimation
    order : int
        order of Polynomial output if transformlist
        inputs are non-Affine
    Returns
    -------
    :class:`AffineModel` or :class:`Polynomial2DTransform`
        best estimate of transformlist in a single transform of this order
    """
    def flatten(l):
        """generator-iterator to flatten deep lists of lists"""
        for i in l:
            if (isinstance(i, Iterable) and not
                    isinstance(i, basestring)):
                for sub in flatten(i):
                    yield sub
            else:
                yield i

    dstpts = estimate_dstpts(transformlist, src)
    tforms = flatten(transformlist)
    if all([tform.className == AffineModel.className
            for tform in tforms]):
        am = AffineModel()
        am.estimate(A=src, B=dstpts, return_params=False)
        return am
    return Polynomial2DTransform(src=src, dst=dstpts, order=order)
