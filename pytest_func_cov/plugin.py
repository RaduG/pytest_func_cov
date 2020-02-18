import os
import sys

from .tracking import FunctionIndexer, get_full_function_name


def pytest_addoption(parser):
    """
    Pytest hook - register command line arguments. We want to register the
    --func_cov argument to explicitly pass the location of the package to
    discover and the ignore_func_names ini setting.

    Args:
        parser:
    """
    group = parser.getgroup("func_cov")
    group.addoption(
        "--func_cov",
        dest="func_cov_source",
        action="append",
        default=[],
        metavar="SOURCE",
        nargs="?",
        const=True,
    )

    parser.addini("ignore_func_names", "function names to ignore", "linelist", [])


def pytest_load_initial_conftests(early_config, parser, args):
    if early_config.known_args_namespace.func_cov_source:
        plugin = FuncCovPlugin(early_config)
        early_config.pluginmanager.register(plugin, "_func_cov")


class FuncCovPlugin:
    def __init__(self, args):
        self.args = args
        self.indexer = FunctionIndexer(
            args.getini("ignore_func_names")
        )

    def pytest_sessionstart(self, session):
        """
        Pytest hook - called when the pytest session is created. At this point,
        we need to run a full module discovery and register all functions
        prior to initiating the collection. If the PYTEST_FUNC_COV environment
        variable is set, use that as the root discovery path, relative to the
        session fspath.

        Args:
            session: Pytest session
        """
        # Add current folder to sys.path if it is not already in
        cwd = os.getcwd()
        if cwd not in sys.path:
            sys.path.append(cwd)

        pytest_cov_paths = self.args.known_args_namespace.func_cov_source

        if len(pytest_cov_paths) == 0:
            pytest_cov_paths = [session.fspath]
        else:
            pytest_cov_paths = [
                os.path.join(session.fspath, path) for path in pytest_cov_paths
            ]

        for package_path in pytest_cov_paths:
            self.indexer.index_package(package_path)


    def pytest_collect_file(self, path):
        """
        Pytest hook - called before the collection of a file. At this point
        we need to register the current test file as a valid function call
        origin.

        Args:
            path (str): Path to test file
        """
        self.indexer.register_source_module(path)

    def pytest_terminal_summary(self, terminalreporter):
        """
        Pytest hook - called when the test summary is outputted. Here we
        output basic statistics of the number of functions registered and called,
        as well as a function call test coverage (in percentage).

        Args:
            terminalreporter:
        """
        functions_found = [
            get_full_function_name(f)
            for f in self.indexer.monitor.registered_functions
        ]
        functions_called = [
            get_full_function_name(f)
            for f in self.indexer.monitor.called_functions
        ]
        functions_not_called = [
            get_full_function_name(f)
            for f in self.indexer.monitor.missed_functions
        ]

        coverage = round((len(functions_called) / len(functions_found)) * 100, 0)

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
        terminalreporter.write(
            f"There are {len(functions_not_called)} functions and methods which were not called during testing:\n",
            bold=True,
            red=True,
        )
        terminalreporter.write(
            "\n".join(f"- {f_n}" for f_n in functions_not_called), red=True
        )
        terminalreporter.write("\n\n")

        # Write test coverage
        terminalreporter.write(f"Total function coverage: {coverage}%\n", bold=True)
