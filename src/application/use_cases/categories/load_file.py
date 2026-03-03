# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import re
import unicodedata
from typing import List
from dataclasses import dataclass

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
import pandas as pd
import tqdm

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.categories.category import Category
from domain.entities.categories.category_constraints import CategoryConstraints
from domain.entities.categories.category_profile import CategoryProfile
from domain.entities.embeddings.embedding import Embedding
from domain.value_objects.semantic_hash import SemanticHash

from application.ports.category_repository import CategoryRepository
from application.ports.category_profile_repository import CategoryProfileRepository
from application.ports.embedding_repository import EmbeddingRepository

from application.ports.embedding_service import EmbeddingService

@dataclass
class LoadCategoriesCommand:
    file_path: str

class LoadCategoriesFileUseCase:

    def __init__(
        self,
        category_repository: CategoryRepository,
        profiles_repository: CategoryProfileRepository,
        embedding_repository: EmbeddingRepository,
        embedding_service: EmbeddingService,
    ):
        self.category_repository = category_repository
        self.profiles_repository = profiles_repository
        self.embedding_repository = embedding_repository
        self.embedding_service = embedding_service


    def execute(
        self,
        cmd: LoadCategoriesCommand
    ) -> None:

        xls = pd.ExcelFile(cmd.file_path)
        sheet_names_list = xls.sheet_names

        categories: List[Category] = []
        embeddings: List[Embedding] = []
        profiles: List[CategoryProfile] = []

        for sheet_name in sheet_names_list:
            print(f"Processing sheet: {sheet_name}")

            data = pd.read_excel(xls, sheet_name=sheet_name)
            cat_id_index = data.columns.str.lower().get_loc('catid') if 'catid' in data.columns.str.lower() else None

            if len(data.columns) >= 4:
                levels = [f'level {i}' for i in range(1, cat_id_index + 1)]
                data.columns = levels + list(data.columns[4:])
            else:
                print(f"Skipping sheet {sheet_name} due to insufficient columns.")
                continue

            last_inserted = {}

            for index, row in tqdm.tqdm(data.iterrows(), total=data.shape[0], desc=f"Processing {sheet_name}"):

                try:
                    # Filter out NaN values
                    row_dict = {key: value for key, value in row.to_dict().items() if pd.notna(value)}

                    # Dynamically search for keys containing specific substrings (case-insensitive)
                    def find_key(substring):
                        return next((key for key in row_dict.keys() if substring in key.lower()), None)

                    level_key = find_key('level')
                    id_key = find_key('id')
                    url_key = find_key('url')
                    titulo_key = find_key('título')
                    descripcion_key = find_key('descripcion')
                    palabras_key = find_key('keywords')

                    # Extract values for the found keys
                    level = int(re.sub(r'\D', '', level_key).strip()) if level_key else None  # Keep only numbers
                    name = row_dict.get(level_key)
                    id = row_dict.get(id_key)
                    url = row_dict.get(url_key)
                    titulo = row_dict.get(titulo_key, "")
                    descripcion = row_dict.get(descripcion_key, "")
                    palabras = row_dict.get(palabras_key, "").split(",") if palabras_key else []

                    # Determine the parent ID
                    parent_id = last_inserted.get(level - 1) if level and level > 1 else None

                    # Update the last inserted category for the current level
                    last_inserted[level] = id

                    # Normalize UTF-8 strings and remove special characters
                    def clean_text(text):
                        text = unicodedata.normalize('NFKD', text)  # Normalize UTF-8 characters
                        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)  # Remove URLs
                        text = re.sub(r'\S*\.com\S*', '', text, flags=re.MULTILINE)  # Remove anything with .com
                        text = re.sub(r'[^a-zA-Z0-9\s_-]', '', text)  # Remove special characters
                        return text.strip()

                    titulo = clean_text(titulo)
                    descripcion = clean_text(descripcion)

                    # Extract additional keywords from title and description
                    titulo_keywords = titulo.lower().split()
                    descripcion_keywords = descripcion.lower().split()

                    # Combine all keywords and remove duplicates
                    all_keywords = list(word.strip() for word in palabras + titulo_keywords + descripcion_keywords)

                    flattened_keywords = list(set([word.strip() for phrase in all_keywords for word in phrase.split()]))

                    # Print the extracted values
                    cat: Category = Category.create(
                        id=id,
                        parent_id=parent_id,
                        name=name,
                        level=level,
                        description=descripcion,
                        url=url,
                        brand=None,  # Sheet name (BLP / Multisitios)
                        direction=None,  # Sheet name (Liverpool / Suburbia)
                        business=None,  # Liverpool, Suburbia, BLP, Multisitios
                        keywords=flattened_keywords,
                    )

                    emb: Embedding = Embedding.create(
                        category_id=id,
                        vector=self.embedding_service.generate(cat.to_embedding_text()),
                        content_hash=SemanticHash.from_text(cat.to_embedding_text()).value
                    )

                    prof: CategoryProfile = CategoryProfile.create(
                        category=cat,
                        constraints=(
                            CategoryConstraints(
                                allowed_genders=[],
                                allowed_brands=[cat.brand] if cat.brand else [],
                                allowed_business_types=[cat.business] if cat.business else [],
                                allowed_directions=[cat.direction] if cat.direction else [],
                                required_keywords=cat.keywords,
                            )
                        )
                    )

                    categories.append(cat)
                    embeddings.append(emb)
                    profiles.append(prof)
                except Exception as e:
                    print(f"Error processing index {index} - row {row} in sheet {sheet_name}: {e}")

        self.category_repository.save_batch(categories)
        self.embedding_repository.save_batch(embeddings)
        self.profiles_repository.save_batch(profiles)