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
    UNKNOWN_TYPE = "E4001"
    INVALID_NES_COLOR_VALUE = "E4002"
    INVALID_BYTE_VALUE = "E4003"
    INCOMPATIBLE_TYPES = "E4004"
    MISSING_TOOLCHAIN = "E5001"
    TOOLCHAIN_FAILURE = "E5002"
    FILE_ACCESS_FAILURE = "E6001"


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
    DiagnosticCode.MISSING_TOOLCHAIN: DiagnosticDefinition(
        DiagnosticCategory.CODE_GENERATION, "Missing toolchain"
    ),
    DiagnosticCode.TOOLCHAIN_FAILURE: DiagnosticDefinition(
        DiagnosticCategory.CODE_GENERATION, "Toolchain failure"
    ),
    DiagnosticCode.FILE_ACCESS_FAILURE: DiagnosticDefinition(
        DiagnosticCategory.RUNTIME, "File access failure"
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
