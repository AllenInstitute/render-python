from collections import Iterable
from renderapi.errors import RenderError
from .leaf import AffineModel, Polynomial2DTransform
from .transform import TransformList, ReferenceTransform


def estimate_dstpts(transformlist, src=None, reference_tforms=None):
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
            dstpts = estimate_dstpts(tform, dstpts, reference_tforms)
        elif isinstance(tform, TransformList):
            dstpts = estimate_dstpts(tform.tforms, dstpts, reference_tforms)
        elif isinstance(tform, ReferenceTransform):
            try:
                tform_deref = next((tf for tf in reference_tforms
                                    if tf.transformId == tform.refId))
            except TypeError:
                raise RenderError(
                    "you supplied a set of tranforms that includes a "
                    "reference transform, but didn't supply a set of "
                    "reference transforms to enable dereferencing")
            except StopIteration:
                raise RenderError(
                    "the list of transforms you provided references "
                    "transorm {} but that transform could not be found "
                    "in the list of reference transforms".format(tform.refId))
            dstpts = estimate_dstpts([tform_deref], dstpts, reference_tforms)
        else:
            dstpts = tform.tform(dstpts)
    return dstpts


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
            if isinstance(i, Iterable):
                try:
                    notstring = isinstance(i, basestring)
                except NameError:
                    notstring = isinstance(i, str)
                if notstring:
                    for sub in flatten(i):
                        yield sub
            else:
                yield i

    dstpts = estimate_dstpts(transformlist, src)
    tforms = flatten(transformlist)
    if all([(tform.className == AffineModel.className)
            for tform in tforms]):
        am = AffineModel()
        am.estimate(A=src, B=dstpts, return_params=False)
        return am
    return Polynomial2DTransform(src=src, dst=dstpts, order=order)
