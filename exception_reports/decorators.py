from decorator import decorator

from exception_reports.reporter import ExceptionReporter, render_exception_report
from exception_reports.storages import LocalErrorStorage
from exception_reports.utils import gen_error_filename


def exception_report(storage_backend=LocalErrorStorage(), modify_message=True):
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
            if modify_message:
                raise type(e)(f'{str(e)} [report:{report_location}]').with_traceback(reporter.tb) from None
            else:
                raise e

    return decorator(_exception_reports)
