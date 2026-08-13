"""Hand-written lexer for the current NES Pascal subset."""

from dataclasses import dataclass
from enum import Enum, auto

from .diagnostics import CompilerError, DiagnosticCode, SourceLocation


class TokenKind(Enum):
    PROGRAM = auto()
    TYPE = auto()
    CONST = auto()
    VAR = auto()
    PROCEDURE = auto()
    BEGIN = auto()
    END = auto()
    IF = auto()
    THEN = auto()
    ELSE = auto()
    WHILE = auto()
    DO = auto()
    REPEAT = auto()
    UNTIL = auto()
    BREAK = auto()
    CONTINUE = auto()
    INC = auto()
    DEC = auto()
    FOR = auto()
    TO = auto()
    DOWNTO = auto()
    TRUE = auto()
    FALSE = auto()
    NOT = auto()
    AND = auto()
    OR = auto()
    ARRAY = auto()
    OF = auto()
    IDENTIFIER = auto()
    HEX_LITERAL = auto()
    SEMICOLON = auto()
    DOT = auto()
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_BRACKET = auto()
    RIGHT_BRACKET = auto()
    COMMA = auto()
    COLON = auto()
    EQUAL = auto()
    ASSIGN = auto()
    PLUS = auto()
    MINUS = auto()
    NOT_EQUAL = auto()
    LESS = auto()
    GREATER = auto()
    LESS_EQUAL = auto()
    GREATER_EQUAL = auto()
    EOF = auto()


KEYWORDS = {
    "program": TokenKind.PROGRAM,
    "type": TokenKind.TYPE,
    "const": TokenKind.CONST,
    "var": TokenKind.VAR,
    "procedure": TokenKind.PROCEDURE,
    "begin": TokenKind.BEGIN,
    "end": TokenKind.END,
    "if": TokenKind.IF,
    "then": TokenKind.THEN,
    "else": TokenKind.ELSE,
    "while": TokenKind.WHILE,
    "do": TokenKind.DO,
    "repeat": TokenKind.REPEAT,
    "until": TokenKind.UNTIL,
    "break": TokenKind.BREAK,
    "continue": TokenKind.CONTINUE,
    "inc": TokenKind.INC,
    "dec": TokenKind.DEC,
    "for": TokenKind.FOR,
    "to": TokenKind.TO,
    "downto": TokenKind.DOWNTO,
    "true": TokenKind.TRUE,
    "false": TokenKind.FALSE,
    "not": TokenKind.NOT,
    "and": TokenKind.AND,
    "or": TokenKind.OR,
    "array": TokenKind.ARRAY,
    "of": TokenKind.OF,
}

PUNCTUATION = {
    ";": TokenKind.SEMICOLON,
    ".": TokenKind.DOT,
    "(": TokenKind.LEFT_PAREN,
    ")": TokenKind.RIGHT_PAREN,
    "[": TokenKind.LEFT_BRACKET,
    "]": TokenKind.RIGHT_BRACKET,
    ",": TokenKind.COMMA,
    ":": TokenKind.COLON,
    "=": TokenKind.EQUAL,
    "+": TokenKind.PLUS,
    "-": TokenKind.MINUS,
    "<": TokenKind.LESS,
    ">": TokenKind.GREATER,
}


@dataclass(frozen=True, slots=True)
class Token:
    kind: TokenKind
    text: str
    line: int
    column: int
    value: int | None = None


class Lexer:
    def __init__(self, source: str, filename: str = "<input>") -> None:
        self.source = source
        self.filename = filename
        self.position = 0
        self.line = 1
        self.column = 1
        self.lines = source.splitlines()

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while not self._at_end():
            character = self._current()
            if character.isspace():
                self._consume_whitespace()
            elif character.isalpha():
                tokens.append(self._identifier())
            elif character == "$":
                tokens.append(self._hex_literal())
            elif character == ":" and self._peek() == "=":
                tokens.append(Token(TokenKind.ASSIGN, ":=", self.line, self.column))
                self._advance()
                self._advance()
            elif character == "<" and self._peek() in ("=", ">"):
                text = character + self._peek()
                kind = (
                    TokenKind.LESS_EQUAL
                    if self._peek() == "="
                    else TokenKind.NOT_EQUAL
                )
                tokens.append(Token(kind, text, self.line, self.column))
                self._advance()
                self._advance()
            elif character == ">" and self._peek() == "=":
                tokens.append(
                    Token(TokenKind.GREATER_EQUAL, ">=", self.line, self.column)
                )
                self._advance()
                self._advance()
            elif character in PUNCTUATION:
                tokens.append(
                    Token(PUNCTUATION[character], character, self.line, self.column)
                )
                self._advance()
            else:
                self._error(
                    DiagnosticCode.UNEXPECTED_CHARACTER,
                    f"Unexpected character: {character!r}.",
                    "Remove the character or use a construct supported by the language.",
                )
        tokens.append(Token(TokenKind.EOF, "", self.line, self.column))
        return tokens

    def _identifier(self) -> Token:
        line, column, start = self.line, self.column, self.position
        while not self._at_end() and (
            self._current().isalnum() or self._current() == "_"
        ):
            self._advance()
        text = self.source[start : self.position]
        kind = KEYWORDS.get(text.lower(), TokenKind.IDENTIFIER)
        return Token(kind, text, line, column)

    def _hex_literal(self) -> Token:
        line, column, start = self.line, self.column, self.position
        self._advance()
        digits_start = self.position
        while not self._at_end() and self._current() in "0123456789abcdefABCDEF":
            self._advance()
        if self.position == digits_start:
            self._error_at(
                line,
                column,
                DiagnosticCode.MALFORMED_HEXADECIMAL_LITERAL,
                "Hexadecimal literal has no digits after '$'.",
                "Use a literal such as $00 or $21.",
            )
        text = self.source[start : self.position]
        return Token(TokenKind.HEX_LITERAL, text, line, column, int(text[1:], 16))

    def _consume_whitespace(self) -> None:
        while not self._at_end() and self._current().isspace():
            self._advance()

    def _advance(self) -> None:
        character = self.source[self.position]
        self.position += 1
        if character == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

    def _current(self) -> str:
        return self.source[self.position]

    def _peek(self) -> str:
        next_position = self.position + 1
        return self.source[next_position] if next_position < len(self.source) else ""

    def _at_end(self) -> bool:
        return self.position >= len(self.source)

    def _source_line(self, line: int) -> str:
        return self.lines[line - 1] if 0 < line <= len(self.lines) else ""

    def _error(
        self, code: DiagnosticCode, message: str, suggestion: str
    ) -> None:
        self._error_at(self.line, self.column, code, message, suggestion)

    def _error_at(
        self,
        line: int,
        column: int,
        code: DiagnosticCode,
        message: str,
        suggestion: str,
    ) -> None:
        raise CompilerError(
            code,
            message,
            SourceLocation(self.filename, line, column),
            self._source_line(line),
            suggestion,
        )


def tokenize(source: str, filename: str = "<input>") -> list[Token]:
    return Lexer(source, filename).tokenize()
