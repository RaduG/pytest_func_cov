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
    group.addoption(
        "--func_cov_report",
        dest="func_cov_report",
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
        self.indexer = FunctionIndexer(args.getini("ignore_func_names"))

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
                os.path.join(session.fspath, path.rstrip("/\\"))
                for path in pytest_cov_paths
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
        self.indexer.register_source_module(str(path))

    def pytest_terminal_summary(self, terminalreporter):
        """
        Pytest hook - called when the test summary is outputted. Here we
        output basic statistics of the number of functions registered and called,
        as well as a function call test coverage (in percentage).

        Args:
            terminalreporter:
        """
        output_options = self.args.known_args_namespace.func_cov_report
        include_missing = "term-missing" in output_options

        tr = terminalreporter
        cwd = os.getcwd()

        found = self.indexer.monitor.registered_functions
        called = self.indexer.monitor.called_functions
        missed = self.indexer.monitor.missed_functions

        module_paths = [sys.modules[m].__file__[len(cwd) + 1 :] for m, _ in found]
        max_name_len = max([len(mp) for mp in module_paths] + [5])

        fmt_name = "%%- %ds  " % max_name_len
        header = (fmt_name % "Name") + " Funcs   Miss" + "%*s" % (10, "Cover")

        if include_missing:
            header += "%*s" % (10, "Missing")

        fmt_coverage = fmt_name + "%6d %6d" + "%%%ds%%%%" % (9,)
        if include_missing:
            fmt_coverage += "   %s"

        msg = "pytest_func_cov"
        tr.write("-" * 20 + msg + "-" * 20 + "\n")
        tr.write(header + "\n")
        tr.write("-" * len(header) + "\n")

        total_funcs = 0
        total_miss = 0

        for i, mp in enumerate(module_paths):
            funcs = len(found[i][1])
            miss = len(missed[i][1])
            cover = int(((funcs - miss) / funcs) * 100)

            total_funcs += funcs
            total_miss += miss

            args = (mp, funcs, miss, cover)

            if include_missing:
                args += (", ".join([f.__qualname__ for f in missed[i][1]]),)

            tr.write(fmt_coverage % args)
            tr.write("\n")

        tr.write("-" * len(header) + "\n")

        if total_funcs != 0:
            total_cover = int(((total_funcs - total_miss) / total_funcs) * 100)
        else:
            total_cover = 0

        args = ("TOTAL", total_funcs, total_miss, total_cover)

        if include_missing:
            args += ("",)

        tr.write(fmt_coverage % args + "\n")
