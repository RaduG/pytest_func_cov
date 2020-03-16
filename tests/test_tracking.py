import pytest

from pytest_func_cov import tracking

from .test_package import classes, functions


@pytest.mark.parametrize(
    "func",
    [
        functions.simple_function,
        functions.lambda_,
        classes.SimpleClass.simple_method,
        classes.SimpleClass.simple_class_method,
        classes.SimpleClass.simple_static_method
    ],
    ids=["function", "lambda", "method", "class method", "static method"],
)
def test_get_full_function_name_correct_for_simple_function(func):
    expected_name = f"{func.__module__}.{func.__qualname__}"

    assert tracking.get_full_function_name(func) == expected_name

@pytest.fixture
def package_path():
    return os.path.dirname(os.path.abspath(__file__))

@pytest.fixture
def non_package_path():
    return os.path.dirname(os.path.abspath(__file__)) + "\\test_non_package"

def test_is_package_with_package(package_path):
    expected_result = tracking.is_package(package_path)

    assert expected_result

def test_is_package_with_non_package(non_package_path):
    expected_result = tracking.is_package(non_package_path)

    assert not expected_result

def test_is_package_with_wrong_path():
    expected_result = tracking.is_package("//Windows//120")

    assert expected_result
