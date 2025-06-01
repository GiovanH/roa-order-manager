from collections import OrderedDict, defaultdict
import itertools
import os
import pprint
import ruamel.yaml

from roa import RoaCategoriesFile, RoaEntry, RoaOrderFile, RoaCategory



yaml = ruamel.yaml.YAML(typ='unsafe')
yaml.default_flow_style = False
yaml.width = 4096

def sort_name(entry: RoaEntry):
    try:
        return entry.name.upper() # type: ignore
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


def roa_zip_chars(order_roa: RoaOrderFile, categories_roa: RoaCategoriesFile) -> dict[str, list[RoaEntry]]:
    data: dict = defaultdict(list)
    category = ''

    cats_by_index = {
        c.index: c.label.decode('utf-8')
        for c in categories_roa.categories
    }

    for i, c in enumerate(order_roa.groups['characters']):
        category = cats_by_index.get(i, category)
        data[category].append(c)

    return OrderedDict([
        (k, v)
        for k, v in data.items()
    ])

def load_yaml_state(order_roa: RoaOrderFile, categories_roa: RoaCategoriesFile):
    yaml_state: dict[str, list[str]] = {}
    if not os.path.isfile('sort.yaml'):
        yaml.dump(yaml_state, roa_zip_chars(order_roa, categories_roa))

    with open("sort.yaml", "r", encoding="utf-8") as fp:
        yaml_state = yaml.load(fp)

    return yaml_state

def sync_characters_to_yaml(order_roa: RoaOrderFile, categories_roa: RoaCategoriesFile):
    yaml_state = load_yaml_state(order_roa, categories_roa)

    all_yaml_reprs: set[str] = {
        r
        for g in yaml_state.values()
        if isinstance(g, list)
        for r in g
    }
    all_oar_reprs: set[str] = {
        repr(c) for c in order_roa.groups['characters']
    }
    # Remove unsubscribed or duplicate characters
    yaml_seen_reprs = set()
    for label, group in yaml_state.items():
        if label == '_removed': continue
        for repr_ in [*group]:
            if repr_ in yaml_seen_reprs:
                print(repr_, "appears twice, removing duplicate.")
                yaml_state[label].remove(repr_)
                continue

            yaml_seen_reprs.add(repr_)
            if repr_ not in all_oar_reprs:
                print(repr_, "not in oar, removing.")
                yaml_state[label].remove(repr_)
                yaml_state['_removed'] = yaml_state.get('_removed', [])
                yaml_state['_removed'].append(repr_)
            yaml_state[label] = sorted(group)

    # Add missing characters
    yaml_state['unsorted'] = yaml_state.get('unsorted', [])
    for r in all_oar_reprs.difference(all_yaml_reprs):
        print(r, "not in yaml, adding.")
        yaml_state['unsorted'].append(r)

    # Save yaml state
    with open("sort.yaml", "w", encoding="utf-8") as fp:
        yaml.dump(yaml_state, fp)


def sync_yaml_to_roa(order_roa: RoaOrderFile, categories_roa: RoaCategoriesFile, interactive=False):
    yaml_state = load_yaml_state(order_roa, categories_roa)

    repr_to_char: dict[str, RoaEntry] = {
        repr(c): c for c in order_roa.groups['characters']
    }

    # Sync roa to yaml
    characters = []
    categories_roa.categories.clear()
    for label, group in yaml_state.items():
        if len(group) < 1:
            continue
        new_cat = RoaCategory(len(characters), label.encode('utf-8'))
        print(new_cat)
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
