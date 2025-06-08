import prompt_toolkit as ptk
from prompt_toolkit import completion

import pprint

from .roa import RoaCategoriesFile, RoaOrderFile
from .yaml_sync import load_yaml_state


def GroupCompleter(yaml_state: dict[str, list[str]]) -> completion.WordCompleter:
    groups = [*yaml_state.keys()]
    return completion.WordCompleter(groups, ignore_case=True, match_middle=False)


def edit_interactive(yaml_state: dict[str, list[str]]):
    group_completer = GroupCompleter(yaml_state)

    interactive = True

    while interactive:
        pprint.pprint({g: len(l) for g, l in yaml_state.items()})
        try:
            ans = ptk.prompt(
                "Inspect group? > ",
                completer=group_completer,
                complete_in_thread=True
            )
        except EOFError:
            return
        except KeyboardInterrupt:
            return
        if ans == "":
            return
        if ans not in yaml_state.keys():
            print(ans, "not in", yaml_state.keys())
            continue

        group_label = ans

        for rep in [*yaml_state[group_label]]:
            try:
                print(rep)
                ans = ptk.prompt(
                    "New group? > ",
                    completer=group_completer, complete_in_thread=True
                )
            except EOFError:
                break
            except KeyboardInterrupt:
                break
            if ans == '':
                continue
            if ans in yaml_state.keys():
                yaml_state[ans].append(rep)
                yaml_state[group_label].remove(rep)
            if ans not in yaml_state.keys():
                yaml_state[ans] = [rep]
                group_completer = GroupCompleter(yaml_state)

            pprint.pprint(yaml_state[group_label])
            pprint.pprint(yaml_state[ans])
            print('')


if __name__ == '__main__':
    from src.main import ROA_DIR
    order_roa = RoaOrderFile(ROA_DIR / 'order.roa')
    categories_roa = RoaCategoriesFile(ROA_DIR / 'categories.roa')
    yaml_state = load_yaml_state(order_roa, categories_roa)
    edit_interactive(yaml_state)
