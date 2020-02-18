from setuptools import setup

setup(
    name="pytest_func_cov",
    packages=["pytest_func_cov"],
    version="0.1.2",
    license="MIT",
    description="Pytest plugin for measuring function coverage",
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
