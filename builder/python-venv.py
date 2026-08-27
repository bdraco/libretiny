# Copyright (c) Kuba Szczodrzyński 2023-09-07.

import json
import shutil
import site
import subprocess
import sys
from pathlib import Path

import semantic_version
from platformio.compat import IS_WINDOWS
from platformio.package.version import pepver_to_semver
from platformio.platform.base import PlatformBase
from SCons.Script import DefaultEnvironment, Environment

env: Environment = DefaultEnvironment()
platform: PlatformBase = env.PioPlatform()

# code borrowed and modified from espressif32/builder/frameworks/espidf.py


def env_configure_python_venv(env: Environment):
    venv_path = Path(env.subst("${PROJECT_CORE_DIR}"), "penv", ".libretiny")

    pip_path = venv_path.joinpath(
        "Scripts" if IS_WINDOWS else "bin",
        "pip" + (".exe" if IS_WINDOWS else ""),
    )
    python_path = venv_path.joinpath(
        "Scripts" if IS_WINDOWS else "bin",
        "python" + (".exe" if IS_WINDOWS else ""),
    )
    site_path = venv_path.joinpath(
        "Lib" if IS_WINDOWS else "lib",
        "." if IS_WINDOWS else f"python{sys.version_info[0]}.{sys.version_info[1]}",
        "site-packages",
    )

    if not pip_path.is_file():
        # Use the built-in PlatformIO Python to create a standalone virtual env
        result = env.Execute(
            env.VerboseAction(
                f'"$PYTHONEXE" -m venv --clear "{venv_path.absolute()}"',
                "LibreTiny: Creating a virtual environment for Python dependencies",
            )
        )
        if not python_path.is_file():
            # Creating the venv failed
            raise RuntimeError(
                f"Failed to create virtual environment. Error code {result}"
            )
        if not pip_path.is_file():
            # Creating the venv succeeded but pip didn't get installed
            # (i.e. Debian/Ubuntu without ensurepip)
            print(
                "LibreTiny: Failed to install pip, running get-pip.py", file=sys.stderr
            )
            import requests

            with requests.get("https://bootstrap.pypa.io/get-pip.py") as r:
                p = subprocess.Popen(
                    args=str(python_path.absolute()),
                    stdin=subprocess.PIPE,
                )
                p.communicate(r.content)
                p.wait()

    assert (
        pip_path.is_file()
    ), f"Error: Missing the pip binary in virtual environment `{pip_path.absolute()}`"
    assert (
        python_path.is_file()
    ), f"Error: Missing Python executable file `{python_path.absolute()}`"
    assert (
        site_path.is_dir()
    ), f"Error: Missing site-packages directory `{site_path.absolute()}`"

    env.Replace(LTPYTHONEXE=python_path.absolute(), LTPYTHONENV=venv_path.absolute())
    site.addsitedir(str(site_path.absolute()))


def env_install_python_dependencies(env: Environment, dependencies: dict):
    # uv (much faster than pip) is used when available, e.g. in the ESPHome docker image
    uv_path = shutil.which("uv")
    python_exe = env.subst("${LTPYTHONEXE}")
    try:
        if uv_path:
            list_cmd = [uv_path, "pip", "list", "--format=json", "--python", python_exe]
        else:
            list_cmd = [
                python_exe,
                "-m",
                "pip",
                "list",
                "--format=json",
                "--disable-pip-version-check",
            ]
        pip_output = subprocess.check_output(list_cmd)
        pip_data = json.loads(pip_output)
        packages = {p["name"]: pepver_to_semver(p["version"]) for p in pip_data}
    except:
        print(
            "LibreTiny: Warning! Couldn't extract the list of installed Python packages"
        )
        packages = {}

    to_install = []
    for name, spec in dependencies.items():
        install_spec = f'"{name}{dependencies[name]}"'
        if name not in packages:
            to_install.append(install_spec)
        elif spec:
            version_spec = semantic_version.Spec(spec)
            if not version_spec.match(packages[name]):
                to_install.append(install_spec)

    if to_install:
        if uv_path:
            install_cmd = f'"{uv_path}" pip install --python "${{LTPYTHONEXE}}" -U '
        else:
            install_cmd = '"${LTPYTHONEXE}" -m pip install --prefer-binary -U '
        env.Execute(
            env.VerboseAction(
                install_cmd + " ".join(to_install),
                "LibreTiny: Installing Python dependencies",
            )
        )


env.AddMethod(env_configure_python_venv, "ConfigurePythonVenv")
env.AddMethod(env_install_python_dependencies, "InstallPythonDependencies")
