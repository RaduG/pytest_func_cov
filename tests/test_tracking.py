import os
import pathlib
import tempfile

import pytest
from pytest_func_cov import tracking

from .test_package.classes import SimpleClass
from .test_package.functions import simple_function, lambda_
from .test_package import functions


def create_files(*files):
    """
    Creates files at given paths with given contents.

    Args:
        *files (Tuple[str, Optional[Any]]): first element is the absolute path to
            a file to be created, and the second is used as the file content. If the content
            is None the file will be empty.
    """
    for path, contents in files:
        with open(path, "w") as f:
            if contents is not None:
                f.write(contents)


@pytest.mark.parametrize(
    "func",
    [
        simple_function,
        lambda_,
        SimpleClass.simple_method,
        SimpleClass.simple_class_method,
        SimpleClass.simple_static_method,
    ],
    ids=["function", "lambda", "method", "class method", "static method"],
)
def test_get_full_function_name_correct_for_simple_function(func):
    expected_name = f"{func.__module__}.{func.__qualname__}"

    assert tracking.get_full_function_name(func) == expected_name


@pytest.fixture
def package_path():
    with tempfile.TemporaryDirectory() as folder:
        with open(os.path.join(folder, "__init__.py"), "w"):
            yield folder


@pytest.fixture(scope="module")
def non_package_path():
    with tempfile.TemporaryDirectory() as folder:
        yield folder


@pytest.fixture
def directory_with_packages():
    """
    Returns
        tuple(str, list(str)): First element is the absolute path to the root folder,
            the second element is the list of expected package names
    """
    with tempfile.TemporaryDirectory() as root_folder:
        with tempfile.TemporaryDirectory(
            prefix=f"{os.path.basename(root_folder)}/"
        ) as package_folder:
            with open(os.path.join(package_folder, "__init__.py"), "w"):
                yield root_folder, [package_folder]


def test_get_methods_defined_in_class():
    output = [m[1] for m in tracking.get_methods_defined_in_class(SimpleClass)]
    expected = [
        SimpleClass.__init__,
        SimpleClass.simple_class_method,
        SimpleClass.simple_method,
        SimpleClass.simple_static_method,
    ]
    assert len(output) == len(expected) and all(
        [method in output for method in expected]
    )


@pytest.fixture(scope="package")
def nested_package_directory():
    """
    Creates the following structure (directory names are random):
        package/
            __init__.py
            module1.py
            non_py_file.ext
            subpackage1/
                __init__.py
                module2.py
                subpackage2/
                    module3.py
    Returns
        Tuple[str, Tuple[Tuple[str, str], ...]]: First element is the absolute path
            to the created directory, and the second is a tuple of tuples, where the first
            element is the absolute path to a .py file, and the second one is the name under
            which is should be imported.
    """
    with tempfile.TemporaryDirectory() as package_folder:
        # Create inner package directories
        pathlib.Path(os.path.join(package_folder, "subpackage1", "subpackage2")).mkdir(
            parents=True
        )

        files_to_create = (
            (os.path.join(package_folder, "__init__.py"), None),
            (os.path.join(package_folder, "module1.py"), None),
            (os.path.join(package_folder, "non_py_file.ext"), None),
            (os.path.join(package_folder, "subpackage1", "__init__.py"), None),
            (os.path.join(package_folder, "subpackage1", "module2.py"), None),
            (
                os.path.join(
                    package_folder, "subpackage1", "subpackage2", "module3.py"
                ),
                None,
            ),
        )
        create_files(*files_to_create)

        # Construct expected modulse
        package = os.path.basename(package_folder)
        expected_modules = (
            (files_to_create[0][0], package),
            (files_to_create[1][0], f"{package}.module1"),
            (files_to_create[3][0], f"{package}.subpackage1"),
            (files_to_create[4][0], f"{package}.subpackage1.module2"),
            (files_to_create[5][0], f"{package}.subpackage1.subpackage2.module3"),
        )

        yield package_folder, expected_modules


def test_find_module_in_nested_package_directory(nested_package_directory):
    directory, expected = nested_package_directory
    output = tuple(tracking.find_modules(directory))

    # Order is not guaranteed
    assert sorted(output) == sorted(expected)


def test_get_functions_defined_in_module():
    output = tracking.get_functions_defined_in_module(functions)
    expected = [
        ("simple_function", functions.simple_function),
        ("lambda_", functions.lambda_),
    ]

    assert all([function in output for function in expected])


@pytest.fixture(scope="function")
def empty_fcm():
    fcm = tracking.FunctionCallMonitor()
    fcm.register_target_module(__file__)

    return fcm


def test_fcm_correctly_tracks_function(empty_fcm):
    def f():
        return 42

    dec_f = empty_fcm.register_function(f)

    assert (
        (dec_f() == 42)
        and (empty_fcm.registered_functions == ((f.__module__, (f,)),))
        and (empty_fcm.called_functions == ((f.__module__, (f,)),))
    )


def test_fcm_correctly_tracks_method(empty_fcm):
    class A:
        def m(self):
            return 42

    orig_m = A.m
    A.m = empty_fcm.register_function(A.m)

    assert (
        (A().m() == 42)
        and (empty_fcm.registered_functions == ((orig_m.__module__, (orig_m,)),))
        and (empty_fcm.called_functions == ((orig_m.__module__, (orig_m,)),))
    )


def test_fcm_correctly_tracks_classmethod(empty_fcm):
    class A:
        @classmethod
        def cm(cls):
            return 42

    orig_cm = A.cm
    A.cm = empty_fcm.register_function(A.cm, A)

    assert (
        (A.cm() == 42)
        and (
            empty_fcm.registered_functions
            == ((orig_cm.__module__, (orig_cm.__func__,)),)
        )
        and (empty_fcm.called_functions == ((orig_cm.__module__, (orig_cm.__func__,)),))
    )


def test_fcm_returns_correct_missed(empty_fcm):
    def f():
        pass

    orig_f = f
    empty_fcm.register_function(f)

    assert empty_fcm.missed_functions == ((orig_f.__module__, (orig_f,)),)


def test_fcm_does_not_track_against_unregistered_targets():
    fcm = tracking.FunctionCallMonitor()

    def f():
        pass

    orig_f = f
    f = fcm.register_function(f)
    f()

    assert fcm.missed_functions == ((orig_f.__module__, (orig_f,)),)


def test_fcm_record_call_raises_monitoring_error_if_f_not_tracked(empty_fcm):
    with pytest.raises(tracking.MonitoringError):
        empty_fcm.record_call(
            lambda x: x,
            __file__,
            test_fcm_record_call_raises_monitoring_error_if_f_not_tracked,
        )


def test_fcm_record_call_returns_false_if_source_not_registered(empty_fcm):
    f = lambda x: x
    dec_f = empty_fcm.register_function(f)

    # Use other file as source as the source
    assert not empty_fcm.record_call(f, "not/a/path", None)


def test_fcm_record_call_returns_true_if_source_registered(empty_fcm):
    f = lambda x: x
    dec_f = empty_fcm.register_function(f)

    assert empty_fcm.record_call(f, __file__, None)


def test_module_loader_loads_all_modules_from_package(nested_package_directory):
    directory, expected_modules = nested_package_directory

    ml = tracking.ModuleLoader()
    ml.load_from_package(directory)

    module_paths, module_names = zip(*expected_modules)

    assert all(
        module_name in module_names
        and module_obj.__file__ == module_paths[module_names.index(module_name)]
        for module_name, module_obj in ml
    )


@pytest.fixture(scope="package")
def fi_with_filters():
    filters = ("^test_", "_end$")

    return tracking.FunctionIndexer(filters)


@pytest.mark.parametrize(
    ["func_name", "expected_result"],
    [
        ("test_x", True),
        ("atest_x", False),
        ("test_", True),
        ("x_end", True),
        ("x_end_x", False),
    ],
)
def test_fi_matches_filters(fi_with_filters, func_name, expected_result):
    assert fi_with_filters.matches_filters(func_name) is expected_result
