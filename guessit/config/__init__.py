"""
Config module.
"""
from importlib import import_module
from typing import Any, List

from rebulk import Rebulk

_regex_prefix = 're:'
_import_prefix = 'import:'
_import_cache = {}
_pattern_types = ('regex', 'string')


def _process_option(name: str, value: Any):
    if name == 'validator':
        return _process_option_validator(value)
    return value


def _import_function(value: str):
    function_id = value[len(_import_prefix):]
    if '.' in function_id:
        module_name, func_name = function_id.rsplit('.', 1)
    else:
        module_name = "guessit.rules.common.validators"
        func_name = function_id
    function_id = f"{module_name}.{func_name}"
    if function_id in _import_cache:
        return _import_cache[function_id]

    mod = import_module(module_name)
    func = getattr(mod, func_name)
    _import_cache[function_id] = func

    return func


def _process_option_validator(value: str):
    if value.startswith(_import_prefix):
        return _import_function(value)
    return value


def _build_entry_decl(entry, options, value):
    entry_decl = dict(options.get(None, {}))
    entry_decl['value'] = value
    if isinstance(entry, str):
        if entry.startswith(_regex_prefix):
            entry_decl["regex"] = [entry[len(_regex_prefix):]]
        else:
            entry_decl["string"] = [entry]
    else:
        entry_decl.update(entry)
    if "pattern" in entry_decl:
        legacy_pattern = entry.pop("pattern")
        if legacy_pattern.startswith(_regex_prefix):
            entry_decl["regex"] = [legacy_pattern[len(_regex_prefix):]]
        else:
            entry_decl["string"] = [legacy_pattern]
    return entry_decl


def load_patterns(rebulk: Rebulk,
                  pattern_type: str,
                  patterns: List[str],
                  options: dict = None):
    """
    Load patterns for a prepared config entry
    :param rebulk: Rebulk builder to use.
    :param pattern_type: Pattern type.
    :param patterns: Patterns
    :param options: kwargs options to pass to rebulk pattern function.
    :return:
    """
    default_options = options.get(None) if options else None
    item_options = dict(default_options) if default_options else {}
    pattern_type_option = options.get(pattern_type)
    if pattern_type_option:
        item_options.update(pattern_type_option)
    item_options = {name: _process_option(name, value) for name, value in item_options.items()}
    getattr(rebulk, pattern_type)(*patterns, **item_options)


def load_config_patterns(rebulk: Rebulk,
                         config: dict,
                         options: dict = None):
    """
    Load patterns defined in given config.
    :param rebulk: Rebulk builder to use.
    :param config: dict containing pattern definition.
    :param options: Additional pattern options to use.
    :type options: Dict[Dict[str, str]] A dict where key is the pattern type (regex, string, functional) and value is
    the default kwargs options to pass.
    :return:
    """
    if options is None:
        options = {}

    for value, raw_entries in config.items():
        entries = raw_entries if isinstance(raw_entries, list) else [raw_entries]
        for entry in entries:
            entry_decl = _build_entry_decl(entry, options, value)

            for pattern_type in _pattern_types:
                patterns = entry_decl.get(pattern_type)
                if not patterns:
                    continue
                if not isinstance(patterns, list):
                    patterns = [patterns]
                patterns_entry_decl = dict(entry_decl)

                for pattern_type_to_remove in _pattern_types:
                    patterns_entry_decl.pop(pattern_type_to_remove, None)

                current_pattern_options = dict(options)
                current_pattern_options[None] = patterns_entry_decl

                load_patterns(rebulk, pattern_type, patterns, current_pattern_options)
