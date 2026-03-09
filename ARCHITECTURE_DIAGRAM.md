# Architecture Diagram

## Before Refactoring

```
┌─────────────────────────────────────────────────────────────┐
│                  LoadCategoriesFileUseCase                   │
│                      (load_file.py)                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ • Parse Excel                                         │  │
│  │ • Create Categories                                   │  │
│  │ • Generate Embeddings                                 │  │
│  │ • Create Profiles                                     │  │
│  │ • Save everything                                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Dependencies:                                               │
│  • CategoryRepository                                        │
│  • EmbeddingRepository                                       │
│  • CategoryProfileRepository                                 │
│  • EmbeddingService                                          │
│  • Session                                                   │
└─────────────────────────────────────────────────────────────┘
```

## After Refactoring

```
┌───────────────────────────────────────────────────────────────────┐
│          LoadCategoriesFromFileUseCase (Orchestrator)             │
│                (load_categories_from_file.py)                     │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Step 1: Load Categories                                    │ │
│  │  ┌────────────────────────────────────────────────────────┐ │ │
│  │  │     LoadCategoriesUseCase                              │ │ │
│  │  │     (load_categories.py)                               │ │ │
│  │  │                                                         │ │ │
│  │  │  • Parse Excel                                         │ │ │
│  │  │  • Validate structure                                  │ │ │
│  │  │  • Create Category entities                            │ │ │
│  │  │  • Save to database                                    │ │ │
│  │  │                                                         │ │ │
│  │  │  Dependencies: CategoryRepository, Session             │ │ │
│  │  │  Returns: List[Category]                               │ │ │
│  │  └────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                             ↓                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Step 2: Generate Embeddings                                │ │
│  │  ┌────────────────────────────────────────────────────────┐ │ │
│  │  │     LoadEmbeddingsUseCase                              │ │ │
│  │  │     (load_embeddings.py)                               │ │ │
│  │  │                                                         │ │ │
│  │  │  • Extract embedding text                              │ │ │
│  │  │  • Generate vectors (batch)                            │ │ │
│  │  │  • Create Embedding entities                           │ │ │
│  │  │  • Save to database                                    │ │ │
│  │  │                                                         │ │ │
│  │  │  Dependencies: EmbeddingRepository,                    │ │ │
│  │  │                EmbeddingService, Session               │ │ │
│  │  │  Returns: List[Embedding]                              │ │ │
│  │  └────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                             ↓                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Step 3: Create Profiles                                    │ │
│  │  ┌────────────────────────────────────────────────────────┐ │ │
│  │  │     LoadCategoryProfilesUseCase                        │ │ │
│  │  │     (load_profiles.py)                                 │ │ │
│  │  │                                                         │ │ │
│  │  │  • Create default profiles                             │ │ │
│  │  │  • Initialize constraints                              │ │ │
│  │  │  • Create CategoryProfile entities                     │ │ │
│  │  │  • Save to database                                    │ │ │
│  │  │                                                         │ │ │
│  │  │  Dependencies: CategoryProfileRepository, Session      │ │ │
│  │  │  Returns: List[CategoryProfile]                        │ │ │
│  │  └────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
Excel File (.xlsx)
       ↓
┌──────────────────────┐
│ LoadCategories       │  Input:  file_path
│ UseCase              │  Output: List[Category]
└──────────────────────┘
       ↓
    Categories
       ↓
┌──────────────────────┐
│ LoadEmbeddings       │  Input:  List[Category]
│ UseCase              │  Output: List[Embedding]
└──────────────────────┘
       ↓
    Embeddings
       ↓
┌──────────────────────┐
│ LoadCategoryProfiles │  Input:  List[Category]
│ UseCase              │  Output: List[CategoryProfile]
└──────────────────────┘
       ↓
    Profiles
       ↓
  ┌────────────┐
  │  Database  │
  └────────────┘
```

## Dependency Graph

```
LoadCategoriesFromFileUseCase (Orchestrator)
    │
    ├─→ LoadCategoriesUseCase
    │       └─→ CategoryRepository
    │       └─→ Session
    │
    ├─→ LoadEmbeddingsUseCase
    │       └─→ EmbeddingRepository
    │       └─→ EmbeddingService
    │       └─→ Session
    │
    └─→ LoadCategoryProfilesUseCase
            └─→ CategoryProfileRepository
            └─→ Session
```

## Use Case Composition Examples

### Example 1: Full Pipeline (Default)
```python
orchestrator.execute(LoadCategoriesFromFileCommand("data.xlsx"))
```
→ Categories + Embeddings + Profiles

### Example 2: Categories Only
```python
load_categories.execute(LoadCategoriesCommand("data.xlsx"))
```
→ Categories (no embeddings, no profiles)

### Example 3: Re-generate Embeddings
```python
categories = category_repo.find_all()
load_embeddings.execute(LoadEmbeddingsCommand(categories))
```
→ New embeddings for existing categories

### Example 4: Add Profiles Later
```python
categories = category_repo.find_all()
load_profiles.execute(LoadCategoryProfilesCommand(categories))
```
→ Profiles for existing categories

## Benefits Visualization

```
┌────────────────────────────────────────────────────────────┐
│                    BEFORE (Monolithic)                     │
├────────────────────────────────────────────────────────────┤
│ ❌ 500+ lines in one file                                  │
│ ❌ Multiple responsibilities                               │
│ ❌ Hard to test individually                               │
│ ❌ Cannot reuse parts                                      │
│ ❌ Difficult to modify                                     │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│                   AFTER (Modular)                          │
├────────────────────────────────────────────────────────────┤
│ ✅ ~150 lines per file                                     │
│ ✅ Single responsibility each                              │
│ ✅ Easy to test in isolation                               │
│ ✅ Reusable components                                     │
│ ✅ Easy to extend/modify                                   │
│ ✅ Clear separation of concerns                            │
└────────────────────────────────────────────────────────────┘
```
