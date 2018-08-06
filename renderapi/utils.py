#!/usr/bin/env python
'''
utilities to make render/java/web/life interfacing easier
'''
import tempfile
import logging
import copy
import json
import base64
import zlib

import numpy
import requests
try:
    from inspect import getfullargspec
except ImportError:
    from inspect import getargspec as getfullargspec

from .errors import RenderError

# use ujson if installed for faster json
try:
    import ujson as requests_json
except ImportError:
    import json as requests_json
requests.models.complexjson = requests_json


class NullHandler(logging.Handler):
    """handler to avoid logging errors for, e.g., missing logger setup"""
    def emit(self, record):
        pass


logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())


class RenderEncoder(json.JSONEncoder):
    """json Encoder in the following hierarchy for serialization:
        obj.to_dict()
        dict(obj)
        JsonEncoder.default(obj)
        obj.__dict__
    """
    def default(self, obj):
        """default encoder for that handles Render objects

        Parameters
        ----------
        obj : obj
            any object that implements to_dict, dict(obj),
            JsonEncoder.default(obj), or __dict__ (in order)
        Returns
        -------
        dict or list
            json encodable datatype

        """
        if isinstance(obj, numpy.integer):
            return int(obj)
        to_dict = getattr(obj, "to_dict", None)
        if callable(to_dict):
            return obj.to_dict()
        else:
            try:
                return dict(obj)
            except TypeError as e:
                logger.debug("{} object is not recognized dictionary".format(
                    type(obj)))
                try:
                    return super(RenderEncoder, self).default(obj)
                except TypeError as e:  # pragma: no cover
                    logger.info(e)
                    logger.warning(
                        "cannot json serialize {}.  "
                        "Defaulting to __dict__".format(type(obj)))
                    return obj.__dict__


def post_json(session, request_url, d, params=None):
    """POST requests with RenderError handling

    Parameters
    ----------
    session : requests.session.Session
        requests session
    request_url : str
        url
    d : dict
        data payload (will be json dumps-ed)
    params : dict
        requests parameters

    Returns
    -------
    requests.response: server response

    Raises
    ------
    RenderError
        if cannot post
    """

    headers = {"content-type": "application/json"}
    if d is not None:
        payload = json.dumps(d)
    else:
        payload = None
        headers['Accept'] = "application/json"
    r = session.post(request_url, data=payload, params=params,
                     headers=headers)
    if r.status_code not in [200, 201, 204]:
        raise RenderError(
            'cannot post {} to {} with params {} returned status_code '
            '{} with message {}'.format(
                d, request_url, params, r.status_code, r.text))
    return r


def rest_delete(session, request_url, params=None):
    """DELETE requests with RenderError handling

    Parameters
    ----------
    session : requests.session.Session
        requests session
    request_url : str
        url
    Returns
    -------
    requests.response
        server response
    """
    r = session.delete(request_url)
    if r.status_code not in [200, 202, 204]:
        raise RenderError("delete of {} returned {} with message {}".format(
            r.url, r.status_code, r.text))
    return r


def put_json(session, request_url, d, params=None):
    """PUT requests with RenderError handling

    Parameters
    ----------
    session : requests.session.Session
        requests session
    request_url : str
        url
    d : dict
        data payload (will be json dumps-ed)
    params : dict
        requests parameters

    Returns
    -------
    requests.response
        server response

    Raises
    ------
    RenderError
        if cannot post
    """

    headers = {"content-type": "application/json"}
    if d is not None:
        payload = renderdumps(d)
    else:
        payload = None
        headers['Accept'] = "application/json"
    r = session.put(request_url, data=payload, params=params,
                    headers=headers)
    if r.status_code not in [200, 201, 204]:
        raise RenderError(
            'put {} to {} returned status code {} with message {}'.format(
                d, r.url, r.status_code, r.text))
    return r


def get_json(session, request_url, params=None, stream=False, **kwargs):
    """get_json wrapper for requests to handle errors

    Parameters
    ----------
    session : requests.session.Session
        requests session
    request_url : str
        url
    params : dict
        requests parameters
    stream: bool
        requests whether to stream
    kwargs: dict
        kwargs to shout into the dark
    Returns
    -------
    dict
        json response from server

    Raises
    ------
    RenderError
        if cannot get json successfully
    """

    r = session.get(request_url, params=params, stream=stream)
    if r.status_code != 200:
        message = "request to {} returned error code {} with message {}"
        raise RenderError(message.format(r.url, r.status_code, r.text))
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


def renderdumps(obj, *args, **kwargs):
    """json.dumps using the RenderEncode

    Parameters
    ----------
    obj : obj
        object to dumps
    *args
        json.dumps args
    **kwargs
        json.dumps kwargs

    Returns
    -------
    str
        serialized object
    """
    cls_ = kwargs.pop('cls', RenderEncoder)
    return json.dumps(obj, *args, cls=cls_, **kwargs)


def renderdump(obj, *args, **kwargs):
    """json.dump using the RenderEncoder

    Parameters
    ----------
    obj : obj
        object to dumps
    *args
        json.dump args
    **kwargs
        json.dump kwargs
    """
    cls_ = kwargs.pop('cls', RenderEncoder)
    return json.dump(obj, *args, cls=cls_, **kwargs)


def renderdump_temp(obj, *args, **kwargs):
    """json.dump into a temporary file
    renderdump_temp(obj), obj will be dumped through renderdump
    into a temporary file

    Parameters
    ----------
    obj : obj
        object to dump
    *args
        json.dump args
    **kwargs
        json.dump kwargs

    Returns
    -------
    str
        path to location where temporary file was dumped
    """

    with tempfile.NamedTemporaryFile(
            suffix=".json", mode='w', delete=False) as tf:
        tempfilename = tf.name
        renderdump(obj, tf, *args, **kwargs)
    return tempfilename


def jbool(val):
    """return string representing java string values of py booleans

    Parameters
    ----------
    val : bool
        boolean to encode

    Returns
    -------
    str
        'true' or 'false'

    """
    if not isinstance(val, bool):
        logger.warning('Evaluating javastring of non-boolean {} {}'.format(
            type(val), val))
    return 'true' if val else 'false'


def stripLogger(logger_tostrip):  # pragma: no cover
    """remove all handlers from a logger -- useful for redefining

    Parameters
    ----------
    logger_tostrip : :class:`logging.Logger`
        logging logger to strip
    """
    if logger_tostrip.handlers:
        for handler in logger_tostrip.handlers:
            logger_tostrip.removeHandler(handler)


def defaultifNone(val, default=None):
    """simple default handler

    Parameters
    ----------
    val : obj
        value to fill in default
    default : obj
        default value

    Returns
    -------
    obj
        val if val is not None, else default
    """
    return val if val is not None else default


def fitargspec(f, oldargs, oldkwargs):
    """fit function argspec given input args tuple and kwargs dict

    Parameters
    ----------
    f : func
        function to inspect
    oldargs : tuple
        arguments passed to func
    oldkwards : dict
        keyword args passed to func

    Returns
    -------
    new_args
        args with values filled in according to f spec
    new_kwargs
        kwargs with values filled in according to f spec
    """
    try:
        arginfo = getfullargspec(f)
        # args, varargs, keywords, defaults = inspect.getargspec(f)
        num_expected_args = len(arginfo.args) - len(arginfo.defaults)
        new_args = tuple(oldargs[:num_expected_args])
        new_kwargs = copy.copy(oldkwargs)
        for i, arg in enumerate(oldargs[num_expected_args:]):
            new_kwargs.update({arginfo.args[i + num_expected_args]: arg})
        return new_args, new_kwargs
    except Exception as e:
        logger.error('Cannot fit argspec for {}'.format(f))
        logger.error(e)
        return oldargs, oldkwargs


def encodeBase64(src):
    """encode an array or list of doubles
    in Base64 binary-to-text encoding
    same as in trakem2...ThinPlateSplineTransform.java

    Parameters
    ----------
    src : 1D numpy array
        floating point values to be encoded

    Returns
    -------
    encoded: string
    """
    return base64.b64encode(
            zlib.compress(
                src.byteswap().tobytes())
                            ).decode('utf-8')


def decodeBase64(src):
    """decode a string
    encoded in base64 binary-to-text encoding
    same as in trakem2...ThinPlateSplineTransform.java

    Parameters
    ----------
    src : string
        encoded string

    Returns
    -------
    arr: length n numpy array of double-precision floats
    """
    if src[0] == '@':
        b = base64.b64decode(src[1:])
    else:
        b = zlib.decompress(base64.b64decode(src))
    return numpy.frombuffer(b).byteswap()
