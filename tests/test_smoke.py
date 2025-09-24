from utils.base_config import config


def test_config_loads_from_test_env():
    """Ensure the test configuration loads placeholder values without secrets."""
    assert config.app_uri == "foo"
    assert config.nhs_login_client_id == "foo"
