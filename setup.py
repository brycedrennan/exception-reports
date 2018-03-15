from setuptools import setup

__version__ = '0.2.2'

setup(
    name="exception-reports",
    packages=["exception_reports"],
    package_data={'exception_reports': ['report_template.html']},
    version=__version__,
    description="Interactive stacktraces with variable state at each level.",
    author="Bryce Drennan, CircleUp",
    author_email="exception_reports@brycedrennan.org",
    url="https://github.com/circleup/exception-reports",
    download_url='https://github.com/circleup/exception-reports/tarball/' + __version__,
    keywords=["exception handler", "exceptions", "error logs"],
    classifiers=[
        "Programming Language :: Python :: 3.6",
    ],
    install_requires=['jinja2>=2.4', 'tinys3', 'decorator>=4.1'],
)
