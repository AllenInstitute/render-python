import json
from collections import Iterable
from renderapi.errors import RenderError
from renderapi.transform.leaf import (
    load_leaf_json, AffineModel, Polynomial2DTransform)


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
    """  # noqa: E501

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
    renderapi.transform.Transform
        deserialized transformation using the most appropriate class

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
