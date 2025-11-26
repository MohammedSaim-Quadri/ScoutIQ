"""
Custom Exceptions for ScoutIQ application
"""

class ScoutIQException(Exception):
    """Base exception for ScoutIQ"""
    def __init__(self, message: str, status_code: int=500, user_message: str=None):
        self.message = message
        self.status_code = status_code
        self.user_message = user_message or message
        super().__init__(self.message)


class LLMServiceError(ScoutIQException):
    """Raised when LLM service fails"""
    def __init__(self, message:str = "AI service temporarily unavailable"):
        super().__init__(message = message, status_code=503, user_message="Our AI service is experiencing high demand. Please try again in a moment.")


class RateLimitError(ScoutIQException):
    """Raised when rate limit is exceeded"""
    def __init__(self):
        super().__init__(
            message="Rate limit exceeded",
            status_code=429,
            user_message="You're sending requests too quickly. Please wait a moment before trying again."
        )


class InvalidInputError(ScoutIQException):
    """Raised when input validation fails"""
    def __init__(self, field: str, issue: str):
        super().__init__(
            message=f"Invalid {field}: {issue}",
            status_code=400,
            user_message=f"Please check your {field}. {issue}"
        )


def get_error_suggestion(exc: ScoutIQException) -> str:
    """Provide helpful suggestions based on error type"""
    suggestions = {
        LLMServiceError: "Our AI is temporarily overloaded. Please wait 30 seconds and try again.",
        RateLimitError: "You've reached the rate limit. Wait a minute before making more requests.",
        InvalidInputError: "Double-check that your Job Description and Resume contain valid text.",
    }
    return suggestions.get(type(exc), "Please try again or contact support if the issue persists.")