from .transform import Transform, logger
from .affine_models import AffineModel
import numpy as np
from .common import calc_first_order_properties
from renderapi.errors import ConversionError, EstimationError, RenderError

try:
    from scipy.linalg import svd, LinAlgError
except ImportError as e:
    logger.info(e)
    logger.info('scipy-based linalg may or may not lead '
                'to better parameter fitting')
    from numpy.linalg import svd
    from numpy.linalg.linalg import LinAlgError
__all__ = [
        'Polynomial2DTransform', 'NonLinearCoordinateTransform',
        'NonLinearTransform', 'LensCorrection']


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
                 labels=None, transformId=None, json=None,
                 force_shear='x', **kwargs):
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
        self.force_shear = force_shear
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
            self.transformId = transformId
            self.labels = labels

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

    def calc_properties(self):
        if self.order == 0:
            return 1.0, 1.0, 0.0, 0.0, 0.0
        return calc_first_order_properties(
                self.params[:, 1:3],
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
        return tuple(self.params[:, 0])

    @property
    def rotation(self):
        """counter-clockwise rotation"""
        sx, sy, cx, cy, theta = self.calc_properties()
        return theta

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
        halfway = int(len(raveled_params) / 2)
        return np.array(
            [[float(d) for d in raveled_params[:halfway]],
             [float(d) for d in raveled_params[halfway:]]])

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


class NonLinearCoordinateTransform(Transform):
    """
    render-python class that implements the
    mpicbg.trakem2.transform.NonLinearCoordinateTransform class

    Parameters
    ----------
    dataString: str or None
        data string of transformation
    labels : list of str
        list of labels to give this transform
    json: dict or None
        json compatible dictionary representation of the transformation

    Returns
    -------
    :class:`NonLinearTransform`
        a transform instance


    """

    className = 'mpicbg.trakem2.transform.NonLinearCoordinateTransform'

    def __init__(self, dataString=None, json=None, transformId=None,
                 labels=None):
        if json is not None:
            self.from_dict(json)
        else:
            if dataString is not None:
                self._process_dataString(dataString)
            if labels is not None:
                self.labels = labels
            self.transformId = transformId
            self.className = (
                'mpicbg.trakem2.transform.NonLinearCoordinateTransform')

    def _process_dataString(self, dataString):

        fields = dataString.split(" ")

        self.dimension = int(fields[0])
        self.length = int(fields[1])

        # cutoff whitespace if there
        fields = fields[0:2 + 4 * self.length + 2]
        # last 2 fields are width and height
        self.width = int(fields[-2])
        self.height = int(fields[-1])

        data = np.array(fields[2:-2], dtype='float32')
        try:
            self.beta = data[0:2 * self.length].reshape(self.length, 2)
        except ValueError as e:
            raise RenderError(
                'Incorrect number of coefficients in '
                'NonLinearCoordinateTransform. msg: {}'.format(e))
        if not (self.beta.shape[0] == self.length):
            raise RenderError("not correct number of coefficents")

        # normMean and normVar follow
        self.normMean = data[self.length * 2:self.length * 3]
        self.normVar = data[self.length * 3:self.length * 4]
        if not (self.normMean.shape[0] == self.length):
            raise RenderError(
                "incorrect number of normMean coefficents "
                "{} != length {}".format(self.normMean.shape[0], self.length))
        if not (self.normVar.shape[0] == self.length):
            raise RenderError(
                "incorrect number of normVar coefficents "
                "{} != {}".format(self.normVar.shape[0], self.length))

    def kernelExpand(self, src, normMean=None, normVar=None):
        """creates an expanded representation of the x,y
        src points in a polynomial form

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

        if normMean is None:
            normMean = self.normMean
        if normVar is None:
            normVar = self.normVar

        expanded[:, :-1] = ((expanded[:, :-1] - normMean[:-1]) /
                            normVar[:-1])
        expanded[:, -1] = 100.0
        return expanded

    def fit(self, A, B):
        """function to fit this transform given the corresponding sets of points A & B
        Parameters
        ----------
        A : numpy.array
            a Nx2 matrix of source points
        B : numpy.array
            a Nx2 matrix of destination points

        Returns
        -------
        beta
            a self.lengthx2 matrix with polynomial factors
        normMean
            a self.length vector of expanded means
        normVar
            a self.length vector of expanded standard deviations
        """
        if not all([A.shape[0] == B.shape[0], A.shape[1] == B.shape[1] == 2]):
            raise EstimationError(
                'shape mismatch! A shape: {}, B shape {}'.format(
                    A.shape, B.shape))

        normMean = np.zeros(self.length).astype('float')
        normVar = np.ones(self.length).astype('float')
        src_exp = self.kernelExpand(A, normMean=normMean, normVar=normVar)
        normMean = src_exp.mean(0)
        normVar = src_exp.std(0)  # poorly named variable
        src_exp = self.kernelExpand(A, normMean=normMean, normVar=normVar)

        xcoeff, xresiduals, xrank, xs = np.linalg.lstsq(src_exp, B[:, 0])
        ycoeff, yresiduals, yrank, ys = np.linalg.lstsq(src_exp, B[:, 1])

        beta = np.zeros((self.length, 2))
        beta[:, 0] = xcoeff
        beta[:, 1] = ycoeff

        return beta, normMean, normVar

    def estimate(self, A, B, ndim=None, return_params=True, **kwargs):
        """method for setting this transformation with the best fit
        given the corresponding points A,B

        Parameters
        ----------
        A : numpy.array
            a Nx2 matrix of source points
        B : numpy.array
            a Nx2 matrix of destination points
        return_params : boolean
            whether to return the dataString
        **kwargs
            keyword arguments to pass to self.fit

        Returns
        -------
        dataString
        """

        beta, normMean, normVar = self.fit(A, B)
        self.beta = beta
        self.normMean = normMean
        self.normVar = normVar

        if return_params:
            return self.dataString

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
        nsrc = np.array(src, dtype=np.float64)
        featureVector = self.kernelExpand(nsrc)

        dst = np.zeros(src.shape)
        for i in range(0, featureVector.shape[1]):
            dst[:, 0] = dst[:, 0] + (featureVector[:, i] * self.beta[i, 0])
            dst[:, 1] = dst[:, 1] + (featureVector[:, i] * self.beta[i, 1])
        return np.array(dst, dtype=src.dtype)

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


class NonLinearTransform(NonLinearCoordinateTransform):
    className = 'mpicbg.trakem2.transform.nonLinearTransform'


class LensCorrection(NonLinearCoordinateTransform):
    """
    a placeholder for the lenscorrection transform, same as NonLinearTransform
    for now
    """
    className = 'lenscorrection.NonLinearTransform'
