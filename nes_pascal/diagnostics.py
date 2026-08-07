"""User-friendly diagnostics for source errors."""

from dataclasses import dataclass
from enum import StrEnum


class DiagnosticCategory(StrEnum):
    LEXICAL = "Lexical Analysis"
    PARSER = "Parser / Syntax"
    SEMANTIC = "Semantic Analysis"
    TYPE_SYSTEM = "Type System"
    CODE_GENERATION = "Code Generation"
    RUNTIME = "Runtime Validation"


class DiagnosticCode(StrEnum):
    UNEXPECTED_CHARACTER = "E1000"
    MALFORMED_HEXADECIMAL_LITERAL = "E1002"
    UNKNOWN_COMMAND = "E2101"
    INVALID_SYNTAX = "E2102"
    MISSING_RUN = "E3001"
    STATEMENT_AFTER_RUN = "E3002"
    INVALID_BACKGROUND_COLOR_CALL_COUNT = "E3003"
    DUPLICATE_SYMBOL = "E3004"
    UNKNOWN_IDENTIFIER = "E3005"
    ASSIGNMENT_TO_CONSTANT = "E3006"
    UNKNOWN_ASSIGNMENT_TARGET = "E3007"
    VARIABLE_READ_BEFORE_ASSIGNMENT = "E3008"
    CONDITIONAL_RUNTIME_COMMAND = "E3009"
    LOOP_CONTROL_OUTSIDE_LOOP = "E3010"
    LOOP_RUNTIME_COMMAND = "E3011"
    FOR_CONTROL_VARIABLE_MODIFICATION = "E3012"
    UNKNOWN_PROCEDURE = "E3013"
    RECURSIVE_PROCEDURE_CALL = "E3014"
    PROCEDURE_RUNTIME_COMMAND = "E3015"
    PROCEDURE_ARGUMENT_COUNT = "E3016"
    FRAME_WAIT_BEFORE_RUNTIME = "E3017"
    UNKNOWN_CALLBACK_PROCEDURE = "E3018"
    INVALID_CALLBACK_SIGNATURE = "E3019"
    DUPLICATE_UPDATE_CALLBACK = "E3020"
    DUPLICATE_VBLANK_CALLBACK = "E3021"
    INVALID_CALLBACK_REGISTRATION_CONTEXT = "E3022"
    VBLANK_UNSAFE_OPERATION = "E3023"
    INVALID_CALLBACK_CALL_GRAPH = "E3024"
    CONFLICTING_CALLBACK_REGISTRATION = "E3025"
    INVALID_CONTROLLER_INDEX = "E3026"
    DYNAMIC_CONTROLLER_INDEX = "E3027"
    INVALID_CONTROLLER_BUTTON = "E3028"
    INVALID_CONTROLLER_ARGUMENT_COUNT = "E3029"
    INVALID_SPRITE_ZERO_ARGUMENT_COUNT = "E3030"
    INVALID_BACKGROUND_PALETTE_INDEX = "E3031"
    INVALID_SPRITE_PALETTE_INDEX = "E3032"
    INVALID_PALETTE_COLOR_INDEX = "E3033"
    INVALID_PALETTE_ARGUMENT_COUNT = "E3034"
    INVALID_BACKGROUND_LOAD_ARGUMENT_COUNT = "E3035"
    BACKGROUND_LOAD_AFTER_RUN = "E3036"
    DUPLICATE_BACKGROUND_LOAD = "E3037"
    INVALID_SET_TILE_ARGUMENT_COUNT = "E3038"
    INVALID_GET_TILE_ARGUMENT_COUNT = "E3039"
    INVALID_SET_ATTRIBUTE_ARGUMENT_COUNT = "E3040"
    INVALID_CLEAR_BACKGROUND_UPDATES_ARGUMENT_COUNT = "E3041"
    INVALID_TILE_COORDINATE = "E3042"
    INVALID_ATTRIBUTE_COORDINATE = "E3043"
    INVALID_BACKGROUND_OVERFLOW_QUERY_ARGUMENT_COUNT = "E3044"
    INVALID_BACKGROUND_OVERFLOW_CLEAR_ARGUMENT_COUNT = "E3045"
    INVALID_SET_SCROLL_ARGUMENT_COUNT = "E3046"
    UNKNOWN_TYPE = "E4001"
    INVALID_NES_COLOR_VALUE = "E4002"
    INVALID_BYTE_VALUE = "E4003"
    INCOMPATIBLE_TYPES = "E4004"
    UNSUPPORTED_PARAMETER_TYPE = "E4005"
    INVALID_CONTROLLER_ARGUMENT_TYPE = "E4006"
    INVALID_PALETTE_ARGUMENT_TYPE = "E4007"
    MISSING_TOOLCHAIN = "E5001"
    TOOLCHAIN_FAILURE = "E5002"
    USER_RAM_EXHAUSTED = "E5003"
    TEMPORARY_RAM_EXHAUSTED = "E5004"
    INVALID_MEMORY_LAYOUT = "E5005"
    RAM_SEGMENT_OVERFLOW = "E5006"
    FILE_ACCESS_FAILURE = "E6001"
    CHR_ASSET_NOT_FOUND = "E6002"
    CHR_ASSET_READ_FAILURE = "E6003"
    INVALID_CHR_ROM_SIZE = "E6004"
    INVALID_BACKGROUND_ASSET_CONFIGURATION = "E6005"
    BACKGROUND_ASSET_NOT_FOUND = "E6006"
    BACKGROUND_ASSET_READ_FAILURE = "E6007"
    INVALID_BACKGROUND_ASSET_SIZE = "E6008"
    BACKGROUND_ASSET_REQUIRED = "E6009"
    INVALID_MIRRORING_CONFIGURATION = "E6010"


@dataclass(frozen=True, slots=True)
class DiagnosticDefinition:
    category: DiagnosticCategory
    title: str


DIAGNOSTIC_CATALOG: dict[DiagnosticCode, DiagnosticDefinition] = {
    DiagnosticCode.UNEXPECTED_CHARACTER: DiagnosticDefinition(
        DiagnosticCategory.LEXICAL, "Unexpected character"
    ),
    DiagnosticCode.MALFORMED_HEXADECIMAL_LITERAL: DiagnosticDefinition(
        DiagnosticCategory.LEXICAL, "Malformed hexadecimal literal"
    ),
    DiagnosticCode.UNKNOWN_COMMAND: DiagnosticDefinition(
        DiagnosticCategory.PARSER, "Unknown command"
    ),
    DiagnosticCode.INVALID_SYNTAX: DiagnosticDefinition(
        DiagnosticCategory.PARSER, "Invalid syntax"
    ),
    DiagnosticCode.MISSING_RUN: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Missing nes.run"
    ),
    DiagnosticCode.STATEMENT_AFTER_RUN: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Statement after nes.run"
    ),
    DiagnosticCode.INVALID_BACKGROUND_COLOR_CALL_COUNT: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Invalid background-color call count"
    ),
    DiagnosticCode.DUPLICATE_SYMBOL: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Duplicate symbol"
    ),
    DiagnosticCode.UNKNOWN_IDENTIFIER: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Unknown identifier"
    ),
    DiagnosticCode.ASSIGNMENT_TO_CONSTANT: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Assignment to constant"
    ),
    DiagnosticCode.UNKNOWN_ASSIGNMENT_TARGET: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Unknown assignment target"
    ),
    DiagnosticCode.VARIABLE_READ_BEFORE_ASSIGNMENT: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Variable read before assignment"
    ),
    DiagnosticCode.CONDITIONAL_RUNTIME_COMMAND: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Runtime command inside conditional"
    ),
    DiagnosticCode.LOOP_CONTROL_OUTSIDE_LOOP: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Loop control outside loop"
    ),
    DiagnosticCode.LOOP_RUNTIME_COMMAND: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Runtime command inside loop"
    ),
    DiagnosticCode.FOR_CONTROL_VARIABLE_MODIFICATION: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "For control variable modification"
    ),
    DiagnosticCode.UNKNOWN_PROCEDURE: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Unknown procedure"
    ),
    DiagnosticCode.RECURSIVE_PROCEDURE_CALL: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Recursive procedure call"
    ),
    DiagnosticCode.PROCEDURE_RUNTIME_COMMAND: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Runtime command inside procedure"
    ),
    DiagnosticCode.PROCEDURE_ARGUMENT_COUNT: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Incorrect procedure argument count"
    ),
    DiagnosticCode.FRAME_WAIT_BEFORE_RUNTIME: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Frame wait before runtime start"
    ),
    DiagnosticCode.UNKNOWN_CALLBACK_PROCEDURE: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Unknown callback procedure"
    ),
    DiagnosticCode.INVALID_CALLBACK_SIGNATURE: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Invalid callback signature"
    ),
    DiagnosticCode.DUPLICATE_UPDATE_CALLBACK: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Duplicate update callback"
    ),
    DiagnosticCode.DUPLICATE_VBLANK_CALLBACK: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Duplicate VBlank callback"
    ),
    DiagnosticCode.INVALID_CALLBACK_REGISTRATION_CONTEXT: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Invalid callback registration context"
    ),
    DiagnosticCode.VBLANK_UNSAFE_OPERATION: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "VBlank-unsafe operation"
    ),
    DiagnosticCode.INVALID_CALLBACK_CALL_GRAPH: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Invalid callback call graph"
    ),
    DiagnosticCode.CONFLICTING_CALLBACK_REGISTRATION: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Conflicting callback registration"
    ),
    DiagnosticCode.INVALID_CONTROLLER_INDEX: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Invalid controller index"
    ),
    DiagnosticCode.DYNAMIC_CONTROLLER_INDEX: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Dynamic controller index"
    ),
    DiagnosticCode.INVALID_CONTROLLER_BUTTON: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Invalid controller button"
    ),
    DiagnosticCode.INVALID_CONTROLLER_ARGUMENT_COUNT: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Invalid controller argument count"
    ),
    DiagnosticCode.INVALID_SPRITE_ZERO_ARGUMENT_COUNT: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Invalid sprite-zero argument count"
    ),
    DiagnosticCode.INVALID_BACKGROUND_PALETTE_INDEX: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Invalid background palette index"
    ),
    DiagnosticCode.INVALID_SPRITE_PALETTE_INDEX: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Invalid sprite palette index"
    ),
    DiagnosticCode.INVALID_PALETTE_COLOR_INDEX: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Invalid palette color index"
    ),
    DiagnosticCode.INVALID_PALETTE_ARGUMENT_COUNT: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Invalid palette argument count"
    ),
    DiagnosticCode.INVALID_BACKGROUND_LOAD_ARGUMENT_COUNT: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Invalid background-load argument count"
    ),
    DiagnosticCode.BACKGROUND_LOAD_AFTER_RUN: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Background load after runtime start"
    ),
    DiagnosticCode.DUPLICATE_BACKGROUND_LOAD: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Duplicate background load"
    ),
    DiagnosticCode.INVALID_SET_TILE_ARGUMENT_COUNT: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Invalid set-tile argument count"
    ),
    DiagnosticCode.INVALID_GET_TILE_ARGUMENT_COUNT: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Invalid get-tile argument count"
    ),
    DiagnosticCode.INVALID_SET_ATTRIBUTE_ARGUMENT_COUNT: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Invalid set-attribute argument count"
    ),
    DiagnosticCode.INVALID_CLEAR_BACKGROUND_UPDATES_ARGUMENT_COUNT:
        DiagnosticDefinition(
            DiagnosticCategory.SEMANTIC,
            "Invalid clear-background-updates argument count",
        ),
    DiagnosticCode.INVALID_TILE_COORDINATE: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Invalid tile coordinate"
    ),
    DiagnosticCode.INVALID_ATTRIBUTE_COORDINATE: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Invalid attribute coordinate"
    ),
    DiagnosticCode.INVALID_BACKGROUND_OVERFLOW_QUERY_ARGUMENT_COUNT:
        DiagnosticDefinition(
            DiagnosticCategory.SEMANTIC,
            "Invalid background-overflow query argument count",
        ),
    DiagnosticCode.INVALID_BACKGROUND_OVERFLOW_CLEAR_ARGUMENT_COUNT:
        DiagnosticDefinition(
            DiagnosticCategory.SEMANTIC,
            "Invalid background-overflow clear argument count",
        ),
    DiagnosticCode.INVALID_SET_SCROLL_ARGUMENT_COUNT: DiagnosticDefinition(
        DiagnosticCategory.SEMANTIC, "Invalid set-scroll argument count"
    ),
    DiagnosticCode.UNKNOWN_TYPE: DiagnosticDefinition(
        DiagnosticCategory.TYPE_SYSTEM, "Unknown type"
    ),
    DiagnosticCode.INVALID_NES_COLOR_VALUE: DiagnosticDefinition(
        DiagnosticCategory.TYPE_SYSTEM, "Invalid nes_color value"
    ),
    DiagnosticCode.INVALID_BYTE_VALUE: DiagnosticDefinition(
        DiagnosticCategory.TYPE_SYSTEM, "Invalid byte value"
    ),
    DiagnosticCode.INCOMPATIBLE_TYPES: DiagnosticDefinition(
        DiagnosticCategory.TYPE_SYSTEM, "Incompatible types"
    ),
    DiagnosticCode.UNSUPPORTED_PARAMETER_TYPE: DiagnosticDefinition(
        DiagnosticCategory.TYPE_SYSTEM, "Unsupported parameter type"
    ),
    DiagnosticCode.INVALID_CONTROLLER_ARGUMENT_TYPE: DiagnosticDefinition(
        DiagnosticCategory.TYPE_SYSTEM, "Invalid controller argument type"
    ),
    DiagnosticCode.INVALID_PALETTE_ARGUMENT_TYPE: DiagnosticDefinition(
        DiagnosticCategory.TYPE_SYSTEM, "Invalid palette argument type"
    ),
    DiagnosticCode.MISSING_TOOLCHAIN: DiagnosticDefinition(
        DiagnosticCategory.CODE_GENERATION, "Missing toolchain"
    ),
    DiagnosticCode.TOOLCHAIN_FAILURE: DiagnosticDefinition(
        DiagnosticCategory.CODE_GENERATION, "Toolchain failure"
    ),
    DiagnosticCode.USER_RAM_EXHAUSTED: DiagnosticDefinition(
        DiagnosticCategory.CODE_GENERATION, "User RAM exhausted"
    ),
    DiagnosticCode.TEMPORARY_RAM_EXHAUSTED: DiagnosticDefinition(
        DiagnosticCategory.CODE_GENERATION, "Temporary RAM exhausted"
    ),
    DiagnosticCode.INVALID_MEMORY_LAYOUT: DiagnosticDefinition(
        DiagnosticCategory.CODE_GENERATION, "Invalid memory layout"
    ),
    DiagnosticCode.RAM_SEGMENT_OVERFLOW: DiagnosticDefinition(
        DiagnosticCategory.CODE_GENERATION, "RAM segment overflow"
    ),
    DiagnosticCode.FILE_ACCESS_FAILURE: DiagnosticDefinition(
        DiagnosticCategory.RUNTIME, "File access failure"
    ),
    DiagnosticCode.CHR_ASSET_NOT_FOUND: DiagnosticDefinition(
        DiagnosticCategory.RUNTIME, "CHR-ROM asset not found"
    ),
    DiagnosticCode.CHR_ASSET_READ_FAILURE: DiagnosticDefinition(
        DiagnosticCategory.RUNTIME, "CHR-ROM asset read failure"
    ),
    DiagnosticCode.INVALID_CHR_ROM_SIZE: DiagnosticDefinition(
        DiagnosticCategory.RUNTIME, "Invalid CHR-ROM size"
    ),
    DiagnosticCode.INVALID_BACKGROUND_ASSET_CONFIGURATION: DiagnosticDefinition(
        DiagnosticCategory.RUNTIME, "Invalid background asset configuration"
    ),
    DiagnosticCode.BACKGROUND_ASSET_NOT_FOUND: DiagnosticDefinition(
        DiagnosticCategory.RUNTIME, "Background asset not found"
    ),
    DiagnosticCode.BACKGROUND_ASSET_READ_FAILURE: DiagnosticDefinition(
        DiagnosticCategory.RUNTIME, "Background asset read failure"
    ),
    DiagnosticCode.INVALID_BACKGROUND_ASSET_SIZE: DiagnosticDefinition(
        DiagnosticCategory.RUNTIME, "Invalid background asset size"
    ),
    DiagnosticCode.BACKGROUND_ASSET_REQUIRED: DiagnosticDefinition(
        DiagnosticCategory.RUNTIME, "Background asset required"
    ),
    DiagnosticCode.INVALID_MIRRORING_CONFIGURATION: DiagnosticDefinition(
        DiagnosticCategory.RUNTIME, "Invalid mirroring configuration"
    ),
}


@dataclass(frozen=True, slots=True)
class SourceLocation:
    filename: str
    line: int
    column: int


class CompilerError(Exception):
    """Expected compilation error suitable for display to the user."""

    def __init__(
        self,
        code: str | DiagnosticCode,
        message: str,
        location: SourceLocation,
        source_line: str = "",
        suggestion: str | None = None,
        highlight_length: int = 1,
    ) -> None:
        super().__init__(message)
        self.code = DiagnosticCode(code).value
        self.message = message
        self.location = location
        self.source_line = source_line
        self.suggestion = suggestion
        self.highlight_length = max(1, highlight_length)

    def __str__(self) -> str:
        header = (
            f"{self.code} {self.location.filename}:"
            f"{self.location.line}:{self.location.column}"
        )
        parts = [header, "", self.message]
        if self.source_line:
            parts.extend(
                [
                    "",
                    self.source_line,
                    " " * (self.location.column - 1)
                    + "^" * self.highlight_length,
                ]
            )
        if self.suggestion:
            parts.extend(["", self.suggestion])
        return "\n".join(parts)
