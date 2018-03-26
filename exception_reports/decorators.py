from decorator import decorator

from exception_reports.reporter import ExceptionReporter, render_exception_report
from exception_reports.storages import LocalErrorStorage
from exception_reports.utils import gen_error_filename


def exception_report(storage_backend=LocalErrorStorage()):
    """
    Decorator for creating detailed exception reports for thrown exceptions

    Usage:

        @exception_report()
        def foobar(text):
            raise Exception("bad things!!")

        foobar('hi')

    Output:

        Exception: bad things!! [report:/tmp/python-error-reports/2018-01-05_06:15:56.218190+00:00_0773698470164da3b2c427d8832dac13.html]


    S3 Usage:

        @exception_report()
        def foobar(text):
            raise Exception("bad things!!")

        foobar('hi')
    """

    def _exception_reports(func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            reporter = ExceptionReporter()
            exception_data = reporter.get_traceback_data()
            data = render_exception_report(exception_data)
            filename = gen_error_filename(extension='html')
            report_location = storage_backend.write(filename, data)
            setattr(e, 'report', report_location)

            ExceptionType = type(e)

            def my_str(self):
                m = ExceptionType.__str__(self)
                return f'{m} [report:{report_location}]'

            NewExceptionType = type(ExceptionType.__name__, (ExceptionType,), {'__str__': my_str})
            e.__class__ = NewExceptionType

            # We want to raise the original exception:
            #    1) with a modified message containing the report location
            #    2) with the original traceback
            #    3) without it showing an extra chained exceptino because of this handling  (`from None` accomplishes this)
            raise e from None

    return decorator(_exception_reports)
