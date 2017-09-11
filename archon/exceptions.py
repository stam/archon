class ArchonError(Exception):
    message = 'Something went wrong'


class InvalidTargetError(ArchonError):
    message = 'Invalid target given'


class NoTargetError(ArchonError):
    message = 'No target given'


class UnauthorizedError(ArchonError):
    message = 'Unauthorized'


class InvalidTypeError(ArchonError):
    message = 'Invalid type given'
