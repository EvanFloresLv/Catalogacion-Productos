import logging

import pandas as pd

from domain.entities.brand import Brand

from application.use_cases.categories.load_categories import LoadCategoriesCommand, LoadCategoriesUseCase
from application.use_cases.categories.load_categories_from_file import LoadCategoriesFromFileCommand, LoadCategoriesFromFileUseCase
from application.use_cases.brands.load_brands import LoadBrandsCommand, LoadBrandsUseCase
from application.use_cases.products.load_products_from_file import LoadProductsFromFileCommand, LoadProductsFromFileUseCase
from application.use_cases.classification.classify_product import ClassifyProductCommand, ClassifyProductUseCase
from application.use_cases.classification.classify_batch_products import ClassifyBatchProductsCommand, ClassifyBatchProductsUseCase

from infrastructure.persistence.postgresql.session import SessionLocal

from infrastructure.persistence.postgresql.unit_of_work import SqlAlchemyUnitOfWork
from adapters.messaging.postgres_outbox_writer import PostgresOutboxWriter

from infrastructure.persistence.postgresql.repositories.category_repository_pg import CategoryRepositoryPG
from infrastructure.persistence.postgresql.repositories.embedding_repository_pg import EmbeddingRepositoryPG
from infrastructure.persistence.postgresql.repositories.brand_repository_pg import BrandRepositoryPG
from infrastructure.persistence.postgresql.repositories.product_repository_pg import ProductRepositoryPG
from infrastructure.embeddings.gemini.client import EmbeddingClient
from application.services.category_query_service import CategoryQueryService

from adapters.messaging.in_process_event_bus import InProcessEventBus
from application.event_handlers.wiring import wire_projections

from application.event_handlers.logging_handler import LoggingEventHandler
from application.event_handlers.event_bus_handler import EventBusHandler

from config.logging_config import setup_logging


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

        cmd = LoadCategoriesFromFileCommand(file_path="./data/Suburbia.xlsx", business="suburbia")
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


def test_load_products():

    with SessionLocal() as session:
        product_repo = ProductRepositoryPG(session)

        cmd = LoadProductsFromFileCommand(
            file_path="./data/ProductsWithTypeTest.xlsx",
            enhance=True,  # Set to True if you want to test LLM enhancement (requires prompt setup and API access)
        )
        uow = create_unit_of_work(session)
        use_case = LoadProductsFromFileUseCase(repo=product_repo, uow=uow)
        result = use_case.execute(cmd)

        print(f"\n✓ Products: {result}")


def test_classification_product():

    with SessionLocal() as session:
        product_repo = ProductRepositoryPG(session)

        cmd = ClassifyProductCommand(product_sku="5013081990", top_k=5)

        category_repo = CategoryRepositoryPG(session)
        category_query_service = CategoryQueryService(categories=category_repo)
        brand_repo = BrandRepositoryPG(session)
        embedding_repo = EmbeddingRepositoryPG(session)
        embedding_service = EmbeddingClient()

        uow = create_unit_of_work(session)
        use_case = ClassifyProductUseCase(
            products=product_repo,
            brands=brand_repo,
            embeddings=embedding_repo,
            category_query_service=category_query_service,
            service=embedding_service,
            uow=uow,
        )
        result = use_case.execute(cmd)

        print(f"\n✓ Classification results for product SKU {product_repo.get_by_sku(cmd.product_sku)}:")
        print(f"\n✓ Classification: {result}")


def test_classification_batch_products():

    with SessionLocal() as session:
        product_repo = ProductRepositoryPG(session)

        cmd = ClassifyBatchProductsCommand(product_skus=["1185256673", "1145665252"], top_k=5)

        category_repo = CategoryRepositoryPG(session)
        category_query_service = CategoryQueryService(categories=category_repo)
        brand_repo = BrandRepositoryPG(session)
        embedding_repo = EmbeddingRepositoryPG(session)
        embedding_service = EmbeddingClient()

        uow = create_unit_of_work(session)
        use_case = ClassifyBatchProductsUseCase(
            products=product_repo,
            brands=brand_repo,
            embeddings=embedding_repo,
            category_query_service=category_query_service,
            service=embedding_service,
            uow=uow,
        )
        result = use_case.execute(cmd)

        for product in cmd.product_skus:
            print(f"\n✓ Product {product_repo.get_by_sku(product)}")
            print(f"\n✓ Classification: {result.results.get(product)}")

        if result.failed:
            print(f"\n✗ Failed ({result.failed_count}):")
            for sku, err in result.failed.items():
                print(f"  - {sku}: {err}")


def test_llm():
    import json
    import pandas

    from utils.prompt import Prompt

    from llm_sdk.sync_sdk import LLM
    from llm_sdk.providers.sync_registry import ProviderSpec
    from llm_sdk_provider_gemini import SyncGeminiClient
    from llm_sdk.domain.chat import ChatMessage, ChatPart

    path = "./src/prompts/add_attributes.yml"
    prompt = Prompt(path)

    products_path = "./data/Products.xlsx"
    df = pandas.read_excel(products_path)
    prompt_data = []

    for _, row in df.iterrows():
        prompt_data.append({
            "codigo_sku": row["Código SKU"],
            "nombre_producto": row["Nombre del Producto"],
            "negocio": row["Negocio"],
            "direccion": row["Dirección"],
            "seccion": row["Sección"],
            "marca": row["Marca"]
        })

    # Initialize SDK once
    sdk = LLM.default()
    sdk.registry.register(ProviderSpec(
        name="gemini",
        factory=lambda: SyncGeminiClient(
            location=sdk.settings.gemini.location,
        ),
        models={
            "gemini-2.5-pro",
            "gemini-2.5-flash",
        },
    ))

    BATCH_SIZE = max(1, len(prompt_data) // 5)
    all_results = []

    for i in range(0, len(prompt_data), BATCH_SIZE):
        batch = prompt_data[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        print(f"\n--- Batch {batch_num} ({len(batch)} products) ---")

        data = prompt.get_prompt(
            input_data=str(batch)
        )

        system = str(data.get("system")).replace("\n", "")
        user = str(data.get("user")).replace("\n", "")

        resp = sdk.chat(
            messages=[
                ChatMessage(
                    role="model",
                    parts=[
                        ChatPart(
                            type="text",
                            text=system
                        ),
                    ]
                ),
                ChatMessage(
                    role="user",
                    parts=[
                        ChatPart(
                            type="text",
                            text=user
                        ),
                    ]
                )
            ],
            output_schema=data.get("schema"),
            provider="gemini",
            model="gemini-2.5-flash",
        )

        result = json.loads(resp.content)
        all_results.extend(result if isinstance(result, list) else [result])
        print(json.dumps(result, indent=2, ensure_ascii=False))

    print(f"\n✅ Total results: {len(all_results)}")

    with open("./classification_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    # test_load_file()
    test_load_products()
    # test_load_brands()
    # test_classification_product()
    # test_classification_batch_products()
    # setup_logging()
    # test_llm()
