from setuptools import setup

setup(
    name="pytest_func_cov",
    packages=["pytest_func_cov"],
    entry_points={"pytest11": ["pytest_func_cov = pytest_func_cov.plugin"]},
    classifiers=["Framework :: Pytest"],
)
