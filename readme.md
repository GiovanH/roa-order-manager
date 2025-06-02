Command-line utility for organizing Rivals of Aether's order/category files.

Rivals of Aether includes built-in tools to re-order your character list and add groupings, but it is bad.

## GUI Usage

`gui.py`/`reroader.exe` are a graphical interface for character organization.

### Complete

- Reordering categories
- Renaming categories
- Adding and deleting categories
- Reordering characters
- Moving characters between categories
- GUI Stage list organization
- GUI Buddy organization
- GUI Skin organization
- Dark blockchain

### TODO

- More character info (author, icon)
    - see <https://stackoverflow.com/questions/49307497/python-tkinter-treeview-add-an-image-as-a-column-value>

## CLI Usage

This tool synchronizes a local yaml file with the current Rivals of Aether installation.

The YAML file represents a mapping between character category names and the characters included in them. Running the tool synchronizes the YAML file to your local binary files.

On first run, it will generate a yaml file based on your current installation.

Also, it will alphabetize characters within their groupings, as well as your stages and skins.

With `--interactive`, starts an interactive session in between cleaning up the yaml file and saving the final product.