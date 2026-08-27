import os
from collections.abc import Sequence

from acbs.const import CONF_DIR, DUMP_DIR, LOG_DIR, TMP_DIR
from acbs.parser import get_tree_by_name


def acbs_query(input: str) -> str | None:
    input = input.strip()
    if not input:
        return None
    commands = input.split(':')
    getter = {
        'tree': acbs_query_tree,
        'path': acbs_query_path
    }.get(commands[0])
    if not callable(getter):
        return None
    return getter(commands)


def acbs_query_tree(commands: Sequence[str]) -> str | None:
    if len(commands) != 2:
        return None
    try:
        return get_tree_by_name(os.path.join(CONF_DIR, 'forest.conf'), commands[1])
    except (OSError, ValueError):
        return None


def acbs_query_path(commands: Sequence[str]) -> str | None:
    if len(commands) != 2:
        return None
    return {
        'conf': CONF_DIR,
        'dump': DUMP_DIR,
        'tmp': TMP_DIR,
        'log': LOG_DIR
    }.get(commands[1])
