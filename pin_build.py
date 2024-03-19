from pathlib import Path
import tomlkit, subprocess, click, re

def get_pyproject():
    pyproject_path = Path(__file__).parent / "pyproject.toml"
    return tomlkit.loads(pyproject_path.read_text())

def store_pyproject(pyproject, overwrite):
    pyproject_path = Path(__file__).parent / ("pyproject.toml" if overwrite else "pyproject.pin.toml")
    pyproject_path.write_text(tomlkit.dumps(pyproject))

def pin_dependencies(pyproject):
    # Store the python dep for later, this is the only entry in the table we need to remember
    python_dep = pyproject["tool"]["poetry"]["dependencies"]["python"]

    # Remove the dependencies and dev dependencies group. We don't *need* to remove the dev table, but
    # we don't need to keep it either
    pyproject["tool"]["poetry"].remove("dependencies").remove("group")

    # Let poetry generate the requirements.txt output, capture it in stdout so we can work with it
    dependencies = subprocess.run(["poetry", "export", "-f", "requirements.txt", "--without-hashes", "--only", "main"],
                                    stdout=subprocess.PIPE, text=True).stdout
    if not dependencies:
        print("Error exporting lockfile, make sure 'poetry-plugin-export' is installed")
        return None

    dependencies = dependencies.splitlines()
    dep_table = tomlkit.table()
    dep_table.append("python", python_dep) # Add Python version back in

    # Parse the requirements file lines how we need
    dep_re = re.compile("^(.+?)(==.*) ; (.*)")

    # Add the pinned dependencies back into the dependency table
    for line in dependencies:
        line = line.replace("\"", "'")
        result = dep_re.match(line)
        if not result:
            print(f"There was an error parsing the dependency line:\n{line}")
            return None
        dep, version, markers = result.groups()
        value = tomlkit.inline_table()
        value.update({"version": version, "markers": markers})
        dep_table.append(dep, value)
    pyproject["tool"]["poetry"].append("dependencies", dep_table)

    return pyproject

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.command(context_settings=CONTEXT_SETTINGS,
               help="Get locked dependencies and put them in the pyproject.toml as pinned dependencies.")
@click.option("--overwrite", is_flag=True, help="Overwrite the original pyproject.toml.")
def main(overwrite):
    pyproject = get_pyproject()

    pyproject = pin_dependencies(pyproject)

    if pyproject is not None:
        store_pyproject(pyproject, overwrite)
    else:
        print("Unable to get pinned dependencies.")

if __name__ == '__main__':
    main()
