# Refactoring Summary: Load File Use Case Split

## Overview
The monolithic `load_file.py` has been successfully split into three focused use cases following the Single Responsibility Principle. An orchestrator use case coordinates the workflow.

## New File Structure

```
src/application/use_cases/
├── categories/
│   ├── load_categories.py          # NEW: Category loading
│   ├── load_categories_from_file.py # NEW: Orchestrator
│   └── load_file.py                 # DEPRECATED: Backward compatibility
├── embeddings/
│   ├── __init__.py                  # NEW
│   └── load_embeddings.py           # NEW: Embedding generation
└── category_profiles/
    ├── __init__.py                  # NEW
    └── load_profiles.py             # NEW: Profile creation
```

## 1. LoadCategoriesUseCase
**File:** `src/application/use_cases/categories/load_categories.py`

**Responsibility:** Parse Excel files and persist categories to the database

**Key Features:**
- Parallel sheet processing
- Excel data validation and normalization
- Category parsing from rows
- Parent-child relationship validation
- Keyword extraction
- Deduplication

**Dependencies:**
- `CategoryRepository`
- `Session`

**Command:**
```python
LoadCategoriesCommand(file_path: str)
```

**Returns:** `List[Category]`

## 2. LoadEmbeddingsUseCase
**File:** `src/application/use_cases/embeddings/load_embeddings.py`

**Responsibility:** Generate and persist embeddings for categories

**Key Features:**
- Batch embedding generation
- Parallel processing
- Embedding text extraction with fallback
- Deduplication by (category_id, content_hash)

**Dependencies:**
- `EmbeddingRepository`
- `EmbeddingService`
- `Session`

**Command:**
```python
LoadEmbeddingsCommand(categories: List[Category])
```

**Returns:** `List[Embedding]`

## 3. LoadCategoryProfilesUseCase
**File:** `src/application/use_cases/category_profiles/load_profiles.py`

**Responsibility:** Create and persist category profiles with constraints

**Key Features:**
- Default profile creation
- Constraint initialization
- Deduplication by category_id

**Dependencies:**
- `CategoryProfileRepository`
- `Session`

**Command:**
```python
LoadCategoryProfilesCommand(categories: List[Category])
```

**Returns:** `List[CategoryProfile]`

## 4. LoadCategoriesFromFileUseCase (Orchestrator)
**File:** `src/application/use_cases/categories/load_categories_from_file.py`

**Responsibility:** Coordinate the three use cases in the correct order

**Workflow:**
1. Load categories from Excel file
2. Generate embeddings for loaded categories
3. Create profiles for loaded categories

**Dependencies:**
- All three use cases
- All repositories and services

**Command:**
```python
LoadCategoriesFromFileCommand(file_path: str)
```

**Returns:**
```python
{
    "categories": List[Category],
    "embeddings": List[Embedding],
    "profiles": List[CategoryProfile]
}
```

## Migration Guide

### Before (Old Code)
```python
from application.use_cases.categories.load_file import (
    LoadCategoriesFileUseCase,
    LoadCategoriesCommand,
)

use_case = LoadCategoriesFileUseCase(
    session=session,
    category_repository=category_repo,
    profiles_repository=profile_repo,
    embedding_repository=embedding_repo,
    embedding_service=embedding_svc,
)

use_case.execute(LoadCategoriesCommand(file_path="data.xlsx"))
```

### After (New Code - Orchestrator)
```python
from application.use_cases.categories.load_categories_from_file import (
    LoadCategoriesFromFileUseCase,
    LoadCategoriesFromFileCommand,
)

use_case = LoadCategoriesFromFileUseCase(
    session=session,
    category_repository=category_repo,
    profiles_repository=profile_repo,
    embedding_repository=embedding_repo,
    embedding_service=embedding_svc,
)

result = use_case.execute(LoadCategoriesFromFileCommand(file_path="data.xlsx"))
# result = {
#     "categories": [...],
#     "embeddings": [...],
#     "profiles": [...]
# }
```

### After (New Code - Individual Use Cases)
```python
# 1. Load categories only
from application.use_cases.categories.load_categories import (
    LoadCategoriesUseCase,
    LoadCategoriesCommand,
)

categories = LoadCategoriesUseCase(
    session=session,
    category_repository=category_repo,
).execute(LoadCategoriesCommand(file_path="data.xlsx"))

# 2. Generate embeddings only
from application.use_cases.embeddings.load_embeddings import (
    LoadEmbeddingsUseCase,
    LoadEmbeddingsCommand,
)

embeddings = LoadEmbeddingsUseCase(
    session=session,
    embedding_repository=embedding_repo,
    embedding_service=embedding_svc,
).execute(LoadEmbeddingsCommand(categories=categories))

# 3. Create profiles only
from application.use_cases.category_profiles.load_profiles import (
    LoadCategoryProfilesUseCase,
    LoadCategoryProfilesCommand,
)

profiles = LoadCategoryProfilesUseCase(
    session=session,
    profiles_repository=profile_repo,
).execute(LoadCategoryProfilesCommand(categories=categories))
```

## Benefits

### 1. **Single Responsibility**
Each use case has one clear responsibility:
- `LoadCategoriesUseCase`: Excel → Categories
- `LoadEmbeddingsUseCase`: Categories → Embeddings
- `LoadCategoryProfilesUseCase`: Categories → Profiles

### 2. **Testability**
Each use case can be tested independently with focused unit tests.

### 3. **Reusability**
Use cases can be composed in different ways:
- Load only categories (skip embeddings/profiles)
- Re-generate embeddings for existing categories
- Create profiles separately

### 4. **Maintainability**
Smaller, focused files are easier to understand and modify.

### 5. **Flexibility**
Can easily add new functionality without modifying existing use cases.

## Backward Compatibility

The old `load_file.py` file is preserved with:
- Deprecation warning on import
- Re-exports pointing to new orchestrator
- Maintains same public API

## Next Steps

1. ✅ Update tests to use new use cases
2. ✅ Update CLI/API endpoints to use orchestrator
3. ✅ Add error handling and logging to each use case
4. ✅ Create integration tests for orchestrator
5. ⏳ Remove deprecated `load_file.py` in next major version

## Transaction Handling

Each use case manages its own transaction:
- Categories: Commit after batch save
- Embeddings: Commit after batch save
- Profiles: Commit after batch save

The orchestrator can wrap all three in a single transaction if needed for atomicity.
