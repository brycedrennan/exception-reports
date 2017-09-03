from exception_reports.reporter import ExceptionReporter


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
        exception_data = ExceptionReporter().get_traceback_data()
        frames = exception_data['frames']

        assert exception_data['exception_type'] == 'CustomException'
        assert exception_data['exception_value'] == 'yolo!'
        assert len(frames) == 4
        assert exception_data['frames'][-1]['function'] == 'c'
        local_vars = dict(exception_data['frames'][-1]['vars'])
        assert local_vars['green'] == '93'
