import factory_target_py


def test_package_exposes_version():
    assert factory_target_py.__version__ == "0.1.0"
