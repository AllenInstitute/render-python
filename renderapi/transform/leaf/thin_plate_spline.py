#!/usr/bin/env python
import logging
import sys

import numpy as np
import scipy.spatial
import scipy.special

from renderapi.errors import RenderError, EstimationError
from renderapi.utils import encodeBase64, decodeBase64
from renderapi.transform.leaf.transform import Transform


__all__ = ['ThinPlateSplineTransform']

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))


def _tps_kernel_from_sqdist(d2, out=None, eps=None):
    """Convert squared distances to U(r) = r^2 log(r)

    Parameters
    ----------
    d2 : numpy.ndarray
        squared euclidean distances
    out : numpy.ndarray, optional
        output array; may be the same array as d2

    Returns
    -------
    numpy.ndarray
        TPS radial basis values
    """
    if out is None:
        out = np.array(d2, dtype=np.float64, copy=True)
    elif out is not d2:
        np.copyto(out, d2)

    if eps is not None:
        eps2 = eps * eps
        out[out <= eps2] = 0.0

    scipy.special.xlogy(out, out, out=out)
    out *= 0.5

    return out


def _tps_kernel(x, y, out=None, eps=None):
    """Compute the TPS kernel between two Nx2/Mx2 point arrays

    Parameters
    ----------
    x : (N, 2) ndarray
    y : (M, 2) ndarray
    out : (N, M) ndarray, optional
        output array, buffer

    Returns
    -------
    (N, M) ndarray
        K[i, j] = U(||x[i] - y[j]||).
    """
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)

    if out is None:
        out = scipy.spatial.distance.cdist(
            x,
            y,
            metric="sqeuclidean",
        )
    else:
        scipy.spatial.distance.cdist(
            x,
            y,
            metric="sqeuclidean",
            out=out,
        )

    return _tps_kernel_from_sqdist(
        out,
        out=out,
        eps=eps
    )


def _legacy_fit_tps(A, B, computeAffine=True):
    """function to fit this transform given the corresponding sets of points A & B

    Parameters
    ----------
    A : numpy.array
        a Nx2 matrix of source points
    B : numpy.array
        a Nx2 matrix of destination points
    computeAffine: bool
        include affine TPS terms

    Returns
    -------
    dMatrix : numpy.array
        ndims x nLm
    aMatrix : numpy.array
        ndims x ndims, affine matrix
    bVector : numpy.array
        ndims x 1, translation vector
    """
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


@staticmethod
def _fill_tps_kernel(
        K,
        points,
        block_size=512,
        eps=None):

    points = np.asarray(points, dtype=np.float64)
    n = points.shape[0]

    block_size = min(block_size, n)

    # 1d buffer lets every partial block be reshaped C-contiguously
    work = np.empty(
        block_size * block_size,
        dtype=np.float64,
    )

    for i0 in range(0, n, block_size):
        i1 = min(i0 + block_size, n)
        ni = i1 - i0

        for j0 in range(i0, n, block_size):
            j1 = min(j0 + block_size, n)
            nj = j1 - j0

            block = work[:ni * nj].reshape(ni, nj)

            _tps_kernel(
                points[i0:i1],
                points[j0:j1],
                out=block,
                eps=eps,
            )

            K[i0:i1, j0:j1] = block

            if i0 != j0:
                K[j0:j1, i0:i1] = block.T


def _reconstruct_normalized_tps_fit(
        W, C, An,
        center, scale):
    # Normalized evaluation:
    #   f(x) =
    #       sum_i W_i U(||(x - A_i) / scale||)
    #       + ((x - center) / scale) @ Cxy
    #       + C0
    #
    # Legacy evaluation:
    #   f(x) =
    #       sum_i Wlegacy_i U(||x - A_i||)
    #       + x @ Clegacy
    #       + blegacy

    scale2 = scale * scale

    W_legacy = W / scale2

    Cxy = C[:2]
    C0 = C[2]

    Cxy_legacy = Cxy / scale

    # center correction
    b_legacy = C0 - (center / scale) @ Cxy

    # kernel scaling introduces a constant:
    #   U(r / s) = U(r) / s² - log(s) r² / s²
    #
    # Because TPS weights satisfy:
    #   sum(W_i) = 0
    #   sum(W_i * A_i) = 0
    #
    # r² term becomes constant; add to translation
    kernel_constant = (
        -np.log(scale)
        * np.sum(
            W * np.sum(An * An, axis=1)[:, None],
            axis=0,
        )
    )

    b_legacy += kernel_constant

    dMatrix = W_legacy.T
    aMatrix = Cxy_legacy.T
    bVector = b_legacy.copy()

    return dMatrix, aMatrix, bVector



def _fit_tps(
        A, B,
        computeAffine=True,
        legacy_output=True,
        regularization=0.0,
        block_size=512):
    """
    Fit 2d thin-plate spline using corresponding points A and B.

    Parameters
    ----------
    A : numpy.array
        a Nx2 matrix of source points
    B : numpy.array
        a Nx2 matrix of destination points
    computeAffine: bool
        include affine TPS terms
    legacy_output : bool
        If True, convert coefficients back to the original coordinate
        convention so existing transform/evaluation code can use them
        unchanged
        If False, coefficients operate on normalized coordinates and the
        normalization parameters are also returned.
    regularization : float
        diagonal TPS regularization
    block_size : int
         block size used to construct kernel
    Returns
    -------
    if legacy_output=True:
        dMatrix : numpy.array
            ndims x nLm
        aMatrix : numpy.array
            ndims x ndims, affine matrix
        bVector : numpy.array
            ndims x 1, translation vector

    if legacy_output=False:
        dMatrix : numpy.array
            ndims x nLm
        aMatrix : numpy.array
            ndims x ndims, affine matrix
        bVector : numpy.array
            ndims x 1, translation vector
        center: numpy.ndarray
            center used for normalization
        scale: numpy.ndarray
            scale used for normalization
    """
    n = A.shape[0]
    displacement = B - A

    # Normalize source coordinates to improve conditioning.
    center = A.mean(axis=0)

    Ac = A - center
    scale = np.sqrt(np.mean(np.sum(Ac * Ac, axis=1)))

    if not np.isfinite(scale) or scale <= np.finfo(np.float64).eps:
        raise EstimationError("Degenerate source control-point coordinates")

    An = Ac / scale

    if not computeAffine and legacy_output:
        K = np.empty((n, n), dtype=np.float64)
        _fill_tps_kernel(
            K,
            A,
            block_size=block_size,
        )

        if regularization:
            K.flat[::n + 1] += regularization

        W = scipy.linalg.solve(
            K,
            displacement.copy(),
            assume_a="sym",
            overwrite_a=True,
            overwrite_b=True,
            check_finite=False,
        )

        return W.T, None, None

    if not computeAffine and not legacy_output:
        K = np.empty((n, n), dtype=np.float64)
        _fill_tps_kernel(K, An, block_size=block_size)

        if regularization:
            K.flat[::n + 1] += regularization

        W = scipy.linalg.solve(
            K,
            displacement.copy(),
            assume_a="sym",
            check_finite=False,
            overwrite_a=True,
            overwrite_b=True,
        )

        return W.T, None, None, center, scale

    # [ K   P ] [ W ] = [ displacement ]
    # [ P^T 0 ] [ C ]   [      0       ]
    L = np.zeros((n + 3, n + 3), dtype=np.float64)

    _fill_tps_kernel(
        L[:n, :n],
        An,
        block_size=block_size,
    )

    if regularization:
        idx = np.arange(n)
        L[idx, idx] += regularization

    # Normalized affine coordinates.
    L[:n, n] = An[:, 0]
    L[:n, n + 1] = An[:, 1]
    L[:n, n + 2] = 1.0

    L[n:, :n] = L[:n, n:].T

    rhs = np.zeros((n + 3, 2), dtype=np.float64)
    rhs[:n] = displacement

    coefficients = scipy.linalg.solve(
        L,
        rhs,
        assume_a="sym",
        overwrite_a=True,
        overwrite_b=True,
        check_finite=False,
    )
    W = coefficients[:n]
    C = coefficients[n:]

    if not legacy_output:
        dMatrix = W.T
        aMatrix = C[:2].T
        bVector = C[2].copy()

        return (
            dMatrix,
            aMatrix,
            bVector,
            center,
            scale,
        )

    return _reconstruct_normalized_tps_fit(W, C, An, center, scale)


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

    def apply(self, points, block_size=128):
        points = np.asarray(points)

        if not hasattr(self, "dMtxDat"):
            return points

        result = self.computeDeformationContribution(
            points,
            block_size=block_size,
        )

        result += points

        if self.aMtx is not None:
            result += points @ self.aMtx.T

        if self.bVec is not None:
            result += self.bVec

        return result

    def computeDeformationContribution(self, points, block_size=128):
        points = np.asarray(points, dtype=np.float64)

        src = np.ascontiguousarray(
            self.srcPts.T,
            dtype=np.float64,
        )
        weights = np.ascontiguousarray(
            self.dMtxDat.T,
            dtype=np.float64,
        )

        n_points = points.shape[0]
        n_control = src.shape[0]

        result = np.empty((n_points, 2), dtype=np.float64)

        # Reused Mblock x Ncontrol kernel buffer.
        buffer = np.empty(
            (min(block_size, n_points), n_control),
            dtype=np.float64,
        )

        for i0 in range(0, n_points, block_size):
            i1 = min(i0 + block_size, n_points)
            n = i1 - i0

            kernel = buffer[:n]

            _tps_kernel(
                        points[i0:i1],
                        src,
                        out=kernel,
                    )

            result[i0:i1] = kernel @ weights

        return result

    def _inverse_newton_step(
            self,
            current,
            target,
            src,
            weights,
            linear,
            translation,
            damping=1.0,
            block_size=64):
        """vectorized newton iteration step for evaluating inverse TPS

        Parameters
        ----------
        current : (N, 2) ndarray
            Current estimate of inverse coordinates. Modified in-place.
        target : (N, 2) ndarray
            Desired transformed coordinates.
        src : (M, 2) ndarray
            TPS source control points.
        weights : (M, 2) ndarray
            TPS nonlinear weights.
        linear : (2, 2) ndarray
            Identity + TPS affine matrix.
        translation : (2,) ndarray
            TPS translation.
        damping : float
            Newton step multiplier.
        block_size : int
            Number of query points processed at once.

        Returns
        -------
        float
            Maximum squared update magnitude.
        """
        max_step2 = 0.0

        for i0 in range(0, current.shape[0], block_size):
            i1 = min(i0 + block_size, current.shape[0])

            p = current[i0:i1]
            t = target[i0:i1]

            dx = p[:, 0, None] - src[None, :, 0]
            dy = p[:, 1, None] - src[None, :, 1]

            r2 = dx * dx
            r2 += dy * dy

            # log(r^2), with log(0) -> 0
            log_r2 = np.empty_like(r2)
            log_r2.fill(0.0)
            np.log(
                r2,
                out=log_r2,
                where=r2 > 0.0,
            )

            # TPS kernel:
            #
            # U(r) = r^2 log(r)
            r2 *= log_r2
            r2 *= 0.5

            # evaluate transform
            f = p @ linear.T
            f += translation
            f += r2 @ weights

            # reuse f for residual
            f -= t

            rx = f[:, 0]
            ry = f[:, 1]

            # TPS derivative:
            #     dU/dx = dx * (log(r^2) + 1)
            #     dU/dy = dy * (log(r^2) + 1)
            log_r2 += 1.0
            dx *= log_r2
            dy *= log_r2

            jx = dx @ weights
            jy = dy @ weights

            j00 = linear[0, 0] + jx[:, 0]
            j10 = linear[1, 0] + jx[:, 1]

            j01 = linear[0, 1] + jy[:, 0]
            j11 = linear[1, 1] + jy[:, 1]

            # vectorized inverse of Jacobian
            det = j00 * j11 - j01 * j10

            det_scale = (
                np.abs(j00 * j11)
                + np.abs(j01 * j10)
                + 1.0
            )

            good = np.abs(det) > 1e-12 * det_scale

            # nearly singular local Jacobian becomes fixed-point residual
            sx = rx.copy()
            sy = ry.copy()

            sx[good] = (
                j11[good] * rx[good]
                - j01[good] * ry[good]
            ) / det[good]

            sy[good] = (
                -j10[good] * rx[good]
                + j00[good] * ry[good]
            ) / det[good]

            sx *= damping
            sy *= damping

            p[:, 0] -= sx
            p[:, 1] -= sy

            step2 = sx * sx + sy * sy
            max_step2 = max(
                max_step2,
                float(step2.max()),
            )
        return max_step2

    @staticmethod
    def _newton_block_size(
            n_points,
            n_control,
            target_bytes=8 * 1024**2,
            max_block=128,
            min_block=16):
        """helper method to determine newton iteration block size"""
        bytes_per_row = 4 * n_control * np.dtype(np.float64).itemsize

        block_size = max(
            min_block,
            min(
                max_block,
                n_points,
                target_bytes // bytes_per_row,
            ),
        )

        # Cache-friendly multiple where possible.
        if block_size >= 32:
            block_size = (block_size // 16) * 16

        return max(min_block, block_size)

    def _inverse_newton(
            self,
            points,
            precision=0.0001,
            max_iters=100,
            damping=1.0,
            block_size=None):
        """approximate TPS inversion with newton iteration"""
        target = np.ascontiguousarray(
            points,
            dtype=np.float64,
        )

        src = np.ascontiguousarray(
            self.srcPts.T,
            dtype=np.float64,
        )

        weights = np.ascontiguousarray(
            self.dMtxDat.T,
            dtype=np.float64,
        )

        linear = np.eye(2, dtype=np.float64)

        if self.aMtx is not None:
            linear += self.aMtx

        translation = (
            np.zeros(2, dtype=np.float64)
            if self.bVec is None
            else np.asarray(self.bVec, dtype=np.float64)
        )

        # Start with the inverse of the affine component.
        try:
            current = np.linalg.solve(
                linear,
                (target - translation).T,
            ).T

            current = np.ascontiguousarray(current)

        except np.linalg.LinAlgError:
            current = target.copy()

        if block_size is None:
            block_size = self._newton_block_size(
                target.shape[0],
                src.shape[0],
            )

        precision2 = precision * precision

        for _ in range(max_iters):
            step2 = self._inverse_newton_step(
                current,
                target,
                src,
                weights,
                linear,
                translation,
                damping=damping,
                block_size=block_size,
            )

            if step2 <= precision2:
                return current

        raise EstimationError(
            "Newton inversion of ThinPlateSplineTransform "
            f"reached maximum iterations: {max_iters}"
        )

    def gradient_descent(
            self,
            pts,
            gamma=1.0,
            precision=0.0001,
            max_iters=1000):
        """fixed-point approximation of inverse tps
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
        pts = np.asarray(pts, dtype=np.float64)
        cur_pts = pts.copy()

        precision2 = precision * precision
        gamma2 = gamma * gamma

        for _ in range(max_iters):
            residual = self.apply(cur_pts) - pts

            cur_pts -= gamma * residual

            step2 = gamma2 * np.max(
                np.einsum("ij,ij->i", residual, residual)
            )

            if step2 <= precision2:
                return cur_pts

        raise EstimationError(
            "gradient descent for inversion of ThinPlateSpline "
            f"reached maximum iterations: {max_iters}"
        )


    def inverse_tform(
            self,
            points,
            gamma=1.0,
            precision=0.0001,
            max_iters=1000,
            method="fixed"
        ):
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
        method: str
            convergence method for inversion: "newton" for newton iteration or "fixed" for gradient descent
        Returns
        -------
        numpy.array
            a Nx2 array of x,y points after inverse transformation
        """
        if method == "newton":
            return self._inverse_newton(
                points,
                precision=precision,
                max_iters=min(max_iters, 100),
            )

        if method == "fixed":
            return self.gradient_descent(
                points,
                gamma=gamma,
                precision=precision,
                max_iters=max_iters,
            )

        raise ValueError(
            f"unknown inverse method: {method}"
        )

    @staticmethod
    def fit(A, B, computeAffine=True, use_legacy=False):
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
        A = np.ascontiguousarray(A, dtype=np.float64)
        B = np.ascontiguousarray(B, dtype=np.float64)

        if (
            A.ndim != 2
            or B.ndim != 2
            or A.shape != B.shape
            or A.shape[1] != 2
        ):
            raise EstimationError(
                f"shape mismatch! A shape: {A.shape}, B shape: {B.shape}"
            )
        if not np.isfinite(A).all() or not np.isfinite(B).all():
            raise EstimationError("A and B must contain finite values")

        if use_legacy:
            return _legacy_fit_tps(A, B, computeAffine=computeAffine)
        return _fit_tps(A, B, computeAffine=computeAffine)


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
