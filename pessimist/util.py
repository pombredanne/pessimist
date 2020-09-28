import logging
import os.path
from email.message import Message
from email.parser import Parser
from pathlib import Path
from typing import Any, Dict, List

import toml
import volatile
from pep517.wrappers import Pep517HookCaller

LOG = logging.getLogger(__name__)

# From unreleased https://github.com/pypa/pep517/blob/master/pep517/pyproject.py
def load_system(source_dir: Path) -> Dict[str, Any]:
    """
    Load the build system from a source dir (pyproject.toml).
    """
    pyproject = os.path.join(source_dir, "pyproject.toml")
    with open(pyproject) as f:
        pyproject_data = toml.load(f)
    return pyproject_data["build-system"]  # type: ignore


def compat_system(source_dir: Path) -> Dict[str, Any]:
    """
    Given a source dir, attempt to get a build system backend
    and requirements from pyproject.toml. Fallback to
    setuptools but only if the file was not found or a build
    system was not indicated.
    """
    try:
        system = load_system(source_dir)
    except (FileNotFoundError, KeyError):
        system = {}
    system.setdefault(
        "build-backend", "setuptools.build_meta:__legacy__",
    )
    system.setdefault("requires", ["setuptools", "wheel"])
    return system


def get_metadata(path: Path) -> Message:
    with volatile.dir() as d:
        build_sys = compat_system(path)
        hooks = Pep517HookCaller(
            path,
            build_backend=build_sys["build-backend"],
            backend_path=build_sys.get("backend-path"),
        )

        dist_info = hooks.prepare_metadata_for_build_wheel(d)
        metadata_path = Path(d, dist_info, "METADATA")
        with open(metadata_path) as fp:
            return Parser().parse(fp)


def get_requirements(path: Path) -> List[str]:
    req = []
    for filename in path.glob("requirements*.txt"):
        LOG.info("Reading reqs from %s", filename)
        for line in filename.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            req.append(line)
    return req
