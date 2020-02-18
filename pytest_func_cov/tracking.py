from functools import wraps
import importlib.util
import inspect
import os
import re
import sys
from types import MethodType


class IndexingError(Exception):
    """
    Raised for indexing errors
    """

    pass


class MonitoringError(Exception):
    """
    Raised for monitoring errors
    """

    pass


class FunctionCallMonitor:
    def __init__(self):
        self._functions = {}
        self._target_modules = []

    def register_function(self, f, parent_class=None):
        """
        Register function for call tracking. Wraps functions without changing
        signatures. Classmethods are unwrapped and the returned function is
        wrapped in @classmethod again as it is returned to preserve
        functionality.

        Args:
            f (function): Function to track
            parent_class (type): Parent class of the function if part of a
                class; defaults to None
        """
        # If function is part of a class and it is bound to it
        is_classmethod = parent_class is not None and isinstance(f, MethodType)

        # Unwrap @classmethod
        if is_classmethod:
            try:
                f = f.__func__
            except AttributeError as e:
                raise MonitoringError(f"Function {get_full_function_name(f)} not a classmethod")

        self._functions[f] = []

        @wraps(f)
        def _(*args, **kwargs):
            # Check the filename of the previous stack frame - that is where
            # the function call originates from
            source_frame = inspect.stack()[1]
            source_file = source_frame.filename
            source_function = source_frame.function
            self.record_call(f, source_file, source_function)

            return f(*args, **kwargs)

        # Re-wrap @classmethod
        if is_classmethod:
            _ = classmethod(_)

        return _

    @property
    def registered_functions(self):
        """
        Returns:
            Tuple(function) - all registered functions
        """
        return tuple(self._functions.keys())

    @property
    def called_functions(self):
        """
        Returns:
            Tuple(function) - all called registered functions
        """
        return tuple(
            [function for function, calls in self._functions.items() if len(calls) > 0]
        )

    @property
    def missed_functions(self):
        """
        Returns:
            Tuple(function) - all missed registered functions
        """
        return tuple(
            [function for function, calls in self._functions.items() if len(calls) == 0]
        )

    @property
    def tracking(self):
        """
        Returns:
            Dict(func, tuple(tuple(str, str))) - complete tracking information
        """
        return {f: tuple(v) for f, v in self._functions.items()}

    def register_target_module(self, m):
        """
        Registers a module from which an eligible function call may originate.

        Args:
            m (str): Absolute file path to the module
        """
        self._target_modules.append(m)

    def record_call(self, f, source_file, source_function):
        """
        Records a function call if the originating module is being tracked.

        Args:
            f (str): Full module name for the invoked function
            source_file (str): Absolute file path to the module from where the call
                originates
            source_function (str): Name of the function from where the call
                originates
        Returns:
            True if the call was recorded, False otherwise.
        """
        funcs = self._functions

        if source_file in self._target_modules:
            try:
                funcs[f].append((source_file, source_function))
            except KeyError:
                raise MonitoringError(f"Function {get_full_function_name(f)} not monitored.")

            return True

        return False


class ModuleLoader:
    def __init__(self):
        self._modules = {}

    def load_from_package(self, path, parent_package=None):
        """
        Recursively load all modules in a package specified in path.

        Args:
            path (str): Path to the package folder
            parent_package (str): Name of the parent package. Defaults to None.
        """
        package_name = os.path.basename(path)

        if parent_package is not None:
            package_name = f"{parent_package}.{package_name}"

        # Register package module
        package_import_path = os.path.join(path, "__init__.py")
        module_name, module = import_module_from_file(
            package_import_path, module_name=package_name
        )
        self._modules[module_name] = module

        # Register modules in path
        for module_path in find_modules(path):
            module_name, module = import_module_from_file(
                module_path, package_name=package_name
            )
            self._modules[module_name] = module

        for package_path in find_packages(path):
            self.load_from_package(package_path, package_name)

    def __contains__(self, item):
        return item in self._modules

    def __iter__(self):
        return iter(self._modules.items())


class FunctionIndexer:
    def __init__(self, ignore_func_names=None):
        """
        Args:
            ignore_func_names (list(str)): Function name patterns to
                ignore. Defaults to none
        """
        self._ignore_func_names = (
            ignore_func_names if ignore_func_names is not None else []
        )

        # Compile regular expressions
        self._func_names_rgx = [
            re.compile(pattern) for pattern in self._ignore_func_names
        ]

        # Initialise indexer and monitor
        self._loader = ModuleLoader()
        self._monitor = FunctionCallMonitor()

    def index_package(self, package_path):
        """
        Args:
            package_path(str): Path to package
        """
        if not is_package(package_path):
            raise IndexingError(f"Path {package_path} is not a package")

        self._loader.load_from_package(package_path)

        for module_name, module in self._loader:
            functions = get_functions_defined_in_module(module)
            classes = get_classes_defined_in_module(module)

            for f_name, f in functions:
                if not self.matches_filters(f_name):
                    setattr(module, f_name, self._monitor.register_function(f))

            for cls_name, cls in classes:
                for f_name, f in get_methods_defined_in_class(cls):
                    if not self.matches_filters(f_name):
                        setattr(cls, f_name, self._monitor.register_function(f, cls))

    def matches_filters(self, f_name):
        """
        Checks if the given function matches any of the filters.

        Args:
            f_name(str): Name of the function

        Returns:
            bool
        """
        return any(rgx.match(f_name) is not None for rgx in self._func_names_rgx)

    def register_source_module(self, module_name):
        self._monitor.register_target_module(module_name)

    @property
    def monitor(self):
        return self._monitor


def import_module_from_file(file_path, package_name=None, module_name=None):
    """
    Imports module from a given file path. If no package name is given, it is
    treated as a base package.

    Args:
        file_path (str): Path to module, assumed to be a ".py" file
        package_name (str): Name of the parent package, defaults to None
        module_name (str): Name of the module, defaults to None. If not set,
            the name of the file excluding the .py extension is used

    Returns:
        Tuple(str, module): qualified module name, module
    """
    if module_name is None:
        module_name = os.path.basename(file_path).rstrip(".py")

    if package_name is not None:
        module_name = f"{package_name}.{module_name}"

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return module_name, module


def is_defined_in_module(o, module):
    """
    Checks if an object is defined in a given module and not imported.

    Args:
        o (object): Object to check
        module (module): Module

    Returns:
        True or False
    """
    return o.__module__ == module.__name__


def get_functions_defined_in_module(module):
    """
    Get all the functions defined in a given module.

    Args:
        module (module): Module for lookup

    Returns:
        List(tuple(str, o))
    """
    all_functions = inspect.getmembers(module, inspect.isfunction)
    functions_defined_in_module = [
        f for f in all_functions if is_defined_in_module(f[1], module)
    ]

    return functions_defined_in_module


def get_classes_defined_in_module(module):
    """
    Get all the classes defined in a given module.

    Args:
        module (module): Module for lookup

    Returns:
        List(tuple(str, o))
    """
    all_classes = inspect.getmembers(module, inspect.isclass)
    classes_defined_in_module = [
        f for f in all_classes if is_defined_in_module(f[1], module)
    ]

    return classes_defined_in_module


def get_methods_defined_in_class(cls):
    """
    Get all functions defined in a given class. This includes all
    non-inherited methods, static methods and class methods.

    Args:
        cls (type): Class for lookup

    Returns:
        List(tuple(str, o))
    """
    methods = inspect.getmembers(cls, inspect.isfunction)
    class_methods = inspect.getmembers(cls, inspect.ismethod)

    functions = methods + class_methods

    # Only keep non-inherited functions
    cls_symbols = cls.__dict__
    functions = [f for f in functions if f[0] in cls_symbols]

    return functions


def is_package(path):
    """
    Checks if a given directory is a Python package (it contains a __init__.py
    file)

    Args:
        path (str):

    Returns:
        bool
    """
    return "__init__.py" in os.listdir(path)


def find_packages(path):
    """
    Finds all packages in a given directory. A directory is a package if
    it contains a file named __init__.py.

    Args:
        path (str): Base lookup directory

    Returns:
        List(str) absolute paths to the package
    """
    directories_in_path = [
        os.path.join(path, d)
        for d in os.listdir(path)
        if os.path.isdir(os.path.join(path, d))
    ]

    packages = [d for d in directories_in_path if is_package(d)]

    return packages


def find_modules(path):
    """
    Finds all modules in a given directory. A file is a module if it has a
    .py extension and is not named __init__.py.

    Args:
        path (str): Base lookup directory

    Returns:
        List(str) absolute paths to the modules
    """
    modules_in_path = [
        os.path.join(path, m)
        for m in os.listdir(path)
        if m.endswith(".py") and m != "__init__.py"
    ]

    return modules_in_path


def index_module(module, function_call_monitor):
    """
    Decorates all functions and classes defined in the given module
    for function call monitoring.

    Args:
        module (module): Module to index
        function_call_monitor (FunctionCallMonitor):
    """
    functions = get_functions_defined_in_module(module)
    classes = get_classes_defined_in_module(module)

    for f_name, f in functions:
        setattr(module, f_name, function_call_monitor.register_function(f))

    for cls_name, cls in classes:
        for f_name, f in get_methods_defined_in_class(cls):
            setattr(cls, f_name, function_call_monitor.register_function(f, cls))

        setattr(module, cls_name, cls)


def get_full_function_name(f):
    """
    Constructs full module path for a given function.

    Args:
        f (function): Function to construct the path for

    Returns:
        str
    """
    return f"{f.__module__}.{f.__qualname__}"
