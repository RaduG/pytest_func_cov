import os
from setuptools import setup


this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, "README.md"), "r") as f:
    long_description = f.read()


setup(
    name="pytest_func_cov",
    packages=["pytest_func_cov"],
    version="0.2.3",
    license="MIT",
    description="Pytest plugin for measuring function coverage",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Radu Ghitescu",
    author_email="radu.ghitescu@gmail.com",
    url="https://github.com/radug0314/pytest_func_cov",
    install_requires=["pytest>=5"],
    entry_points={"pytest11": ["pytest_func_cov = pytest_func_cov.plugin"]},
    classifiers=[
        "Framework :: Pytest",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
    ],
    python_requires=">=3.6",
    zip_safe=False,
)
