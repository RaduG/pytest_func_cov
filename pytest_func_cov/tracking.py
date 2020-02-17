from functools import wraps
import importlib.util
import inspect
import os
import sys
from types import MethodType


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
        # class_name = parent_class.__name__ if parent_class is not None else None

        self._functions[f] = 0

        # If function is part of a class and it is bound to it
        is_classmethod = parent_class is not None and isinstance(f, MethodType)

        # Unwrap @classmethod
        if is_classmethod:
            f = f.__func__

        @wraps(f)
        def _(*args, **kwargs):
            # Check the filename of the previous stack frame - that is where
            # the function call originates from
            called_from = inspect.stack()[1].filename
            self.record_call(f, called_from)

            return f(*args, **kwargs)

        # Re-wrap @classmethod
        if is_classmethod:
            _ = classmethod(_)

        return _

    @property
    def registered_functions(self):
        """
        Returns:
            Tuple(str) - full module names for registered functions
        """
        return tuple(self._functions.keys())

    @property
    def called_functions(self):
        """
        Returns:
            Tuple(str) - full module names for all called registered functions
        """
        return tuple([name for name, calls in self._functions.items() if calls > 0])

    @property
    def uncalled_functions(self):
        """
        Returns:
            Tuple(str) - full module names for all uncalled registered functions
        """
        return tuple([name for name, calls in self._functions.items() if calls == 0])

    def register_target_module(self, m):
        """
        Registers a module from which an eligible function call may originate.

        Args:
            m (str): Absolute file path to the module
        """
        self._target_modules.append(m)

    def record_call(self, f, m):
        """
        Records a function call if the originating module is being tracked.

        Args:
            f (str): Full module name for the invoked function
            m (str): Absolute file path to the module from where the call
                originates

        Returns:

        """
        funcs = self._functions
        if m in self._target_modules:
            funcs[f] = funcs[f] + 1


function_call_monitor = FunctionCallMonitor()


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
        Module object
    """
    if module_name is None:
        module_name = os.path.basename(file_path).rstrip(".py")

    if package_name is not None:
        module_name = f"{package_name}.{module_name}"

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return module


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


def index_module(module):
    """
    Decorates all functions and classes defined in the given module
    for function call monitoring.

    Args:
        module (module): Module to index
    """
    functions = get_functions_defined_in_module(module)
    classes = get_classes_defined_in_module(module)

    for f_name, f in functions:
        setattr(module, f_name, function_call_monitor.register_function(f))

    for cls_name, cls in classes:
        for f_name, f in get_methods_defined_in_class(cls):
            setattr(cls, f_name, function_call_monitor.register_function(f, cls))

        setattr(module, cls_name, cls)


def register_package(package_path, parent_package=None):
    """
    Imports package __init__ and all child modules and packages recursively
    and registers each module for function call monitoring.

    Args:
        package_path (str): Path to package
    """
    package_name = os.path.basename(package_path)

    if parent_package is not None:
        package_name = f"{parent_package}.{package_name}"

    package_import_path = os.path.join(package_path, "__init__.py")

    package = import_module_from_file(package_import_path, module_name=package_name)

    index_module(package)

    for module_path in find_modules(package_path):
        module = import_module_from_file(module_path, package_name=package_name)
        index_module(module)

    for child_package in find_packages(package_path):
        register_package(child_package, package_name)


def discover(root_path):
    """
    Finds, registers and indexes all packages in a given folder. If the given
    folder is a package itself, it is also registered.

    Args:
        root_path (str): Lookup path
    """
    if is_package(root_path):
        register_package(root_path)

    else:
        packages = find_packages(root_path)

        # Filter for commonly known test folders
        packages = [p for p in packages if os.path.basename(p) not in ["tests", "test"]]

        # Register packages
        for package in packages:
            register_package(package)


def get_full_function_name(f):
    """
    Constructs full module path for a given function.

    Args:
        f (function): Function to construct the path for

    Returns:
        str
    """
    return f"{f.__module__}.{f.__qualname__}"