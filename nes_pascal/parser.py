"""Hand-written recursive-descent parser for the current milestone."""

from .ast import (
    Assignment,
    BooleanLiteral,
    BuiltInType,
    ConstantDeclaration,
    ConstantReference,
    HexLiteral,
    Literal,
    Program,
    Run,
    SetBackgroundColor,
    SourcePosition,
    Statement,
    ValueExpression,
    VariableDeclaration,
    VariableReference,
)
from .diagnostics import CompilerError, DiagnosticCode, SourceLocation
from .lexer import Token, TokenKind, tokenize


class Parser:
    def __init__(
        self, tokens: list[Token], source: str, filename: str = "<input>"
    ) -> None:
        self.tokens = tokens
        self.source_lines = source.splitlines()
        self.filename = filename
        self.position = 0
        self.constant_names: set[str] = set()
        self.variable_names: set[str] = set()

    def parse(self) -> Program:
        self._expect(TokenKind.PROGRAM, "Expected 'program' at the start of the file.")
        name = self._expect(
            TokenKind.IDENTIFIER, "Expected a program name after 'program'."
        )
        self._expect(TokenKind.SEMICOLON, "Expected ';' after the program name.")

        constants = self._parse_constants()
        self.constant_names = {declaration.name.lower() for declaration in constants}
        variables = self._parse_variables()
        self.variable_names = {declaration.name.lower() for declaration in variables}
        self._expect(TokenKind.BEGIN, "Expected 'begin' to start the program block.")

        statements: list[Statement] = []
        while not self._check(TokenKind.END):
            if self._check(TokenKind.EOF):
                self._error(
                    self._current(),
                    DiagnosticCode.INVALID_SYNTAX,
                    "Reached the end of the file before 'end.'.",
                    "Finish the program block with 'end.'.",
                )
            statement = self._parse_statement()
            statements.append(statement)

        end_token = self._expect(TokenKind.END, "Expected 'end'.")
        self._expect(TokenKind.DOT, "Expected '.' after 'end'.")
        self._expect(TokenKind.EOF, "Unexpected content after 'end.'.")

        return Program(
            name.text,
            tuple(constants),
            tuple(variables),
            tuple(statements),
            SourcePosition(end_token.line, end_token.column),
        )

    def _parse_constants(self) -> list[ConstantDeclaration]:
        if not self._match(TokenKind.CONST):
            return []
        if not self._check(TokenKind.IDENTIFIER):
            self._error(
                self._current(),
                DiagnosticCode.INVALID_SYNTAX,
                "Expected a constant declaration after 'const'.",
                "Declare a constant as: Name: nes_color = $21;",
            )

        declarations: list[ConstantDeclaration] = []
        while self._check(TokenKind.IDENTIFIER):
            name = self._expect(TokenKind.IDENTIFIER, "Expected a constant name.")
            self._expect(TokenKind.COLON, "Expected ':' after the constant name.")
            declared_type = self._parse_type()
            self._expect(TokenKind.EQUAL, "Expected '=' after the constant type.")
            literal = self._parse_literal("constant value")
            self._expect(
                TokenKind.SEMICOLON, "Expected ';' after the constant declaration."
            )
            declarations.append(
                ConstantDeclaration(
                    name.text,
                    declared_type,
                    literal,
                    SourcePosition(name.line, name.column),
                )
            )
        return declarations

    def _parse_variables(self) -> list[VariableDeclaration]:
        if not self._match(TokenKind.VAR):
            return []
        if not self._check(TokenKind.IDENTIFIER):
            self._error(
                self._current(),
                DiagnosticCode.INVALID_SYNTAX,
                "Expected a variable declaration after 'var'.",
                "Declare a variable as: Name: byte;",
            )

        declarations: list[VariableDeclaration] = []
        while self._check(TokenKind.IDENTIFIER):
            name = self._expect(TokenKind.IDENTIFIER, "Expected a variable name.")
            self._expect(TokenKind.COLON, "Expected ':' after the variable name.")
            declared_type = self._parse_type()
            self._expect(
                TokenKind.SEMICOLON, "Expected ';' after the variable declaration."
            )
            declarations.append(
                VariableDeclaration(
                    name.text,
                    declared_type,
                    SourcePosition(name.line, name.column),
                )
            )
        return declarations

    def _parse_type(self) -> BuiltInType:
        token = self._expect(TokenKind.IDENTIFIER, "Expected a type after ':'.")
        for built_in_type in BuiltInType:
            if token.text.lower() == built_in_type.value:
                return built_in_type
        supported = ", ".join(type_.value for type_ in BuiltInType)
        self._error(
            token,
            DiagnosticCode.UNKNOWN_TYPE,
            f"Unknown type: {token.text}.",
            f"Supported types: {supported}.",
        )
        raise AssertionError("unreachable")

    def _parse_literal(self, description: str) -> Literal:
        token = self._current()
        position = SourcePosition(token.line, token.column)
        if self._match(TokenKind.HEX_LITERAL):
            assert token.value is not None
            return HexLiteral(token.value, token.text, position)
        if self._match(TokenKind.TRUE):
            return BooleanLiteral(True, token.text, position)
        if self._match(TokenKind.FALSE):
            return BooleanLiteral(False, token.text, position)
        self._error(
            token,
            DiagnosticCode.INVALID_SYNTAX,
            f"Expected a hexadecimal or boolean literal as the {description}.",
            "Use a value such as $21, true, or false.",
        )
        raise AssertionError("unreachable")

    def _parse_statement(self) -> Statement:
        if self._check(TokenKind.IDENTIFIER) and self._peek_kind() is TokenKind.ASSIGN:
            return self._parse_assignment()

        namespace = self._expect(
            TokenKind.IDENTIFIER,
            "Expected an assignment, nes.set_background_color, or nes.run.",
        )
        self._expect(TokenKind.DOT, "Expected '.' after 'nes'.")
        command = self._expect(TokenKind.IDENTIFIER, "Expected a command name.")
        qualified_name = f"{namespace.text}.{command.text}"
        normalized = qualified_name.lower()

        if namespace.text.lower() != "nes":
            self._unknown_command(namespace, qualified_name)
        if normalized == "nes.set_background_color":
            return self._parse_background_color(
                SourcePosition(namespace.line, namespace.column)
            )
        if normalized == "nes.run":
            self._expect(TokenKind.SEMICOLON, "Expected ';' after 'nes.run'.")
            return Run(SourcePosition(namespace.line, namespace.column))
        self._unknown_command(command, qualified_name)
        raise AssertionError("unreachable")

    def _parse_assignment(self) -> Assignment:
        target = self._expect(TokenKind.IDENTIFIER, "Expected an assignment target.")
        self._expect(TokenKind.ASSIGN, "Expected ':=' after the assignment target.")
        value = self._parse_value()
        self._expect(TokenKind.SEMICOLON, "Expected ';' after the assignment.")
        return Assignment(
            target.text,
            SourcePosition(target.line, target.column),
            value,
        )

    def _parse_background_color(
        self, position: SourcePosition
    ) -> SetBackgroundColor:
        self._expect(
            TokenKind.LEFT_PAREN,
            "Expected '(' after 'nes.set_background_color'.",
        )
        argument = self._parse_value()
        self._expect(
            TokenKind.RIGHT_PAREN,
            "Expected ')' after the background color.",
        )
        self._expect(
            TokenKind.SEMICOLON,
            "Expected ';' after 'nes.set_background_color(...)'.",
        )
        return SetBackgroundColor(argument, position)

    def _parse_value(self) -> ValueExpression:
        token = self._current()
        if token.kind in (
            TokenKind.HEX_LITERAL,
            TokenKind.TRUE,
            TokenKind.FALSE,
        ):
            return self._parse_literal("value")
        if self._match(TokenKind.IDENTIFIER):
            position = SourcePosition(token.line, token.column)
            if token.text.lower() in self.variable_names:
                return VariableReference(token.text, position)
            return ConstantReference(token.text, position)
        self._error(
            token,
            DiagnosticCode.INVALID_SYNTAX,
            "Expected a literal or identifier.",
            "Use a hexadecimal value, boolean value, constant, or variable.",
        )
        raise AssertionError("unreachable")

    def _unknown_command(self, token: Token, name: str) -> None:
        self._error(
            token,
            DiagnosticCode.UNKNOWN_COMMAND,
            f"Unknown command: {name}.",
            "Use an assignment, nes.set_background_color(value);, or nes.run;.",
        )

    def _match(self, kind: TokenKind) -> bool:
        if not self._check(kind):
            return False
        self.position += 1
        return True

    def _expect(self, kind: TokenKind, message: str) -> Token:
        if self._check(kind):
            token = self._current()
            self.position += 1
            return token
        self._error(
            self._current(),
            DiagnosticCode.INVALID_SYNTAX,
            message,
            "Review the program syntax.",
        )
        raise AssertionError("unreachable")

    def _check(self, kind: TokenKind) -> bool:
        return self._current().kind is kind

    def _peek_kind(self) -> TokenKind:
        next_position = self.position + 1
        if next_position >= len(self.tokens):
            return TokenKind.EOF
        return self.tokens[next_position].kind

    def _current(self) -> Token:
        return self.tokens[self.position]

    def _previous(self) -> Token:
        return self.tokens[self.position - 1]

    def _error(
        self,
        token: Token,
        code: DiagnosticCode,
        message: str,
        suggestion: str,
    ) -> None:
        source_line = (
            self.source_lines[token.line - 1]
            if 0 < token.line <= len(self.source_lines)
            else ""
        )
        raise CompilerError(
            code,
            message,
            SourceLocation(self.filename, token.line, token.column),
            source_line,
            suggestion,
        )


def parse(source: str, filename: str = "<input>") -> Program:
    return Parser(tokenize(source, filename), source, filename).parse()
