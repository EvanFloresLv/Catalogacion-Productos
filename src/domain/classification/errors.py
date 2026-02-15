class ClassificationError(Exception):
    pass


class NoEligibleCategoriesError(ClassificationError):
    pass


class NoEligibleMatchesError(ClassificationError):
    pass