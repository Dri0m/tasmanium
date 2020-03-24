import glob
import importlib
import pkgutil
from copy import deepcopy
from pathlib import Path
from typing import Collection, AnyStr, List, Dict

from tasmanium import logger
from tasmanium.boiled_pickle import Feature
from tasmanium.constants import FEATURES_PATH

l = logger.getLogger(__name__)


def _glob_files_in_paths(paths: Collection[AnyStr], prefix: AnyStr, extension: AnyStr) -> List[AnyStr]:
    """Given a collection of arbitrary path strings, returns a list of (absolute) paths to feature files."""
    result = []
    for path in paths:
        path = f"{prefix}/{path}"
        path = Path(path).resolve()
        if not path.exists():
            raise ValueError(f"Provided path '{path}' does not exist.")
        if path.is_dir():
            result.extend([f for f in glob.glob(str(path.joinpath(Path(f"**/*{extension}"))), recursive=True)])

        elif path.is_file():
            if path.suffix != extension:
                raise ValueError(f"Cannot provide a file '{path}' with extension different than provided '{extension}'.")
            result.append(str(path))
    return result


def _glob_feature_files_in_paths(paths: Collection[AnyStr]) -> List[AnyStr]:
    return _glob_files_in_paths(paths, FEATURES_PATH, ".feature")


def _import_submodules(package, recursive=True):
    """ Import all submodules of a module, recursively, including subpackages
    :param recursive: bool
    :param package: package (name or actual module)
    :type package: str | module
    :rtype: dict[str, types.ModuleType]
    """
    if isinstance(package, str):
        l.ttrace(f"importing {package}")
        package = importlib.import_module(package)
    results = {}
    for loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
        full_name = package.__name__ + '.' + name
        try:
            results[full_name] = importlib.import_module(full_name)
        except ModuleNotFoundError as e:
            l.error("failed to import a step module!", exc_info=e)  # TODO there seems to be a problem here with phantom imports
        if recursive and is_pkg:
            results.update(_import_submodules(full_name))
    return results


def _gather_tags_from_features(features: List[Feature]) -> Dict[AnyStr, List[AnyStr]]:
    all_tags: Dict[AnyStr, List[AnyStr]] = {'feature_level': [], 'scenario_level': [], 'example_level': []}
    for feature in features:
        for scenario in feature.scenarios:
            for tag_level, tags in scenario.tags.items():
                for tag in tags:
                    if tag not in all_tags[tag_level]:
                        all_tags[tag_level].append(tag)
    return all_tags


def _remove_ats_from_tag_dict(tags: Dict[AnyStr, List[AnyStr]]) -> Dict[AnyStr, List[AnyStr]]:
    result: Dict[AnyStr, List[AnyStr]] = deepcopy(tags)
    for tag_level in result:
        result[tag_level] = [tag[1:] for tag in tags[tag_level]]
    return result
