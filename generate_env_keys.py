import os
import sys
import subprocess

from secure_token import generate_key, DEFAULT_KEY_ENV_VAR

DEFAULT_VARS = [DEFAULT_KEY_ENV_VAR]


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    var_names = [a for a in args if a != "--apply"] or DEFAULT_VARS

    keys = {var: generate_key().decode() for var in var_names}

    if apply and os.name == "nt":
        for var, value in keys.items():
            subprocess.run(["setx", var, value], check=True)
        print("Applied the following environment variables (also shown here as a backup, in case setx failed):")
        for var, value in keys.items():
            print(f'{var}="{value}"')
        return

    if apply and os.name != "nt":
        print("--apply only runs setx on Windows. Printing values to set manually instead:\n")

    for var, value in keys.items():
        if os.name == "nt":
            print(f'setx {var} "{value}"')
        else:
            print(f'export {var}="{value}"')


if __name__ == "__main__":
    main()
