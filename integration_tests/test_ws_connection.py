import pytest

from renderapi.render import get_owners


@pytest.mark.render_service
def test_service_connection(render):
    owners = get_owners(render=render)
    assert isinstance(owners, list)
