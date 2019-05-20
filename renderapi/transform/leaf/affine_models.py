from .transform import Transform, logger
from .common import calc_first_order_properties
import numpy as np
from renderapi.errors import ConversionError, EstimationError

try:
    from scipy.linalg import svd, LinAlgError
except ImportError as e:
    logger.info(e)
    logger.info('scipy-based linalg may or may not lead '
                'to better parameter fitting')
    from numpy.linalg import svd
    from numpy.linalg.linalg import LinAlgError
__all__ = [
        'AffineModel', 'TranslationModel',
        'SimilarityModel', 'RigidModel']


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
    labels : list of str
        list of labels to give this transform
    M : numpy.array
        3x3 numpy array representing 2d Affine with homogeneous coordinates
        populates with values from M00, M01, M10, M11, B0, B1 with load_M()

    """

    className = 'mpicbg.trakem2.transform.AffineModel2D'

    def __init__(self, M00=1.0, M01=0.0, M10=0.0, M11=1.0, B0=0.0, B1=0.0,
                 transformId=None, labels=None, json=None, force_shear='x'):
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
        labels : list of str
            list of labels to give this transform
        json : dict
            json compatible representation of this transform
            (will supersede all other parameters if not None)

        """
        self.force_shear = force_shear
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
            self.labels = labels
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
    def fit(A, B, return_all=False):
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
        if return_all:
            return Tvec, residuals, rank, s
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
        A = self.M.dot(model.M)
        newmodel = AffineModel(
                A[0, 0], A[0, 1], A[1, 0],
                A[1, 1], A[0, 2], A[1, 2])
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

    def calc_properties(self):
        return calc_first_order_properties(
                self.M[0:2, 0:2],
                force_shear=self.force_shear)

    @property
    def scale(self):
        """tuple of scale for x, y"""
        sx, sy, cx, cy, theta = self.calc_properties()
        return (sx, sy)

    @property
    def shear(self):
        """shear"""
        sx, sy, cx, cy, theta = self.calc_properties()
        if self.force_shear == 'x':
            return cx
        else:
            return cy

    @property
    def translation(self):
        """tuple of translation in x, y"""
        return tuple(self.M[:2, 2])

    @property
    def rotation(self):
        """counter-clockwise rotation"""
        sx, sy, cx, cy, theta = self.calc_properties()
        return theta

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
    labels : list of str
            list of labels to give this transform
    M : numpy.array
        3x3 numpy array representing 2d Affine with homogeneous coordinates
        populates with values from M00, M01, M10, M11, B0, B1 with load_M()
    """

    className = 'mpicbg.trakem2.transform.TranslationModel2D'

    def __init__(self, *args, **kwargs):
        super(TranslationModel, self).__init__(*args, **kwargs)

    def _process_dataString(self, dataString):
        """expected dataString is 'tx ty'"""
        tx, ty = map(float, dataString.split(' '))
        self.B0 = tx
        self.B1 = ty
        self.M00 = 1
        self.M10 = 0
        self.M01 = 0
        self.M11 = 1
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
    labels : list of str
        list of labels to give this transform
    M : numpy.array
        3x3 numpy array representing 2d Affine with homogeneous coordinates
        populates with values from M00, M01, M10, M11, B0, B1 with load_M()

    """
    className = 'mpicbg.trakem2.transform.RigidModel2D'

    def __init__(self, *args, **kwargs):
        super(RigidModel, self).__init__(*args, **kwargs)

    def _process_dataString(self, dataString):
        """expected datastring is 'theta tx ty'"""
        theta, tx, ty = map(float, dataString.split(' '))
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
    labels : list of str
        list of labels to give this transform
    M : numpy.array
        3x3 numpy array representing 2d Affine with homogeneous coordinates
        populates with values from M00, M01, M10, M11, B0, B1 with load_M()

    """
    className = 'mpicbg.trakem2.transform.SimilarityModel2D'

    def __init__(self, *args, **kwargs):
        super(SimilarityModel, self).__init__(*args, **kwargs)

    def _process_dataString(self, dataString):
        """expected datastring is 's theta tx ty'"""
        s, theta, tx, ty = map(float, dataString.split(' '))
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
