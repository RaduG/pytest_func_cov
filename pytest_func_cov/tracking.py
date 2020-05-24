from collections import defaultdict
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
        self._modules = defaultdict(lambda: {})
        self._target_modules = []

    def register_function(self, f, parent_class=None):
        """
        Register function for call tracking. Wraps functions without changing
        signatures. Classmethods are unwrapped and the returned function is
        wrapped in @classmethod again as it is returned to preserve
        functionality.

        Args:
            f (FunctionType): Function to track
            parent_class (Type): Parent class of the function if part of a
                class; defaults to None
        
        Raises:
            MonitoringError: if f seems to be a classmethod but it does not have
                an __func__ attribute holding the wrapped method.
        """
        # If function is part of a class and it is bound to it
        is_classmethod = isinstance(f, MethodType)

        # Unwrap @classmethod
        if is_classmethod:
            try:
                f = f.__func__
            except AttributeError as e:
                raise MonitoringError(
                    f"Function {get_full_function_name(f)} not a classmethod"
                )

        self._modules[f.__module__][f] = []

        @wraps(f)
        def _(*args, **kwargs):
            # Check the filename of the previous stack frame - that is where
            # the function call originates from
            source_frame = inspect.stack()[1]
            source_file = source_frame.filename
            source_function = source_frame.function
            self.record_call(f, source_file, source_function)

            return f(*args, **kwargs)

        _.__signature__ = inspect.signature(f)

        # Re-wrap @classmethod
        if is_classmethod:
            _ = classmethod(_)

        return _

    @property
    def registered_functions(self):
        """
        Returns:
            Tuple[Tuple[str, Tuple[FunctionType, ...]], ...]: all registered
            functions, grouped by module
        """
        return tuple(
            (module_name, tuple(functions.keys()))
            for module_name, functions in self._modules.items()
        )

    @property
    def called_functions(self):
        """
        Returns:
            Tuple[Tuple[str, Tuple[FunctionType, ...]], ...]: all called registered 
                functions, grouped by module
        """
        return tuple(
            (
                module_name,
                tuple(f for f in functions if len(self._modules[module_name][f]) > 0),
            )
            for module_name, functions in self.registered_functions
        )

    @property
    def missed_functions(self):
        """
        Returns:
            Tuple[Tuple[str, Tuple[FunctionType, ...]], ...]: all missed registered
                functions, grouped by module
        """
        return tuple(
            (
                module_name,
                tuple(f for f in functions if len(self._modules[module_name][f]) == 0),
            )
            for module_name, functions in self.registered_functions
        )

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
            f (Callable): Invoked function
            source_file (str): Absolute file path to the module from where the call
                originates
            source_function (str): Name of the function from where the call
                originates
        
        Returns:
            bool: True if the call was recorded, False otherwise.
        """
        if source_file in self._target_modules:
            try:
                self._modules[f.__module__][f].append((source_file, source_function))
            except KeyError:
                raise MonitoringError(
                    f"Function {get_full_function_name(f)} not monitored."
                )

            return True

        return False


class ModuleLoader:
    def __init__(self):
        self._modules = {}

    def load_from_package(self, path):
        """
        Recursively load all modules in a package specified in path.

        Args:
            path (str): Path to the package folder
        """
        for module_path, module_name in find_modules(path):
            module = import_module_from_file(module_name, module_path)

            self._modules[module_name] = module

    def __iter__(self):
        return iter(self._modules.items())


class FunctionIndexer:
    def __init__(self, ignore_func_names=None):
        """
        Args:
            ignore_func_names (List[str]): Function name patterns to
                ignore. Defaults to None
        """
        self._ignore_func_names = ignore_func_names or []

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
            package_path (str): Path to package
        """
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
            f_name (str): Name of the function

        Returns:
            bool
        """
        return any(rgx.search(f_name) is not None for rgx in self._func_names_rgx)

    def register_source_module(self, module_name):
        """
        Registers a module by name from which function calls are considered
        eligible for tracking.

        Args:
            module_name (str):
        """
        self._monitor.register_target_module(module_name)

    @property
    def monitor(self):
        """
        Returns:
            FunctionCallMonitor
        """
        return self._monitor


def import_module_from_file(module_name, file_path):
    """
    Imports module from a given file path under a given module name. If the module
    exists the function returns the module object from sys.modules.

    Args:
        module_name (str): Full qualified name of the module.
            Example: mypackage.mymodule
        file_path (str): Path to module, assumed to be a ".py" file

    Returns:
        ModuleType
    """
    if module_name in sys.modules:
        module = sys.modules[module_name]
    else:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

    return module


def is_defined_in_module(o, module):
    """
    Checks if an object is defined in a given module and not imported.

    Args:
        o (Type): Object to check
        module (ModuleType): Module

    Returns:
        bool
    """
    return o.__module__ == module.__name__


def get_functions_defined_in_module(module):
    """
    Get all the functions defined in a given module.

    Args:
        module (ModuleType): Module for lookup

    Returns:
        List[Tuple[str, FunctionType]]
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
        module (ModuleType): Module for lookup

    Returns:
        List[Tuple[str, Type]]
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
        cls (Type): Class for lookup

    Returns:
        List[Tuple[str, Union[FunctionType, MethodType]]]
    """
    methods = inspect.getmembers(cls, inspect.isfunction)
    class_methods = inspect.getmembers(cls, inspect.ismethod)

    functions = methods + class_methods

    # Only keep non-inherited functions
    cls_symbols = cls.__dict__
    functions = [f for f in functions if f[0] in cls_symbols]

    return functions


def find_modules(path):
    """
    Discover all Python module files in a path. Uses os.walk to recursively traverse 
    all the nested directories but does not follow symlinks. Returns a generator 
    of 2-tuples, (absolute_file_path, absolute_module_name).

    Args:
        path (str):
    
    Returns:
        Generator[Tuple[str, str], None, None]
    """
    root_path = os.path.dirname(path)
    for dir_path, _, file_names in os.walk(path):
        package_name = dir_path[len(root_path) + 1 :].replace(os.path.sep, ".")

        for file_name in sorted(file_names):
            # We are only interested in .py files
            if not file_name.endswith(".py"):
                continue

            # Get the absolute path of the file
            absolute_path = os.path.join(dir_path, file_name)
            module_name = file_name[:-3]

            # If the module name is __init__, then it should match the package_name
            if module_name == "__init__":
                absolute_module_name = package_name
            else:
                absolute_module_name = f"{package_name}.{module_name}"

            yield (absolute_path, absolute_module_name)


def get_full_function_name(f):
    """
    Constructs full module path for a given function.

    Args:
        f (function): Function to construct the path for

    Returns:
        str
    """
    return f"{f.__module__}.{f.__qualname__}"
