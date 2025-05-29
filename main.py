from collections import defaultdict
import itertools
import os
import pprint
from pathlib import Path
import ruamel.yaml

from roa import RoaCategoriesFile, RoaEntry, RoaOrderFile, RoaCategory

from interactive import edit_interactive


yaml = ruamel.yaml.YAML(typ='unsafe')
yaml.default_flow_style = False

ROA_DIR = Path(f"{os.environ['LOCALAPPDATA']}/RivalsofAether/workshop")

def sort_name(entry: RoaEntry):
    try:
        return entry.name.upper()
    except:
        return 'ERROR'

def alphabetize_characters(order_roa):
    for k, l in order_roa.groups.items():
        if k != 'characters':
            sorted_group = sorted(order_roa.groups[k], key=sort_name)
            order_roa.groups[k] = sorted_group

def set_groups_by_alpha(order_roa, categories_roa):
    categories_roa.categories.clear()

    characters = order_roa.groups['characters']
    for g in itertools.groupby(characters, lambda c: c.name[0].upper()):
        key, list_ = g
        index = characters.index(next(list_))

        new_cat = RoaCategory(index, key.encode())
        # print(new_cat)
        categories_roa.categories.append(new_cat)


def roa_zip_chars(order_roa: RoaOrderFile, categories_roa: RoaCategoriesFile):
    data = defaultdict(list)
    category = ''

    cats_by_index = {
        c.index: c.label.decode('utf-8')
        for c in categories_roa.categories
    }

    for i, c in enumerate(order_roa.groups['characters']):
        category = cats_by_index.get(i, category)
        data[category].append(c)

    return dict(data)


def sync_yaml(order_roa: RoaOrderFile, categories_roa: RoaCategoriesFile):
    yaml_state: dict[str, list[str]] = {}
    if not os.path.isfile('sort.yaml'):
        yaml.dump(yaml_state, roa_zip_chars(order_roa, categories_roa))

    with open("sort.yaml", "r", encoding="utf-8") as fp:
        yaml_state = yaml.load(fp)

    repr_to_char: dict[str, RoaEntry] = {
        repr(c): c for c in order_roa.groups['characters']
    }

    all_yaml_reprs: set[str] = {
        r
        for g in yaml_state.values()
        if isinstance(g, list)
        for r in g
    }
    all_oar_reprs: set[str] = {
        repr(c) for c in order_roa.groups['characters']
    }
    # Remove unsubscribed characters
    yaml_state['_removed'] = yaml_state.get('_removed', [])
    for label, group in yaml_state.items():
        if label == '_removed': continue
        for repr_ in [*group]:
            if repr_ not in all_oar_reprs:
                print(repr_, "not in oar, removing.")
                group.remove(repr_)
                yaml_state['_removed'].append(repr_)
            yaml_state[label] = sorted(group)

    # Add missing characters
    yaml_state['unsorted'] = yaml_state.get('unsorted', [])
    for r in all_oar_reprs.difference(all_yaml_reprs):
        print(r, "not in yaml, adding.")
        yaml_state['unsorted'].append(r)

    edit_interactive(yaml_state)

    # Save yaml state
    with open("sort.yaml", "w", encoding="utf-8") as fp:
        yaml.dump(yaml_state, fp)

    # Sync roa to yaml
    characters = []
    categories_roa.categories.clear()
    for label, group in yaml_state.items():
        if len(group) < 1:
            continue
        new_cat = RoaCategory(len(characters), label.encode('utf-8'))
        categories_roa.categories.append(new_cat)
        for repr_ in group:
            try:
                characters.append(repr_to_char[repr_])
            except KeyError:
                if label == '_removed': continue
                print("Couldn't find repr", repr_, "in repr map")
                pprint.pprint(repr_to_char)
                raise

    order_roa.groups['characters'] = characters
    pprint.pprint(roa_zip_chars(order_roa, categories_roa))


if __name__ == '__main__':
    order_roa = RoaOrderFile(ROA_DIR / 'order.roa')
    categories_roa = RoaCategoriesFile(ROA_DIR / 'categories.roa')

    sync_yaml(order_roa, categories_roa)
    # alphabetize_characters(order_roa)
    # dump = pprint.pformat(dict(order_roa.groups))
    # print(dump)

    # set_groups_by_alpha(order_roa, categories_roa)

    order_roa.save_file()
    categories_roa.save_file()
