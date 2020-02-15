import os

from .tracking import discover, function_call_monitor


def pytest_addoption(parser):
    """
    Pytest hook - register command line arguments. We want to register the
    --func_cov argument to explicitly pass the location of the package to
    discover.

    Args:
        parser:
    """
    parser.addoption("--func_cov", dest="func_cov", default=None)


def pytest_configure(config):
    """
    Pytest hook - called after command line options have been called. Register
    the --func_cov option in the PYTEST_FUNC_COV environment variable.

    Args:
        config: Pytest config object
    """
    func_cov = config.option.func_cov

    if func_cov is not None:
        os.environ["PYTEST_FUNC_COV"] = func_cov


def pytest_sessionstart(session):
    """
    Pytest hook - called when the pytest session is created. At this point,
    we need to run a full module discovery and register all functions
    prior to initiating the collection. If the PYTEST_FUNC_COV environment
    variable is set, use that as the root discovery path, relative to the
    session fspath.

    Args:
        session: Pytest session
    """
    pytest_cov_path = os.getenv("PYTEST_FUNC_COV", None)

    if pytest_cov_path is None:
        pytest_cov_path = session.fspath
    else:
        pytest_cov_path = os.path.join(session.fspath, pytest_cov_path)

    discover(pytest_cov_path)


def pytest_collect_file(path):
    """
    Pytest hook - called before the collection of a file. At this point
    we need to register the current test file as a valid function call
    origin.

    Args:
        path (str): Path to test file
    """
    function_call_monitor.register_target_module(path)


def pytest_terminal_summary(terminalreporter):
    """
    Pytest hook - called when the test summary is outputted. Here we
    output basic statistics of the number of functions registered and called,
    as well as a function call test coverage (in percentage).

    Args:
        terminalreporter:
    """
    functions_found = function_call_monitor.registered_functions
    functions_called = function_call_monitor.called_functions
    functions_not_called = function_call_monitor.uncalled_functions

    coverage = len(functions_called) / len(functions_found)

    # Write functions found message
    terminalreporter.write(
        f"Found {len(functions_found)} functions and methods:\n", bold=True
    )
    terminalreporter.write("\n".join(f"- {f_n}" for f_n in functions_found))
    terminalreporter.write("\n\n")

    # Write functions tested message
    terminalreporter.write(
        f"Called {len(functions_called)} functions and methods:\n", bold=True
    )
    terminalreporter.write(
        "\n".join(f"- {f_n}" for f_n in functions_called), green=True
    )
    terminalreporter.write("\n\n")

    # Write functions not tested message
    # Write functions tested message
    terminalreporter.write(
        f"There are {len(functions_not_called)} functions and methods which were not called during testing:\n",
        bold=True,
        red=True,
    )
    terminalreporter.write(
        "\n".join(f"- {f_n}" for f_n in functions_not_called), red=True
    )
    terminalreporter.write("\n\n")
