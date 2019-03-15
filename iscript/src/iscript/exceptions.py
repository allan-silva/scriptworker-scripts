"""iScript exceptions."""
from scriptworker_client.exceptions import TaskError
from scriptworker_client.constants import STATUSES


class IScriptError(TaskError):
    """Something went wrong with signing script."""

    def __init__(self, msg):
        """Initialize IScriptError.

        Args:
            msg (str): the reason for throwing an exception.
        """
        super(IScriptError, self).__init__(
            msg, exit_code=STATUSES['internal-error']
        )


class FailedSubprocess(IScriptError):
    """Something went wrong during a subprocess exec."""


class UnknownAppDir(IScriptError):
    """There is no single app dir found for an app."""


class InvalidNotarization(IScriptError):
    """Apple returned an invalid status for notarization."""


class TimeoutError(IScriptError):
    """We have hit a timeout."""
