#!/usr/bin/env python3
import hashlib
import json
import os
import re
import shutil
import sys
import traceback
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyghidra
PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "ghidra-headless-mcp"
SERVER_VERSION = "0.1.0"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_LIMIT = 100
MAX_LIMIT = 1000
SCRIPT_DIR = Path(__file__).resolve().parent
# Ghidra project directories cannot live under dot-prefixed path components such as
# ~/.codex, so default to a sibling under the user's home directory.
DEFAULT_PROJECTS_DIR = Path.home() / "CodexGhidraProjects"


TOOLS = [
    {
        "name": "open_binary",
        "description": "Import or reopen a binary in headless Ghidra and make it the active analysis target.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "binary_path": {"type": "string", "description": "Absolute path to the local binary file."},
                "analyze": {"type": "boolean", "description": "Run Ghidra auto-analysis during import. Defaults to true."},
                "project_name": {"type": "string", "description": "Optional fixed Ghidra project name."},
                "project_root": {"type": "string", "description": "Optional parent directory for Ghidra projects."}
            },
            "required": ["binary_path"]
        }
    },
    {
        "name": "get_current_binary",
        "description": "Return metadata for the currently opened binary.",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "list_functions",
        "description": "List functions from the current program.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "offset": {"type": "number", "description": "Pagination offset."},
                "limit": {"type": "number", "description": "Maximum function count to return."},
                "query": {"type": "string", "description": "Optional case-insensitive substring filter."}
            }
        }
    },
    {
        "name": "search_functions_by_name",
        "description": "Search functions whose names contain the given substring.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Case-insensitive substring to match."},
                "offset": {"type": "number", "description": "Pagination offset."},
                "limit": {"type": "number", "description": "Maximum function count to return."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "decompile_function",
        "description": "Decompile a function by exact or fuzzy name match.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Function name to decompile."}
            },
            "required": ["name"]
        }
    },
    {
        "name": "decompile_function_by_address",
        "description": "Decompile a function by entry address.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Function entry address such as 100000558 or 0x100000558."}
            },
            "required": ["address"]
        }
    },
    {
        "name": "disassemble_function",
        "description": "Return assembly instructions for a function by entry address.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Function entry address such as 100000558 or 0x100000558."},
                "limit": {"type": "number", "description": "Maximum instruction count to return. Defaults to 200."}
            },
            "required": ["address"]
        }
    },
    {
        "name": "list_strings",
        "description": "List defined string-like data items from the current program.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "offset": {"type": "number", "description": "Pagination offset."},
                "limit": {"type": "number", "description": "Maximum string count to return."},
                "min_length": {"type": "number", "description": "Minimum string length. Defaults to 4."},
                "query": {"type": "string", "description": "Optional case-insensitive substring filter."}
            }
        }
    },
    {
        "name": "list_imports",
        "description": "List imported symbols from the current program.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "offset": {"type": "number", "description": "Pagination offset."},
                "limit": {"type": "number", "description": "Maximum import count to return."},
                "query": {"type": "string", "description": "Optional case-insensitive substring filter."}
            }
        }
    },
    {
        "name": "get_xrefs_to",
        "description": "List cross-references to a given address.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Target address such as 100000558, 0x100000558, or EXTERNAL:00000001."},
                "offset": {"type": "number", "description": "Pagination offset."},
                "limit": {"type": "number", "description": "Maximum xref count to return."}
            },
            "required": ["address"]
        }
    },
    {
        "name": "get_xrefs_from",
        "description": "List cross-references originating from a given address.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Source address such as 100000558, 0x100000558, or EXTERNAL:00000001."},
                "offset": {"type": "number", "description": "Pagination offset."},
                "limit": {"type": "number", "description": "Maximum xref count to return."}
            },
            "required": ["address"]
        }
    },
    {
        "name": "get_function_xrefs",
        "description": "List cross-references to a function by name or entry address.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Function name to resolve."},
                "address": {"type": "string", "description": "Function entry address as an alternative to name."},
                "offset": {"type": "number", "description": "Pagination offset."},
                "limit": {"type": "number", "description": "Maximum xref count to return."}
            }
        }
    },
    {
        "name": "rename_function_by_address",
        "description": "Rename a function at a specific address.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Function entry address to rename."},
                "new_name": {"type": "string", "description": "New function name."}
            },
            "required": ["address", "new_name"]
        }
    },
    {
        "name": "rename_function",
        "description": "Rename a function by exact or fuzzy name resolution.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Existing function name to resolve."},
                "new_name": {"type": "string", "description": "New function name."}
            },
            "required": ["name", "new_name"]
        }
    },
    {
        "name": "rename_data",
        "description": "Rename defined data at a specific address, or create a label if primary symbol is missing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Defined data address to rename."},
                "new_name": {"type": "string", "description": "New data label name."}
            },
            "required": ["address", "new_name"]
        }
    },
    {
        "name": "list_exports",
        "description": "List exported entry points from the current program.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "offset": {"type": "number", "description": "Pagination offset."},
                "limit": {"type": "number", "description": "Maximum export count to return."},
                "query": {"type": "string", "description": "Optional case-insensitive substring filter."}
            }
        }
    },
    {
        "name": "list_segments",
        "description": "List memory segments / blocks from the current program.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "offset": {"type": "number", "description": "Pagination offset."},
                "limit": {"type": "number", "description": "Maximum segment count to return."},
                "query": {"type": "string", "description": "Optional case-insensitive substring filter on segment name."}
            }
        }
    },
    {
        "name": "close_binary",
        "description": "Close the current Ghidra project and clear active state.",
        "inputSchema": {"type": "object", "properties": {}}
    }
]


@dataclass
class GhidraState:
    project: Any = None
    nested_project_dir: Path | None = None
    project_name: str | None = None
    program_path: str | None = None
    program_name: str | None = None
    binary_path: Path | None = None
    ghidra_install_dir: Path | None = None


STATE = GhidraState()


def eprint(message: str) -> None:
    sys.stderr.write(message + "\n")
    sys.stderr.flush()


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def respond(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def sanitize_project_name(binary: Path) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", binary.stem).strip("._-") or "sample"
    digest = hashlib.sha1(str(binary).encode("utf-8")).hexdigest()[:8]
    return f"{base}_{digest}"


def detect_ghidra_install_dir() -> Path:
    env_value = os.environ.get("GHIDRA_INSTALL_DIR")
    if env_value:
        path = Path(env_value).expanduser().resolve()
        if path.exists():
            return path
        raise RuntimeError(f"GHIDRA_INSTALL_DIR 不存在: {path}")

    ghidra_run = shutil.which("ghidraRun")
    if not ghidra_run:
        raise RuntimeError("未找到 ghidraRun，请在环境变量中提供 GHIDRA_INSTALL_DIR。")

    ghidra_run_path = Path(ghidra_run).resolve()
    if ghidra_run_path.parent.name == "bin":
        candidate = ghidra_run_path.parent.parent / "libexec"
        if candidate.exists():
            return candidate
    if ghidra_run_path.parent.name == "libexec":
        return ghidra_run_path.parent

    raise RuntimeError(f"无法从 ghidraRun 推断安装目录: {ghidra_run_path}")


def ensure_ghidra_started() -> Path:
    install_dir = detect_ghidra_install_dir()
    if not pyghidra.started():
        pyghidra.start(install_dir=install_dir)
        eprint(f"[ghidra-headless-mcp] started pyghidra with install_dir={install_dir}")
    STATE.ghidra_install_dir = install_dir
    return install_dir


def get_source_type():
    ensure_ghidra_started()
    from ghidra.program.model.symbol import SourceType
    return SourceType


def close_current_project() -> None:
    if STATE.project is not None:
        try:
            STATE.project.close()
        except Exception:
            eprint("[ghidra-headless-mcp] warning: failed to close current project cleanly")
            eprint(traceback.format_exc())
    STATE.project = None
    STATE.nested_project_dir = None
    STATE.project_name = None
    STATE.program_path = None
    STATE.program_name = None
    STATE.binary_path = None


def ensure_loaded() -> None:
    if STATE.project is None or not STATE.program_path or not STATE.binary_path:
        raise RuntimeError("当前没有已打开的二进制。请先调用 open_binary。")


def clamp_limit(raw_value: Any, default: int = DEFAULT_LIMIT) -> int:
    if raw_value is None:
        return default
    value = int(raw_value)
    if value <= 0:
        return default
    return min(value, MAX_LIMIT)


def normalize_offset(raw_value: Any) -> int:
    if raw_value is None:
        return 0
    value = int(raw_value)
    return max(0, value)


def open_active_program():
    ensure_loaded()
    return pyghidra.program_context(STATE.project, STATE.program_path)


def iter_functions(program):
    function_manager = program.getFunctionManager()
    return function_manager.getFunctions(True)


def normalize_address(value: str) -> str:
    normalized = value.strip().lower()
    return normalized[2:] if normalized.startswith("0x") else normalized


def parse_address(program, value: str):
    if not value or not str(value).strip():
        raise RuntimeError("address 不能为空。")
    text = str(value).strip()
    factory = program.getAddressFactory()
    try:
        address = factory.getAddress(text)
        if address is not None:
            return address
    except Exception:
        pass
    normalized = normalize_address(text)
    try:
        address = factory.getAddress(normalized)
        if address is not None:
            return address
    except Exception:
        pass
    raise RuntimeError(f"无法解析地址: {value}")


def resolve_function(program, *, name: str | None = None, address: str | None = None):
    exact_matches = []
    fuzzy_matches = []
    normalized_name = name.lower() if name else None
    normalized_address = normalize_address(address) if address else None

    function_iterator = iter_functions(program)
    while function_iterator.hasNext():
        function = function_iterator.next()
        function_name = function.getName()
        entry = str(function.getEntryPoint())

        if normalized_address and normalize_address(entry) == normalized_address:
            return function
        if normalized_name:
            if function_name.lower() == normalized_name:
                exact_matches.append(function)
            elif normalized_name in function_name.lower():
                fuzzy_matches.append(function)

    if exact_matches:
        return exact_matches[0]
    if fuzzy_matches:
        return fuzzy_matches[0]

    if address:
        raise RuntimeError(f"未找到地址为 {address} 的函数。")
    raise RuntimeError(f"未找到名称匹配 {name} 的函数。")


def function_summary(function) -> dict[str, Any]:
    signature = None
    try:
        signature = function.getSignature().getPrototypeString()
    except Exception:
        signature = None
    return {
        "name": function.getName(),
        "address": str(function.getEntryPoint()),
        "signature": signature
    }


def paginate_items(items: list[dict[str, Any]], *, offset: int, limit: int) -> dict[str, Any]:
    total = len(items)
    return {"offset": offset, "limit": limit, "total": total, "items": items[offset:offset + limit]}


def collect_imports(program, *, query: str | None) -> list[dict[str, Any]]:
    query_lower = query.lower() if query else None
    symbol_table = program.getSymbolTable()
    external_symbols = symbol_table.getExternalSymbols()
    items: list[dict[str, Any]] = []
    while external_symbols.hasNext():
        symbol = external_symbols.next()
        name = symbol.getName(True)
        if query_lower and query_lower not in name.lower():
            continue
        items.append(
            {
                "address": str(symbol.getAddress()),
                "name": name,
            }
        )
    return items


def collect_exports(program, *, query: str | None) -> list[dict[str, Any]]:
    query_lower = query.lower() if query else None
    symbol_table = program.getSymbolTable()
    items: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    try:
        export_iter = symbol_table.getExternalEntryPointIterator()
        while export_iter.hasNext():
            address = export_iter.next()
            for symbol in symbol_table.getSymbols(address):
                name = symbol.getName()
                if query_lower and query_lower not in name.lower():
                    continue
                key = (str(address), name)
                if key in seen:
                    continue
                seen.add(key)
                items.append(
                    {
                        "address": str(address),
                        "name": name,
                    }
                )
    except Exception:
        pass

    symbol_iter = symbol_table.getAllSymbols(True)
    while symbol_iter.hasNext():
        symbol = symbol_iter.next()
        try:
            is_export = symbol.isExternalEntryPoint()
        except Exception:
            is_export = False
        if not is_export:
            continue
        name = symbol.getName()
        if query_lower and query_lower not in name.lower():
            continue
        key = (str(symbol.getAddress()), name)
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "address": str(symbol.getAddress()),
                "name": name,
            }
        )

    items.sort(key=lambda item: (item["address"], item["name"]))
    return items


def collect_segments(program, *, query: str | None) -> list[dict[str, Any]]:
    query_lower = query.lower() if query else None
    items: list[dict[str, Any]] = []
    for block in program.getMemory().getBlocks():
        name = block.getName()
        if query_lower and query_lower not in name.lower():
            continue
        try:
            size = int(block.getSize())
        except Exception:
            size = None
        items.append(
            {
                "name": name,
                "start": str(block.getStart()),
                "end": str(block.getEnd()),
                "size": size,
                "read": bool(block.isRead()),
                "write": bool(block.isWrite()),
                "execute": bool(block.isExecute()),
                "initialized": bool(block.isInitialized()),
            }
        )
    return items


def build_xref_to_item(program, ref) -> dict[str, Any]:
    from_address = ref.getFromAddress()
    ref_type = ref.getReferenceType()
    function = program.getFunctionManager().getFunctionContaining(from_address)
    return {
        "from_address": str(from_address),
        "from_function": function.getName() if function is not None else None,
        "reference_type": ref_type.getName(),
    }


def build_xref_from_item(program, ref) -> dict[str, Any]:
    to_address = ref.getToAddress()
    ref_type = ref.getReferenceType()
    target_function = program.getFunctionManager().getFunctionAt(to_address)
    listing = program.getListing()
    target_data = None
    try:
        target_data = listing.getDataAt(to_address)
    except Exception:
        target_data = None
    data_label = None
    if target_data is not None:
        try:
            data_label = target_data.getLabel() or target_data.getPathName()
        except Exception:
            data_label = str(target_data)
    return {
        "to_address": str(to_address),
        "to_function": target_function.getName() if target_function is not None else None,
        "to_data": data_label,
        "reference_type": ref_type.getName(),
    }


def collect_strings(program, *, min_length: int, query: str | None) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    listing = program.getListing()
    data_iterator = listing.getDefinedData(True)
    query_lower = query.lower() if query else None

    while data_iterator.hasNext():
        data = data_iterator.next()
        value = None
        try:
            if hasattr(data, "hasStringValue") and data.hasStringValue():
                value = data.getValue()
        except Exception:
            value = None
        if value is None:
            try:
                value = data.getValue()
            except Exception:
                value = None
        if value is None:
            continue

        text = str(value).replace("\x00", "")
        if len(text) < min_length:
            continue
        if query_lower and query_lower not in text.lower():
            continue

        results.append({"address": str(data.getAddress()), "text": text})

    return results


def handle_open_binary(arguments: dict[str, Any]) -> dict[str, Any]:
    ensure_ghidra_started()

    binary_path = Path(arguments["binary_path"]).expanduser().resolve()
    if not binary_path.exists():
        raise RuntimeError(f"二进制文件不存在: {binary_path}")
    if not binary_path.is_file():
        raise RuntimeError(f"目标不是文件: {binary_path}")

    analyze = arguments.get("analyze", True)
    project_root = Path(arguments.get("project_root", os.environ.get("GHIDRA_PROJECTS_DIR", DEFAULT_PROJECTS_DIR))).expanduser().resolve()
    project_root.mkdir(parents=True, exist_ok=True)
    project_name = arguments.get("project_name") or sanitize_project_name(binary_path)
    program_name = binary_path.name

    warnings.filterwarnings("ignore", category=DeprecationWarning)
    with pyghidra.open_program(
        binary_path,
        project_location=project_root,
        project_name=project_name,
        analyze=bool(analyze),
        program_name=program_name,
        nested_project_location=True,
    ) as flat_api:
        program = flat_api.currentProgram
        function_count = program.getFunctionManager().getFunctionCount()
        image_base = str(program.getImageBase())

    close_current_project()
    nested_project_dir = project_root / project_name
    STATE.project = pyghidra.open_project(nested_project_dir, project_name, create=False)
    STATE.nested_project_dir = nested_project_dir
    STATE.project_name = project_name
    STATE.program_path = f"/{program_name}"
    STATE.program_name = program_name
    STATE.binary_path = binary_path

    with open_active_program() as program:
        strings_preview = collect_strings(program, min_length=4, query=None)[:5]
        import_count = 0
        external_symbols = program.getSymbolTable().getExternalSymbols()
        while external_symbols.hasNext():
            external_symbols.next()
            import_count += 1

    return {
        "binary_path": str(binary_path),
        "project_name": project_name,
        "project_dir": str(nested_project_dir),
        "program_path": STATE.program_path,
        "function_count": function_count,
        "import_count": import_count,
        "image_base": image_base,
        "strings_preview": strings_preview,
    }


def handle_get_current_binary(_: dict[str, Any]) -> dict[str, Any]:
    ensure_loaded()
    with open_active_program() as program:
        return {
            "binary_path": str(STATE.binary_path),
            "project_name": STATE.project_name,
            "project_dir": str(STATE.nested_project_dir),
            "program_path": STATE.program_path,
            "program_name": STATE.program_name,
            "language_id": str(program.getLanguageID()),
            "compiler_spec": str(program.getCompilerSpec().getCompilerSpecID()),
            "image_base": str(program.getImageBase()),
            "function_count": program.getFunctionManager().getFunctionCount(),
        }


def handle_list_functions(arguments: dict[str, Any]) -> dict[str, Any]:
    ensure_loaded()
    offset = normalize_offset(arguments.get("offset"))
    limit = clamp_limit(arguments.get("limit"))
    query = arguments.get("query")
    query_lower = query.lower() if query else None

    with open_active_program() as program:
        results = []
        function_iterator = iter_functions(program)
        while function_iterator.hasNext():
            function = function_iterator.next()
            if query_lower and query_lower not in function.getName().lower():
                continue
            results.append(function_summary(function))

    return paginate_items(results, offset=offset, limit=limit)


def handle_search_functions_by_name(arguments: dict[str, Any]) -> dict[str, Any]:
    query = arguments.get("query")
    if not query:
        raise RuntimeError("query 不能为空。")
    return handle_list_functions(arguments)


def decompile_target(*, name: str | None = None, address: str | None = None) -> dict[str, Any]:
    ensure_loaded()
    ensure_ghidra_started()
    with open_active_program() as program:
        function = resolve_function(program, name=name, address=address)
        from ghidra.app.decompiler import DecompInterface

        decompiler = DecompInterface()
        try:
            decompiler.openProgram(program)
            result = decompiler.decompileFunction(function, DEFAULT_TIMEOUT_SECONDS, None)
            if not result.decompileCompleted():
                raise RuntimeError(result.getErrorMessage() or "Ghidra 反编译失败。")
            decompiled = result.getDecompiledFunction()
            return {
                "function": function_summary(function),
                "decompiled_code": decompiled.getC(),
            }
        finally:
            decompiler.dispose()


def handle_decompile_function(arguments: dict[str, Any]) -> dict[str, Any]:
    return decompile_target(name=arguments["name"])


def handle_decompile_function_by_address(arguments: dict[str, Any]) -> dict[str, Any]:
    return decompile_target(address=arguments["address"])


def handle_disassemble_function(arguments: dict[str, Any]) -> dict[str, Any]:
    ensure_loaded()
    limit = clamp_limit(arguments.get("limit"), default=200)
    with open_active_program() as program:
        function = resolve_function(program, address=arguments["address"])
        listing = program.getListing()
        instructions = listing.getInstructions(function.getBody(), True)
        rows = []
        while instructions.hasNext() and len(rows) < limit:
            instruction = instructions.next()
            rows.append(
                {
                    "address": str(instruction.getAddress()),
                    "instruction": str(instruction),
                }
            )

        return {
            "function": function_summary(function),
            "instruction_count": len(rows),
            "instructions": rows,
        }


def handle_list_strings(arguments: dict[str, Any]) -> dict[str, Any]:
    ensure_loaded()
    offset = normalize_offset(arguments.get("offset"))
    limit = clamp_limit(arguments.get("limit"))
    min_length = int(arguments.get("min_length", 4))
    query = arguments.get("query")

    with open_active_program() as program:
        strings = collect_strings(program, min_length=min_length, query=query)

    return paginate_items(strings, offset=offset, limit=limit)


def handle_list_imports(arguments: dict[str, Any]) -> dict[str, Any]:
    ensure_loaded()
    offset = normalize_offset(arguments.get("offset"))
    limit = clamp_limit(arguments.get("limit"))
    query = arguments.get("query")
    query_lower = query.lower() if query else None

    with open_active_program() as program:
        items = collect_imports(program, query=query_lower if query_lower else None)
    return paginate_items(items, offset=offset, limit=limit)


def handle_get_xrefs_to(arguments: dict[str, Any]) -> dict[str, Any]:
    ensure_loaded()
    offset = normalize_offset(arguments.get("offset"))
    limit = clamp_limit(arguments.get("limit"))
    with open_active_program() as program:
        address = parse_address(program, arguments["address"])
        ref_manager = program.getReferenceManager()
        ref_iter = ref_manager.getReferencesTo(address)
        items = []
        while ref_iter.hasNext():
            items.append(build_xref_to_item(program, ref_iter.next()))
    return {
        "address": str(address),
        **paginate_items(items, offset=offset, limit=limit),
    }


def handle_get_xrefs_from(arguments: dict[str, Any]) -> dict[str, Any]:
    ensure_loaded()
    offset = normalize_offset(arguments.get("offset"))
    limit = clamp_limit(arguments.get("limit"))
    with open_active_program() as program:
        address = parse_address(program, arguments["address"])
        ref_manager = program.getReferenceManager()
        refs = ref_manager.getReferencesFrom(address)
        items = [build_xref_from_item(program, ref) for ref in refs]
    return {
        "address": str(address),
        **paginate_items(items, offset=offset, limit=limit),
    }


def handle_get_function_xrefs(arguments: dict[str, Any]) -> dict[str, Any]:
    ensure_loaded()
    offset = normalize_offset(arguments.get("offset"))
    limit = clamp_limit(arguments.get("limit"))
    name = arguments.get("name")
    address = arguments.get("address")
    if not name and not address:
        raise RuntimeError("name 或 address 至少要提供一个。")
    with open_active_program() as program:
        function = resolve_function(program, name=name, address=address)
        entry = function.getEntryPoint()
        ref_iter = program.getReferenceManager().getReferencesTo(entry)
        items = []
        while ref_iter.hasNext():
            items.append(build_xref_to_item(program, ref_iter.next()))
    return {
        "function": function_summary(function),
        **paginate_items(items, offset=offset, limit=limit),
    }


def handle_rename_function_by_address(arguments: dict[str, Any]) -> dict[str, Any]:
    ensure_loaded()
    new_name = str(arguments["new_name"]).strip()
    if not new_name:
        raise RuntimeError("new_name 不能为空。")
    source_type = get_source_type()
    with open_active_program() as program:
        function = resolve_function(program, address=arguments["address"])
        old_name = function.getName()
        old_address = str(function.getEntryPoint())
        with pyghidra.transaction(program, "Rename function by address"):
            function.setName(new_name, source_type.USER_DEFINED)
            program.flushEvents()
        program.save("Rename function by address", None)
    return {
        "status": "success",
        "address": old_address,
        "old_name": old_name,
        "new_name": new_name,
    }


def handle_rename_function(arguments: dict[str, Any]) -> dict[str, Any]:
    ensure_loaded()
    new_name = str(arguments["new_name"]).strip()
    if not new_name:
        raise RuntimeError("new_name 不能为空。")
    source_type = get_source_type()
    with open_active_program() as program:
        function = resolve_function(program, name=arguments["name"])
        old_name = function.getName()
        old_address = str(function.getEntryPoint())
        with pyghidra.transaction(program, "Rename function"):
            function.setName(new_name, source_type.USER_DEFINED)
            program.flushEvents()
        program.save("Rename function", None)
    return {
        "status": "success",
        "address": old_address,
        "old_name": old_name,
        "new_name": new_name,
    }


def handle_rename_data(arguments: dict[str, Any]) -> dict[str, Any]:
    ensure_loaded()
    new_name = str(arguments["new_name"]).strip()
    if not new_name:
        raise RuntimeError("new_name 不能为空。")
    source_type = get_source_type()
    with open_active_program() as program:
        address = parse_address(program, arguments["address"])
        listing = program.getListing()
        data = listing.getDefinedDataAt(address)
        if data is None:
            raise RuntimeError(f"地址 {address} 没有 defined data。")
        sym_table = program.getSymbolTable()
        symbol = sym_table.getPrimarySymbol(address)
        previous_name = symbol.getName() if symbol is not None else None
        action = "renamed"
        with pyghidra.transaction(program, "Rename data"):
            if symbol is not None:
                if symbol.getName() != new_name:
                    symbol.setName(new_name, source_type.USER_DEFINED)
                else:
                    action = "noop"
            else:
                sym_table.createLabel(address, new_name, source_type.USER_DEFINED)
                action = "created_label"
            program.flushEvents()
        program.save("Rename data", None)
    return {
        "status": "success",
        "address": str(address),
        "old_name": previous_name,
        "new_name": new_name,
        "action": action,
    }


def handle_list_exports(arguments: dict[str, Any]) -> dict[str, Any]:
    ensure_loaded()
    offset = normalize_offset(arguments.get("offset"))
    limit = clamp_limit(arguments.get("limit"))
    query = arguments.get("query")
    with open_active_program() as program:
        items = collect_exports(program, query=query)
    return paginate_items(items, offset=offset, limit=limit)


def handle_list_segments(arguments: dict[str, Any]) -> dict[str, Any]:
    ensure_loaded()
    offset = normalize_offset(arguments.get("offset"))
    limit = clamp_limit(arguments.get("limit"))
    query = arguments.get("query")
    with open_active_program() as program:
        items = collect_segments(program, query=query)
    return paginate_items(items, offset=offset, limit=limit)


def handle_close_binary(_: dict[str, Any]) -> dict[str, Any]:
    had_binary = STATE.binary_path is not None
    close_current_project()
    return {"closed": had_binary}


TOOL_HANDLERS = {
    "open_binary": handle_open_binary,
    "get_current_binary": handle_get_current_binary,
    "list_functions": handle_list_functions,
    "search_functions_by_name": handle_search_functions_by_name,
    "decompile_function": handle_decompile_function,
    "decompile_function_by_address": handle_decompile_function_by_address,
    "disassemble_function": handle_disassemble_function,
    "list_strings": handle_list_strings,
    "list_imports": handle_list_imports,
    "get_xrefs_to": handle_get_xrefs_to,
    "get_xrefs_from": handle_get_xrefs_from,
    "get_function_xrefs": handle_get_function_xrefs,
    "rename_function_by_address": handle_rename_function_by_address,
    "rename_function": handle_rename_function,
    "rename_data": handle_rename_data,
    "list_exports": handle_list_exports,
    "list_segments": handle_list_segments,
    "close_binary": handle_close_binary,
}


def handle_request(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        if tool_name not in TOOL_HANDLERS:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"未知工具: {tool_name}"},
            }
        try:
            result = TOOL_HANDLERS[tool_name](arguments)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": [{"type": "text", "text": json_dumps(result)}]},
            }
        except Exception as exc:
            eprint(f"[ghidra-headless-mcp] tool {tool_name} failed: {exc}")
            eprint(traceback.format_exc())
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": str(exc)},
            }

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> int:
    eprint(f"[ghidra-headless-mcp] booting {SERVER_NAME} {SERVER_VERSION}")
    eprint(f"[ghidra-headless-mcp] default projects dir: {Path(os.environ.get('GHIDRA_PROJECTS_DIR', DEFAULT_PROJECTS_DIR)).expanduser()}")

    buffer = ""
    for line in sys.stdin:
        buffer += line
        try:
            message = json.loads(buffer)
        except json.JSONDecodeError:
            continue
        buffer = ""

        try:
            response = handle_request(message)
        except Exception as exc:
            eprint(f"[ghidra-headless-mcp] request handler crash: {exc}")
            eprint(traceback.format_exc())
            response = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {"code": -32603, "message": str(exc)},
            }
        if response is not None:
            respond(response)

    close_current_project()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
