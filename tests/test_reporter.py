from exception_reports.reporter import ExceptionReporter, render_exception_report


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
    big_str = b'a' * 5000  # noqa
    big_num = 2342342342349835  # noqa

    try:
        raise Exception('on purpose')
    except Exception as e:
        exception_data = ExceptionReporter(get_full_tb=False).get_traceback_data()

    local_vars = dict(exception_data['frames'][-1]['vars'])

    assert '&lt;trimmed' in local_vars['big_str']


def test_rendering_unicode_error():
    some_bytes = b'asdfljsadf\x23\x93\x01'
    try:
        some_bytes.decode('utf8')
    except UnicodeDecodeError:
        exception_data = ExceptionReporter(get_full_tb=False).get_traceback_data()

    html = render_exception_report(exception_data)
    assert 'string that could not be encoded' in html
    #
    # with open('report.html', 'w') as f:
    #     f.write(render_exception_report(exception_data))
