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