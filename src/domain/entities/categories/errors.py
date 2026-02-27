
class CategoryError(Exception):
    """Base class for all category-related errors."""


class CategoryNameError(CategoryError):
    """Raised when a category name is invalid."""


class CategoryDuplicateSemanticContentError(CategoryError):
    """Raised when a duplicate semantic content is found."""