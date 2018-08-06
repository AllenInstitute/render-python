import json
import logging
from collections import Iterable
import numpy as np
from ..errors import ConversionError, EstimationError, RenderError
from ..utils import NullHandler, encodeBase64, decodeBase64


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
                                           self.ndims, self.nLm)
            self.dMtxDat = values[self.ndims*self.nLm:].reshape(
                                           self.ndims, self.nLm)
        except ValueError:
            raise RenderError(
                "inconsistent sizes and array lengths, \
                 in ThinPlateSplineTransform dataString")

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


