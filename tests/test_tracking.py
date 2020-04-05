import os
import tempfile

import pytest
from pytest_func_cov import tracking

from .test_package.classes import SimpleClass
from .test_package.functions import simple_function, lambda_
from .test_package import functions


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


def test_is_package_with_package(package_path):
    assert tracking.is_package(package_path)


def test_is_package_with_non_package(non_package_path):
    assert not tracking.is_package(non_package_path)


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


def test_find_packages_in_directory_without_package(non_package_path):
    packages = tracking.find_packages(non_package_path)

    assert packages == []


def test_find_packages_in_directory_with_package(directory_with_packages):
    root_directory, expected = directory_with_packages

    output = tracking.find_packages(root_directory)

    assert len(output) == len(expected) and all(
        [package in output for package in expected]
    )


@pytest.fixture
def directory_with_modules():
    """
    Returns
        tuple(str, list(str)): First element is the absolute path to the root folder,
            the second element is the list of expected module names
    """
    with tempfile.TemporaryDirectory() as folder:
        with tempfile.NamedTemporaryFile(
            prefix=f"{os.path.basename(folder)}/", suffix=".py"
        ) as f:
            yield folder, [f.name]


def test_find_modules_in_directory_without_modules(non_package_path):
    output = tracking.find_packages(non_package_path)
    assert output == []


def test_find_module_in_directory_with_modules(directory_with_modules):
    directory, expected = directory_with_modules
    output = tracking.find_modules(directory)

    assert len(output) == len(expected) and all(
        [module in output for module in expected]
    )


def test_get_functions_defined_in_module():
    output = tracking.get_functions_defined_in_module(functions)
    expected = [
        ("simple_function", functions.simple_function),
        ("lambda_", functions.lambda_),
    ]
    print(output, expected, flush=True)
    assert all([function in output for function in expected])


def test_is_defined_in_module():
    pass
