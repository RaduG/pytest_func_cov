from .tracking import discover, function_call_monitor


def pytest_sessionstart(session):
    """
    Pytest hook - called when the pytest session is created. At this point,
    we need to run a full module discovery and register all functions
    prior to initiating the collection.

    Args:
        session: Pytest session
    """
    discover(session.fspath)


def pytest_collect_file(path, parent):
    """
    Pytest hook - called before the collection of a file. At this point
    we need to register the current test file as a valid function call
    origin.

    Args:
        path (str): Path to test file
        parent: unused
    """
    function_call_monitor.register_target_module(path)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """
    Pytest hook - called when the test summary is outputted. Here we
    output basic statistics of the number of functions registered and called,
    as well as a function call test coverage (in percentage).

    Args:
        terminalreporter:
        exitstatus: unused
        config: unused
    """
    functions_found = function_call_monitor.registered_functions
    functions_called = function_call_monitor.called_functions
    coverage = len(functions_called) / len(functions_found)

    terminalreporter.write(f"Found {len(functions_found)} functions and methods.\n")
    terminalreporter.write(f"Called {len(functions_called)} functions and methods: {functions_called}\n")
    terminalreporter.write(f"Function call coverage: {round(coverage * 100, 2)}%\n")
