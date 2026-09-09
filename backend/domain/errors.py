"""业务异常只描述问题，由 HTTP 层选择状态码。"""


class DomainError(Exception):
    pass


class NotFound(DomainError):
    pass


class Conflict(DomainError):
    pass


class InvalidInput(DomainError):
    pass


class ModelError(Exception):
    """已脱敏、可以展示给用户的模型错误。"""
