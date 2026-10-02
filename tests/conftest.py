import pytest

from dreamweave import create_app
from dreamweave.providers import MockNarrator, MockStoryModel


@pytest.fixture
def make_app(tmp_path):
    def _make(model=None, narrator=None):
        return create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test",
                "SESSION_COOKIE_SECURE": False,
                "DATA_DIR": str(tmp_path),
                "MODEL": model or MockStoryModel(),
                "NARRATOR": narrator or MockNarrator(),
            }
        )

    return _make


@pytest.fixture
def client(make_app):
    return make_app().test_client()
