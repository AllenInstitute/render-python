#!/usr/bin/env python
"""handling mpicbg transforms in python

Currently only implemented to facilitate Affine and Polynomial2D
    used in Khaled Khairy's EM aligner workflow
"""
import logging

from renderapi.utils import NullHandler

logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())


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
                 transformId=None, labels=None, json=None):
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
        labels : list of str
            list of labels to give this transform
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
            self.labels = labels

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
            d['id'] = self.transformId
        if self.labels is not None:
            d['metaData'] = {'labels': self.labels}
        return d

    def from_dict(self, d):
        """deserialization routine

        Parameters
        ----------
        d : dict
            json compatible representation of this transform
        """
        self.className = d['className']
        self.transformId = d.get('id', None)
        self._process_dataString(d['dataString'])
        md = d.get('metaData', None)
        if md is not None:
            self.labels = md.get('labels', None)
        else:
            self.labels = None

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
