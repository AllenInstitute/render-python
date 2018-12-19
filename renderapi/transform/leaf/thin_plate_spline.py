import numpy as np
from renderapi.errors import RenderError, EstimationError
from renderapi.utils import encodeBase64, decodeBase64
from .transform import Transform
import scipy.spatial
__all__ = ['ThinPlateSplineTransform']


class ThinPlateSplineTransform(Transform):
    """
    render-python class that can hold a dataString for
    mpicbg.trakem2.transform.ThinPlateSplineTransform class.
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
    :class:`ThinPlateSplineTransform`
        a transform instance
    """

    className = 'mpicbg.trakem2.transform.ThinPlateSplineTransform'

    def __init__(self, dataString=None, json=None, transformId=None,
                 labels=None):
        if json is not None:
            self.from_dict(json)
        else:
            if dataString is not None:
                self._process_dataString(dataString)
            self.labels = labels
            self.transformId = transformId
            self.className = (
                'mpicbg.trakem2.transform.ThinPlateSplineTransform')

    def _process_dataString(self, dataString):
        fields = dataString.split(" ")

        self.ndims = int(fields[1])
        self.nLm = int(fields[2])

        if fields[3] != "null":
            try:
                values = decodeBase64(fields[3])
                self.aMtx = values[0:self.ndims*self.ndims].reshape(
                                             self.ndims, self.ndims)
                self.bVec = values[self.ndims*self.ndims:]
            except ValueError:
                raise RenderError(
                    "inconsistent sizes and array lengths, \
                     in ThinPlateSplineTransform dataString")
        else:
            self.aMtx = None
            self.bVec = None

        try:
            values = decodeBase64(fields[4])
            self.srcPts = values[0:self.ndims*self.nLm].reshape(
                                           self.ndims, self.nLm, order='F')
            self.dMtxDat = values[self.ndims*self.nLm:].reshape(
                                           self.ndims, self.nLm, order='C')
        except ValueError:
            raise RenderError(
                "inconsistent sizes and array lengths, \
                 in ThinPlateSplineTransform dataString")

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
        return self.apply(points)

    def apply(self, points):
        if not hasattr(self, 'dMtxDat'):
            return points

        result = points + self.computeDeformationContribution(points)
        if self.aMtx is not None:
            result += self.aMtx.dot(points.transpose()).transpose()
        if self.bVec is not None:
            result += self.bVec

        return result

    def computeDeformationContribution(self, points):
        disp = scipy.spatial.distance.cdist(
                points,
                self.srcPts.transpose(),
                metric='sqeuclidean')
        disp *= np.ma.log(np.sqrt(disp)).filled(0.0)
        return disp.dot(self.dMtxDat.transpose())

    def gradient_descent(
            self,
            pts,
            gamma=1.0,
            precision=0.0001,
            max_iters=1000):
        """based on https://en.wikipedia.org/wiki/Gradient_descent#Python
        Parameters
        ----------
        pts : numpy array
            a Nx2 array of x,y points
        gamma : float
            step size is gamma fraction of current gradient
        precision : float
            criteria for stopping for differences between steps
        max_iters : int
            limit for iterations, error if reached
        Returns
        -------
        cur_pts : numpy array
            a Nx2 array of x,y points, estimated inverse of pt
        """
        cur_pts = np.copy(pts)
        prev_pts = np.copy(pts)
        step_size = 1
        iters = 0
        while (step_size > precision) & (iters < max_iters):
            prev_pts[:, :] = cur_pts[:, :]
            cur_pts -= gamma*(self.apply(prev_pts) - pts)
            step_size = np.linalg.norm(cur_pts - prev_pts, axis=1).max()
            iters += 1
        if iters == max_iters:
            raise EstimationError(
                    'gradient descent for inversion of ThinPlateSpline '
                    'reached maximum iterations: %d' % max_iters)
        return cur_pts

    def inverse_tform(
            self,
            points,
            gamma=1.0,
            precision=0.0001,
            max_iters=1000):
        """transform a set of points through the inverse of this transformation
        Parameters
        ----------
        points : numpy.array
            a Nx2 array of x,y points
        gamma : float
            step size is gamma fraction of current gradient
        precision : float
            criteria for stopping for differences between steps
        max_iters : int
            limit for iterations, error if reached
        Returns
        -------
        numpy.array
            a Nx2 array of x,y points after inverse transformation
        """
        newpts = self.gradient_descent(
                points,
                gamma=gamma,
                precision=precision,
                max_iters=max_iters)
        return newpts

    @staticmethod
    def fit(A, B, computeAffine=True):
        """function to fit this transform given the corresponding sets of points A & B

        Parameters
        ----------
        A : numpy.array
            a Nx2 matrix of source points
        B : numpy.array
            a Nx2 matrix of destination points

        Returns
        -------
        dMatrix : numpy.array
            ndims x nLm
        aMatrix : numpy.array
            ndims x ndims, affine matrix
        bVector : numpy.array
            ndims x 1, translation vector
        """

        if not all([A.shape[0] == B.shape[0], A.shape[1] == B.shape[1] == 2]):
            raise EstimationError(
                'shape mismatch! A shape: {}, B shape {}'.format(
                    A.shape, B.shape))

        # build displacements
        ndims = B.shape[1]
        nLm = B.shape[0]
        y = (B - A).flatten()

        # compute K
        # tempting to matricize this, but, nLm x nLm can get big
        # settle for vectorize
        kMatrix = np.zeros((ndims * nLm, ndims * nLm))
        for i in range(nLm):
            r = np.linalg.norm(A[i, :] - A, axis=1)
            nrm = np.zeros_like(r)
            ind = np.argwhere(r > 1e-8)
            nrm[ind] = r[ind] * r[ind] * np.log(r[ind])
            kMatrix[i * ndims, 0::2] = nrm
            kMatrix[(i * ndims + 1)::2, 1::2] = nrm

        # compute L
        lMatrix = kMatrix
        if computeAffine:
            pMatrix = np.tile(np.eye(ndims), (nLm, ndims + 1))
            for d in range(ndims):
                pMatrix[0::2, d*ndims] = A[:, d]
                pMatrix[1::2, d*ndims + 1] = A[:, d]
            lMatrix = np.zeros(
                    (ndims * (nLm + ndims + 1), ndims * (nLm + ndims + 1)))
            lMatrix[
                    0: pMatrix.shape[0],
                    kMatrix.shape[1]: kMatrix.shape[1] + pMatrix.shape[1]] = \
                pMatrix
            pMatrix = np.transpose(pMatrix)
            lMatrix[
                    kMatrix.shape[0]: kMatrix.shape[0] + pMatrix.shape[0],
                    0: pMatrix.shape[1]] = pMatrix
            lMatrix[0: ndims * nLm, 0: ndims * nLm] = kMatrix
            y = np.append(y, np.zeros(ndims * (ndims + 1)))

        wMatrix = np.linalg.solve(lMatrix, y)

        dMatrix = np.reshape(wMatrix[0: ndims * nLm], (ndims, nLm), order='F')
        aMatrix = None
        bVector = None
        if computeAffine:
            aMatrix = np.reshape(
                    wMatrix[ndims * nLm: ndims * nLm + ndims * ndims],
                    (ndims, ndims),
                    order='F')
            bVector = wMatrix[ndims * nLm + ndims * ndims:]

        return dMatrix, aMatrix, bVector

    def estimate(self, A, B, computeAffine=True):
        """method for setting this transformation with the best fit
        given the corresponding points A,B
        Parameters
        ----------
        A : numpy.array
            a Nx2 matrix of source points
        B : numpy.array
            a Nx2 matrix of destination points
        computeAffine: boolean
            whether to include an affine computation
        """

        self.dMtxDat, self.aMtx, self.bVec = self.fit(
                A, B, computeAffine=computeAffine)
        (self.nLm, self.ndims) = B.shape
        self.srcPts = np.transpose(A)

    @property
    def dataString(self):
        header = 'ThinPlateSplineR2LogR {} {}'.format(self.ndims, self.nLm)

        if self.aMtx is not None:
            blk1 = np.concatenate((self.aMtx.flatten(), self.bVec))
            b64_1 = encodeBase64(blk1)
        else:
            b64_1 = "null"

        blk2 = np.concatenate((
            self.srcPts.flatten(order='F'),
            self.dMtxDat.flatten(order='C')))
        b64_2 = encodeBase64(blk2)

        return '{} {} {}'.format(header, b64_1, b64_2)
