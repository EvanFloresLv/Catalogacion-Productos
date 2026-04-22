from config.logging_config import setup_logging
from interfaces.cli.controller import CLIController

setup_logging()

def test_load_tree_policy():
    iterations = [("Liverpool", "./data/Liverpool.xlsx"), ("Suburbia", "./data/Suburbia.xlsx")]

    for business, file_path in iterations:
        CLIController.load_categories(
            file_path=file_path,
            business=business,
            by_sheet=False,
            brand=False,
        )


def test_create_product():
    products = [
        {
            "sku": "1193915848",
            "name": "Máscara Cameraman Baños Skibidi",
            "description": "Máscara para disfraz de Cameraman Baños Skibidi Ghoulish Productions.",
            "keywords": ["máscara", "disfraz", "cameraman", "baños"],
            "product_type": "marketplace",
            "gender": None,
            "brand": "GHOULISH PRODUCTIONS",
            "direction": "hogar",
        }
    ]
    CLIController.create_products(products)


def test_classification_product():
    CLIController.classify_product(product_sku="1193915848", top_k=5)


if __name__ == "__main__":
    test_load_tree_policy()
    # test_create_product()
    # test_classification_product()