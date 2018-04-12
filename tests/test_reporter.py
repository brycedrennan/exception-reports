import os
from exception_reports.reporter import ExceptionReporter, render_exception_report, render_exception_json
from exception_reports.storages import LocalErrorStorage


def test_exception_report_data():
    class CustomException(Exception):
        pass

    def a(foo):
        bar = 'hey there'  # noqa
        b(foo)

    def b(foo):
        c(foo)

    def c(foo):
        green = 93  # noqa
        raise CustomException('yolo!')

    try:
        a('hi')
    except Exception as e:
        exception_data = ExceptionReporter(get_full_tb=False).get_traceback_data()

    frames = exception_data['frames']

    assert exception_data['exception_type'] == 'CustomException'
    assert exception_data['exception_value'] == 'yolo!'
    assert len(frames) == 4
    assert exception_data['frames'][-1]['function'] == 'c'
    local_vars = dict(exception_data['frames'][-1]['vars'])
    assert local_vars['green'] == '93'


def test_rendering_exception_during_exception():
    class MyException(Exception):

        def __repr__(self):
            return str(self)

        def __str__(self):
            raise Exception("NO RENDERING Exc")

    class ErrorProneThing(object):

        def __repr__(self):
            return str(self)

        def __str__(self):
            raise MyException("NO RENDERING")

    foo = ErrorProneThing()  # noqa

    try:
        raise Exception('on purpose')

    except Exception as e:
        exception_data = ExceptionReporter(get_full_tb=False).get_traceback_data()

    local_vars = dict(exception_data['frames'][-1]['vars'])
    assert 'An error occurred rendering' in local_vars['foo']


def test_rendering_long_string():
    big_str = b'a' * 10000  # noqa
    big_num = 2342342342349835  # noqa

    try:
        raise Exception('on purpose')
    except Exception as e:
        exception_data = ExceptionReporter(get_full_tb=False).get_traceback_data()

    local_vars = dict(exception_data['frames'][-1]['vars'])

    assert '&lt;trimmed' in local_vars['big_str']


def test_rendering_unicode_error(tmpdir):
    some_bytes = b'asdfljsadf\x23\x93\x01'
    try:
        some_bytes.decode('utf8')
    except UnicodeDecodeError:
        exception_data = ExceptionReporter(get_full_tb=False).get_traceback_data()

    html = render_exception_report(exception_data)
    assert 'string that could not be encoded' in html
    storage_backend = LocalErrorStorage(output_path=str(tmpdir))
    storage_backend.write('bug_report.html', html)


def test_saving_unicode_error(tmpdir):
    bad_url = 'http://badwebsite.circleup.com/in\udcaedex.html'
    try:
        bad_url.encode('utf8')
    except UnicodeEncodeError:
        exception_data = ExceptionReporter(get_full_tb=False).get_traceback_data()

    html = render_exception_report(exception_data)
    assert 'string that could not be encoded' in html
    storage_backend = LocalErrorStorage(output_path=str(tmpdir))
    storage_backend.write('bug_report.html', html)


def test_exception_data_json():
    try:
        raise Exception('on purpose')
    except Exception as e:
        exception_data = ExceptionReporter(get_full_tb=False).get_traceback_data()
    render_exception_json(exception_data)


def test_bad_sourcefile():
    reporter = ExceptionReporter()
    empty_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), '__init__.py')
    lower_bound, pre_context, context_line, post_context = reporter._get_lines_from_file(empty_file, 999, 4)
    assert 'There was an error displaying the source' in context_line
