import sys


def get_logger_traceback():  # noqa
    """
    Returns a traceback object for a log event.

    A traceback object is only available when an exception has been thrown. To get one for a log event
    we throw an exception and then wrap it in our own Traceback proxy that hides parts of the stack trace
    lower than the logging call.

    """
    try:
        raise ZeroDivisionError
    except ZeroDivisionError:
        return TracebackFrameProxy(sys.exc_info()[2])


class TracebackFrameProxy(object):
    """Proxies a traceback frame to hide parts of the trace related to logging.."""

    def __init__(self, tb, frames_level=0):
        self.tb = tb
        self.frames_level = frames_level
        self.frames_from_top = self.organize_tb_frames()

    @property
    def tb_frame(self):
        return self.frames_from_top[self.frames_level]

    @property
    def tb_lineno(self):
        return self.tb_frame.f_lineno

    @property
    def tb_lasti(self):
        return self.tb_frame.f_lasti

    @property
    def tb_next(self):
        if self.frames_level < len(self.frames_from_top) - 1:
            return TracebackFrameProxy(self.tb, frames_level=self.frames_level + 1)
        return None

    def organize_tb_frames(self):
        f = self.tb.tb_frame
        first_f = f
        found_log_call = False

        while f:
            if f.f_code.co_name == '_log' and 'logging' in f.f_code.co_filename:
                if 'makeRecord' in f.f_code.co_names:
                    f = f.f_back.f_back
                    found_log_call = True
                    break
            f = f.f_back

        # return entire stack if it can't find the right place to censor
        if not found_log_call:
            f = first_f

        frames = []
        while f:
            frames.append(f)
            f = f.f_back

        frames.reverse()
        return frames

    def __getattr__(self, name):
        return getattr(self.tb, name)
