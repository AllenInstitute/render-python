import numpy as np


def calc_first_order_properties(M, force_shear='x'):
    """calculate scale shear and rotation from a 2x2 matrix
       could be M[0:2, 0:2] from an AffineModel or params[:, 1:3]
       from a Polynomial2DTransform

    Parameters
    ----------
    M : numpy array
        2x2
    force_shear : str
        'x' or 'y'

    Returns
    -------
    sx : float
        scale in x direction
    sy : float
        scale in y direction
    cx : float
        shear in x direction
    cy : float
        shear in y direction
    theta : float
        rotation angle in radians
    """
    if force_shear == 'x':
        sy = np.sqrt(M[1, 0] ** 2 + M[1, 1] ** 2)
        theta = np.arctan2(M[1, 0], M[1, 1])
        rc = np.cos(theta)
        rs = np.sin(theta)
        sx = rc * M[0, 0] - rs * M[0, 1]
        if rs != 0:
            cx = (M[0, 0] - sx*rc) / (sx * rs)
        else:
            cx = (M[0, 1] - sx*rs) / (sx * rc)
        cy = 0.0
    elif force_shear == 'y':
        # shear in y direction
        sx = np.sqrt(M[0, 0] ** 2 + M[0, 1] ** 2)
        theta = np.arctan2(-M[0, 1], M[0, 0])
        rc = np.cos(theta)
        rs = np.sin(theta)
        sy = rs * M[1, 0] + rc * M[1, 1]
        if rs != 0:
            cy = (M[1, 1] - sy * rc) / (-sy * rs)
        else:
            cy = (M[1, 0] - sy * rs) / (sy * rc)
        cx = 0.0
    else:
        raise ValueError("%s not a valid option for force_shear."
                         " should be 'x' or 'y'")
    # room for other cases, for example cx = cy

    return sx, sy, cx, cy, theta
