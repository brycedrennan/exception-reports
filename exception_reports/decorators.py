import sys

from decorator import decorator

from exception_reports.reporter import append_to_exception_message, create_exception_report
from exception_reports.storages import LocalErrorStorage


def exception_report(storage_backend=LocalErrorStorage(), output_format='html', data_processor=None):
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
            exc_type, exc_value, tb = sys.exc_info()

            report_location = create_exception_report(
                exc_type, exc_value, tb, output_format,
                storage_backend=storage_backend,
                data_processor=data_processor
            )

            e = append_to_exception_message(e, tb, f'[report:{report_location}]')
            setattr(e, 'report', report_location)

            # We want to raise the original exception:
            #    1) with a modified message containing the report location
            #    2) with the original traceback
            #    3) without it showing an extra chained exception because of this handling  (`from None` accomplishes this)
            raise e from None

    return decorator(_exception_reports)
