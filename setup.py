from os import path

from setuptools import setup

__version__ = "2.0.0"

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="exception-reports",
    packages=["exception_reports"],
    package_data={"exception_reports": ["report_template.html"]},
    version=__version__,
    description="Interactive stacktraces with variable state at each level.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Bryce Drennan",
    author_email="exception_reports@brycedrennan.org",
    url="https://github.com/brycedrennan/exception-reports",
    download_url="https://github.com/brycedrennan/exception-reports/tarball/"
    + __version__,
    keywords=["exception handler", "exceptions", "error logs"],
    install_requires=["jinja2>=2.4", "decorator>=4.1"],
    python_requires=">=3.8",
)
