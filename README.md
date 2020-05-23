| Build | Release |
| :------:| :------: |
| ![Build#develop](https://github.com/RaduG/pytest_func_cov/workflows/build/badge.svg?branch=develop) |  [![PyPI version](https://badge.fury.io/py/pytest-func-cov.svg)](https://badge.fury.io/py/pytest-func-cov) |


# Overview
This plugin attempts to provide a more meaningful test coverage metric for projects using pytest. The assumption is that,
in reality, the proportion of lines of code covered by tests does not entirely reflect how
much the tests explicitly cover. An additional indicator is how many functions, out of the total functions
defined in a project, are explicitly invoked during tests. This way, a test which
only calls a higher order function will not also count as testing the functions that it invokes during its execution, unlike traditional test coverage metrics.


pytest_func_cov provides an implementation of this metric, covering functions as well as
methods, classmethods and staticmethods. A function is considered tested if it is invoked explicitly
from a test function at least once. To make this check, the second stack frame is inspected
when a discovered function is invoked.


# Usage
```bash
pytest --func_cov=myproject tests/
```
Produces a report like:

```
--------------------pytest_func_cov-----------
Name                   Funcs   Miss     Cover
----------------------------------------------
myproject/module1.py       7      5       28% 
myproject/module2.py      10      3       70%
----------------------------------------------
TOTAL                     17      8       47%   
```

Similar to pytest-cov, you can use the ```--func_cov_report``` argument to configure the output. At the moment, the only
supported option is ```term-missing```, which adds another column to the output which lists all untested functions.

```bash
pytest --func_cov=myproject --func_cov_report=term-missing tests/
```
Produces a report like:

```
--------------------pytest_func_cov--------------------
Name                   Funcs   Miss     Cover   Missing
-------------------------------------------------------
myproject/module1.py       7      5       28%   func1, func2, MyClass.method, MyClass.static_method, MyClass.class_method
myproject/module2.py      10      3       70%   func3, func4, <lambda>
-------------------------------------------------------
TOTAL                     17      8       47%   
```

# Configuration
A list of function name patterns to ignore can be specified in pytest.ini.

Example:
```ini
[pytest]
ignore_func_names = 
    ^test_*
    ^myfunction$
```
This will ignore all function names starting with "test_" and functions named "myfunction".