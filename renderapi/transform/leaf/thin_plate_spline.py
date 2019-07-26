import numpy as np
from renderapi.errors import RenderError, EstimationError
from renderapi.utils import encodeBase64, decodeBase64
from .transform import Transform
import scipy.spatial
import logging
import sys
__all__ = ['ThinPlateSplineTransform']


logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))


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

    @staticmethod
    def mesh_refine(
            new_src,
            old_src,
            old_dst,
            old_tf=None,
            computeAffine=True,
            tol=1.0,
            max_iter=50,
            nworst=10,
            niter=0):
        """recursive kernel for adaptive_mesh_estimate()
        Parameters
        ----------
        new_src : numpy.array
            Nx2 array of new control source points. Adapts during recursion.
            Seeded by adaptive_mesh_estimate.
        old_src : numpy.array
            Nx2 array of orignal control source points.
        old_dst : numpy.array
            Nx2 array of orignal control destination points.
        old_tf : ThinPlateSplineTransform
            transform constructed from old_src and old_dst, passed through
            recursion iterations. Created if None.
        computeAffine : boolean
            whether returned transform will have aMtx
        tol : float
            in units of pixels, how close should the points match
        max_iter: int
            some limit on how many recursive attempts
        nworst : int
            per iteration, the nworst matching srcPts will be added
        niter : int
            passed through the recursion for stopping criteria

        Returns
        -------
        ThinPlateSplineTransform
        """

        if old_tf is None:
            old_tf = ThinPlateSplineTransform()
            old_tf.estimate(old_src, old_dst, computeAffine=computeAffine)

        new_tf = ThinPlateSplineTransform()
        new_tf.estimate(
                new_src,
                old_tf.tform(new_src),
                computeAffine=computeAffine)
        new_dst = new_tf.tform(old_src)

        delta = np.linalg.norm(new_dst - old_dst, axis=1)
        ind = np.argwhere(delta > tol).flatten()

        if ind.size == 0:
            return new_tf

        if niter == max_iter:
            raise EstimationError(
                    "Max number of iterations ({}) reached in"
                    " ThinPlateSplineTransform.mesh_refine()".format(
                        max_iter))

        sortind = np.argsort(delta[ind])
        new_src = np.vstack((new_src, old_src[ind[sortind[0: nworst]]]))

        return ThinPlateSplineTransform.mesh_refine(
            new_src,
            old_src,
            old_dst,
            old_tf=old_tf,
            computeAffine=computeAffine,
            tol=tol,
            max_iter=max_iter,
            nworst=nworst,
            niter=(niter + 1))

    def adaptive_mesh_estimate(
            self,
            starting_grid=7,
            computeAffine=True,
            tol=1.0,
            max_iter=50,
            nworst=10):
        """method for creating a transform with fewer control points
        that matches the original transfom within some tolerance.
        Parameters
        ----------
        starting_grid : int
            estimate will start with an n x n grid
        computeAffine : boolean
            whether returned transform will have aMtx
        tol : float
            in units of pixels, how close should the points match
        max_iter: int
            some limit on how many recursive attempts
        nworst : int
            per iteration, the nworst matching srcPts will be added

        Returns
        -------
        ThinPlateSplineTransform
        """

        mn = self.srcPts.min(axis=1)
        mx = self.srcPts.max(axis=1)
        new_src = self.src_array(
                mn[0], mn[1], mx[0], mx[1], starting_grid, starting_grid)
        old_src = self.srcPts.transpose()
        old_dst = self.tform(old_src)

        return ThinPlateSplineTransform.mesh_refine(
                new_src,
                old_src,
                old_dst,
                old_tf=self,
                computeAffine=computeAffine,
                tol=tol,
                max_iter=max_iter,
                nworst=nworst,
                niter=0)

    @staticmethod
    def src_array(xmin, ymin, xmax, ymax, nx, ny):
        """create N x 2 array of regularly spaced points

        Parameters
        ----------
        xmin : float
            minimum of x grid
        ymin : float
            minimum of y grid
        xmax : float
            maximum of x grid
        ymax : float
            maximum of y grid
        nx : int
            number of points in x axis
        ny : int
            number of points in y axis

        Returns
        -------
        src : :class:`numpy.ndarray`
            (nx * ny) x 2 array of coordinated.

        """
        src = np.mgrid[xmin:xmax:nx*1j, ymin:ymax:ny*1j].reshape(2, -1).T
        return src

    def scale_coordinates(
            self,
            factor,
            ngrid=20,
            preserve_srcPts=False):
        """estimates a new ThinPlateSplineTransform from the current one
           in a scaled transform space.

        Parameters
        ----------
        factor : float
            the factor by which to scale the space
        ngrid : int
            number of points per axis for the estimation grid
        preserve_srcPts : bool
            one might want to keep the original scaled srcPts
            for example, if pts were made specially for a mask
            or a crack or fold

        Returns
        -------
        new_tform : :class:`renderapi.transform.ThinPlateSplineTransform`
            the new transform in the scaled space

        """

        new_tform = ThinPlateSplineTransform()
        computeAffine = True
        if self.aMtx is None:
            computeAffine = False

        mn = self.srcPts.min(axis=1)
        mx = self.srcPts.max(axis=1)
        src = self.src_array(mn[0], mn[1], mx[0], mx[1], ngrid, ngrid)

        if preserve_srcPts:
            # do not repeat close points
            dist = scipy.spatial.distance.cdist(
                    src,
                    self.srcPts.transpose(),
                    metric='euclidean')
            ind = np.invert(np.any(dist < 1e-3, axis=0))
            src = np.vstack((src, self.srcPts.transpose()[ind]))

        new_tform.estimate(
                src * factor,
                self.tform(src) * factor,
                computeAffine=computeAffine)

        return new_tform
