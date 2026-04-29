# from config.logging_config import setup_logging
# from interfaces.cli.controller import CLIController

# setup_logging()

# def test_load_tree_policy():
#     iterations = [("Liverpool", "./data/Liverpool.xlsx"), ("Suburbia", "./data/Suburbia.xlsx")]

#     for business, file_path in iterations:
#         CLIController.load_categories(
#             file_path=file_path,
#             business=business,
#             by_sheet=False,
#             brand=False,
#         )


# def test_create_product():
#     products = [
#         {
#             "sku": "1193915848",
#             "name": "Máscara Cameraman Baños Skibidi",
#             "description": "Máscara para disfraz de Cameraman Baños Skibidi Ghoulish Productions.",
#             "keywords": ["máscara", "disfraz", "cameraman", "baños"],
#             "product_type": "marketplace",
#             "gender": None,
#             "brand": "GHOULISH PRODUCTIONS",
#             "direction": "hogar",
#         }
#     ]
#     CLIController.create_products(products)


# def test_classification_product():
#     CLIController.classify_product(product_sku="1193915848", top_k=5)

import pandas as pd

from domain.entities.brand import Brand

from application.use_cases.categories.load_categories import LoadCategoriesCommand, LoadCategoriesUseCase
from application.use_cases.categories.load_categories_from_file import LoadCategoriesFromFileCommand, LoadCategoriesFromFileUseCase
from application.use_cases.brands.load_brands import LoadBrandsCommand, LoadBrandsUseCase

from infrastructure.persistence.postgresql.session import SessionLocal

from infrastructure.persistence.postgresql.unit_of_work import SqlAlchemyUnitOfWork
from adapters.messaging.postgres_outbox_writer import PostgresOutboxWriter

from infrastructure.persistence.postgresql.repositories.category_repository_pg import CategoryRepositoryPG
from infrastructure.persistence.postgresql.repositories.embedding_repository_pg import EmbeddingRepositoryPG
from infrastructure.persistence.postgresql.repositories.brand_repository_pg import BrandRepositoryPG
from infrastructure.embeddings.gemini.client import EmbeddingClient

from adapters.messaging.in_process_event_bus import InProcessEventBus
from application.event_handlers.wiring import wire_projections

from application.event_handlers.logging_handler import LoggingEventHandler
from application.event_handlers.event_bus_handler import EventBusHandler


def create_unit_of_work(session, event_handlers = None):
    outbox = PostgresOutboxWriter(session)

    if event_handlers is None:

        bus = InProcessEventBus()
        wire_projections(bus, SessionLocal)

        event_handlers = [
            LoggingEventHandler(),
            EventBusHandler(bus)
        ]
    return SqlAlchemyUnitOfWork(
        session=session,
        outbox=outbox,
        event_handlers=event_handlers
    )


def test_load_categories():

    brand = Brand(
        name="Nike",
        business=["Liverpool", "BLP-Liverpool"]
    )

    with SessionLocal() as session:
        category_repo = CategoryRepositoryPG(session)

        data = pd.read_excel("./data/LiverpoolTest.xlsx", sheet_name=0)

        cmd = LoadCategoriesCommand(data=data, brand=brand)
        uow = create_unit_of_work(session)
        use_case = LoadCategoriesUseCase(repo=category_repo, uow=uow)
        result = use_case.execute(cmd)

        print(f"\n✓ Categories: {len(result)}")


def test_load_brands():

    with SessionLocal() as session:
        brand_repo = BrandRepositoryPG(session)

        data = pd.read_excel("./data/Brands.xlsx", sheet_name=0)

        cmd = LoadBrandsCommand(data=data)
        uow = create_unit_of_work(session)
        use_case = LoadBrandsUseCase(repo=brand_repo, uow=uow)
        result = use_case.execute(cmd)

        print(f"\n✓ Brands: {len(result)}")


def test_load_file():

    with SessionLocal() as session:
        category_repo = CategoryRepositoryPG(session)
        brand_repo = BrandRepositoryPG(session)
        embedding_repo = EmbeddingRepositoryPG(session)
        embedding_service = EmbeddingClient()

        cmd = LoadCategoriesFromFileCommand(file_path="./data/Liverpool.xlsx", brand="puma")
        uow = create_unit_of_work(session)
        use_case = LoadCategoriesFromFileUseCase(
            category_repository=category_repo,
            brand_repository=brand_repo,
            embedding_repository=embedding_repo,
            embedding_service=embedding_service,
            uow=uow,
        )
        result = use_case.execute(cmd)

        print(f"\n✓ Categories: {len(result['categories'])}")
        print(f"✓ Embeddings: {len(result['embeddings'])}")


if __name__ == "__main__":
    # test_load_tree_policy()
    # test_create_product()
    # test_classification_product()
    test_load_brands()
    test_load_file()