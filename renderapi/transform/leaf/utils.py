from .transform import Transform, logger
from renderapi.errors import RenderError
from .affine_models import (
        AffineModel,
        TranslationModel,
        RigidModel,
        SimilarityModel)
from .polynomial_models import (
        Polynomial2DTransform,
        NonLinearTransform,
        NonLinearCoordinateTransform,
        LensCorrection)
from .thin_plate_spline import (
        ThinPlateSplineTransform)
__all__ = ['load_leaf_json']


def load_leaf_json(d):
    """function to get the proper deserialization function for leaf transforms

    Parameters
    ----------
    d : dict
        json compatible representation of leaf transform to deserialize

    Returns
    -------
    renderapi.transform.Transform
        deserialized transformation

    Raises
    ------
    RenderError
        if d['type'] != leaf or is omitted

    """
    handle_load_leaf = {
        AffineModel.className: lambda x: AffineModel(json=x),
        Polynomial2DTransform.className:
            lambda x: Polynomial2DTransform(json=x),
        TranslationModel.className: lambda x: TranslationModel(json=x),
        RigidModel.className: lambda x: RigidModel(json=x),
        SimilarityModel.className: lambda x: SimilarityModel(json=x),
        NonLinearTransform.className: lambda x: NonLinearTransform(json=x),
        LensCorrection.className: lambda x: LensCorrection(json=x),
        ThinPlateSplineTransform.className:
            lambda x: ThinPlateSplineTransform(json=x),
        NonLinearCoordinateTransform.className:
            lambda x: NonLinearCoordinateTransform(json=x)}

    tform_type = d.get('type', 'leaf')
    if tform_type != 'leaf':
        raise RenderError(
            'Unexpected or unknown Transform Type {}'.format(tform_type))
    tform_class = d['className']
    try:
        return handle_load_leaf[tform_class](d)
    except KeyError as e:
        logger.info('Leaf transform class {} not defined in '
                    'transform module, using generic'.format(e))
        return Transform(json=d)
