import numpy as np
from ..errors import RenderError
from ..utils import encodeBase64, decodeBase64
from .generalTransforms import Transform


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
                                           self.ndims, self.nLm, order='C')
            self.dMtxDat = values[self.ndims*self.nLm:].reshape(
                                           self.ndims, self.nLm, order='F')
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
        result = []
        for pt in points:
            result.append(self.apply(pt))

        return np.array(result)

    def apply(self, pt):
        if not hasattr(self, 'dMtxDat'):
            result = pt
            return result

        result = self.computeDeformationContribution(pt)

        for i in range(self.ndims):
            result[i] += pt[i]

        #if self.aMtx is not None:
        #    for i in range(self.ndims):
        #        for j in range(self.ndims):
        #            result[i] += self.aMtx[i, j] * pt[j]
        #if self.bVec is not None:
        #    for i in range(self.ndims):
        #        result[i] += self.bVec[i] + pt[i]

        return result

    def computeDeformationContribution(self, pt):
        result = np.zeros(self.ndims).astype(float)
        for lnd in range(self.nLm):
            tmpD = np.linalg.norm(self.srcPts[:, lnd] - pt)
            nrm = 0.0
            if tmpD > 1e-8:
                nrm = tmpD * tmpD * np.log(tmpD)
            for d in range(self.ndims):
                result[d] += (nrm * self.dMtxDat[d, lnd])
        return result

    @property
    def dataString(self):
        header = 'ThinPlateSplineR2LogR {} {}'.format(self.ndims, self.nLm)

        if self.aMtx is not None:
            blk1 = np.concatenate((self.aMtx.flatten(), self.bVec))
            b64_1 = encodeBase64(blk1)
        else:
            b64_1 = "null"

        blk2 = np.concatenate((self.srcPts.flatten(), self.dMtxDat.flatten()))
        b64_2 = encodeBase64(blk2)

        return '{} {} {}'.format(header, b64_1, b64_2)
