import os
import tempfile

import pytest
from pytest_func_cov import tracking

from .test_package.classes import SimpleClass
from .test_package.functions import simple_function, lambda_


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
    with tempfile.TemporaryDirectory() as folder:
        temp_package = tempfile.mkdtemp(dir=folder)
        with open(os.path.join(temp_package, "__init__.py"), "w"):
            yield temp_package

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
    assert all([method in output for method in expected])


def test_find_packages_in_directory_without_package(non_package_path):
    output = tracking.find_packages(non_package_path)
    expected = []
    assert all([directory in output for directory in expected])

def test_find_packages_in_directory_with_package(directory_with_packages):
    output = tracking.find_packages(os.path.abspath(os.path.join(directory_with_packages, os.pardir)))
    expected = [os.path.abspath(directory_with_packages)]
    assert all([directory in output for directory in expected])