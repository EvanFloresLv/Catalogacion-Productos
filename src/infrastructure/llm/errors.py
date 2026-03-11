class LLMError(Exception):
    pass


class TransientLLMError(LLMError):
    pass


class PermanentLLMError(LLMError):
    pass


class ValidationLLMError(LLMError):
    pass


class ProviderLLMError(LLMError):
    pass