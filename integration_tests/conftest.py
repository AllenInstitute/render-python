import os
from pathlib import Path

import pytest

import test_data
from renderapi.render import Render, RenderClient


def _client_script():
    script = os.environ.get("RENDER_CLIENT_SCRIPT")

    if script is None:
        script = RenderClient.clientscript_from_clientscripts(
            test_data.client_script_location
        )

    return Path(script).expanduser()


def _render_params():
    params = test_data.render_params.copy()

    host = str(params["host"])
    if not host.startswith(("http://", "https://")):
        params["host"] = f"http://{host}"

    return params


def _client_available():
    script = _client_script()
    return script.is_file() and os.access(script, os.X_OK)


def _shared_data_available(config):
    """Whether shared client/server data access is configured."""
    return (
        config.getoption("--shared-data")
        or os.environ.get("RENDER_SHARED_DATA", "").lower()
        in ("1", "true", "yes")
    )


def pytest_addoption(parser):
    parser.addoption(
        "--shared-data",
        action="store_true",
        default=False,
        help="Enable integration tests requiring shared data access",
    )


def pytest_collection_modifyitems(config, items):
    """Skip tests requiring unavailable external capabilities."""
    java_available = _client_available()
    shared_available = _shared_data_available(config)

    for item in items:
        if item.get_closest_marker("java_client") and not java_available:
            item.add_marker(pytest.mark.skip(
                reason=f"Java client unavailable: {_client_script()}"
            ))

        if item.get_closest_marker("shared_data") and not shared_available:
            item.add_marker(pytest.mark.skip(
                reason="Shared data unavailable; use --shared-data "
                       "or set RENDER_SHARED_DATA=1"
            ))


@pytest.fixture(scope="session")
def render_web():
    params = _render_params()
    params.pop("client_scripts", None)
    return Render(**params)


@pytest.fixture(scope="session")
def render_java():
    if not _client_available():
        pytest.skip(
            f"Render Java client unavailable: {_client_script()}"
        )

    script = _client_script()
    params = _render_params()
    params["client_scripts"] = str(script.parent)

    return RenderClient(
        **params,
        client_script=str(script),
        memGB=os.environ.get("RENDER_CLIENT_HEAP", "1G"),
        validate_client=True,
    )

@pytest.fixture(scope="session")
def render(request):
    """Return a RenderClient if available, otherwise a web-only Render."""
    fixture_name = "render_java" if _client_available() else "render_web"
    return request.getfixturevalue(fixture_name)
