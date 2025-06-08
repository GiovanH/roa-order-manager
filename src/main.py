import argparse
import pprint

from reroader.roa import ROA_DIR, RoaCategoriesFile, RoaOrderFile
from reroader.yaml_sync import yaml, load_yaml_state, sync_characters_to_yaml, sync_yaml_to_roa, roa_zip_chars
from reroader.interactive import edit_interactive


if __name__ == '__main__':
    order_roa = RoaOrderFile(ROA_DIR / 'order.roa')
    categories_roa = RoaCategoriesFile(ROA_DIR / 'categories.roa')

    parser = argparse.ArgumentParser(
        description="()",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("--interactive", "-i", action="store_true")
    args = parser.parse_args()

    sync_characters_to_yaml(order_roa, categories_roa)

    if args.interactive:
        yaml_state = load_yaml_state(order_roa, categories_roa)
        edit_interactive(yaml_state)
        with open("sort.yaml", "w", encoding="utf-8") as fp:
            yaml.dump(yaml_state, fp)
        pprint.pprint(roa_zip_chars(order_roa, categories_roa))

    sync_yaml_to_roa(order_roa, categories_roa)

    order_roa.save_file()
    categories_roa.save_file()
