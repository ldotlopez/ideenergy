import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--run-integration", 
        action="store_true", 
        default=False, 
        help="run integration tests against the live API"
    )

def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-integration"):
        # Run all tests including integration tests
        return
    
    # Skip tests marked as 'integration' if the flag is not provided
    skip_integration = pytest.mark.skip(reason="need --run-integration flag to run the integration test")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
