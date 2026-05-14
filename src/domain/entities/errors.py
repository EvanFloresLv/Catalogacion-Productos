# --------------------------------------------------------------------- #

class CategoryError(Exception):
    """Base class for all category-related errors."""

class CategoryNameError(CategoryError):
    """Raised when a category name is invalid."""

class CategoryDuplicateSemanticContentError(CategoryError):
    """Raised when a duplicate semantic content is found."""

# --------------------------------------------------------------------- #

class ClassificationError(Exception):
    """Base class for all classification-related errors."""

class NoEligibleCategoriesError(ClassificationError):
    """Raised when no eligible categories are found."""

class NoEligibleMatchesError(ClassificationError):
    """Raised when no eligible matches are found."""

# --------------------------------------------------------------------- #

class ProductError(Exception):
    """Base class for all product-related errors."""

class ProductTitleError(ProductError):
    """Raised when a product title is invalid."""

# --------------------------------------------------------------------- #