"""Hand-written recursive-descent parser for the current milestone."""

from .ast import (
    Assignment,
    BackgroundUpdatesOverflowed,
    BinaryExpression,
    BinaryOperator,
    BooleanBinaryExpression,
    BooleanLiteral,
    BooleanNotExpression,
    BooleanOperator,
    BreakStatement,
    BuiltInType,
    CallbackKind,
    CallbackRegistration,
    ClearBackgroundUpdates,
    ClearBackgroundUpdateOverflow,
    ControllerQuery,
    ControllerQueryKind,
    ConstantDeclaration,
    ConstantReference,
    ComparisonExpression,
    ComparisonOperator,
    ContinueStatement,
    DecrementStatement,
    ForDirection,
    ForStatement,
    GetTile,
    HexLiteral,
    IfStatement,
    IncrementStatement,
    LoadBackground,
    PaletteKind,
    Literal,
    Program,
    ProcedureCall,
    ProcedureDeclaration,
    ProcedureParameter,
    RepeatStatement,
    Run,
    SetBackgroundColor,
    SetAttribute,
    SetPalette,
    SetPaletteColor,
    SetSpriteZero,
    SetScroll,
    SetTile,
    SourcePosition,
    SpriteOperation,
    SpriteOperationKind,
    Statement,
    UnaryExpression,
    UnaryOperator,
    ValueExpression,
    VariableDeclaration,
    VariableReference,
    WaitFrame,
    WhileStatement,
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
        self.parameter_names: set[str] = set()

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
        procedures = self._parse_procedures()
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
            tuple(procedures),
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

    def _parse_procedures(self) -> list[ProcedureDeclaration]:
        declarations: list[ProcedureDeclaration] = []
        while self._check(TokenKind.PROCEDURE):
            procedure_token = self._expect(
                TokenKind.PROCEDURE,
                "Expected 'procedure'.",
            )
            name = self._expect(
                TokenKind.IDENTIFIER,
                "Expected a procedure name after 'procedure'.",
            )
            parameters = self._parse_procedure_parameters()
            self._expect(
                TokenKind.SEMICOLON,
                "Expected ';' after the procedure declaration.",
            )
            self._expect(
                TokenKind.BEGIN,
                "Expected 'begin' to start the procedure body.",
            )
            body: list[Statement] = []
            self.parameter_names = {
                parameter.name.lower() for parameter in parameters
            }
            while not self._check(TokenKind.END):
                if self._check(TokenKind.EOF):
                    self._error(
                        self._current(),
                        DiagnosticCode.INVALID_SYNTAX,
                        "Reached the end of the file before the procedure ended.",
                        "Finish the procedure with 'end;'.",
                    )
                body.append(self._parse_statement())
            self.parameter_names = set()
            self._expect(
                TokenKind.END,
                "Expected 'end' after the procedure body.",
            )
            self._expect(
                TokenKind.SEMICOLON,
                "Expected ';' after the procedure declaration.",
            )
            declarations.append(
                ProcedureDeclaration(
                    name.text,
                    tuple(body),
                    SourcePosition(procedure_token.line, procedure_token.column),
                    tuple(parameters),
                )
            )
        return declarations

    def _parse_procedure_parameters(self) -> list[ProcedureParameter]:
        if not self._match(TokenKind.LEFT_PAREN):
            return []
        if self._check(TokenKind.RIGHT_PAREN):
            self._error(
                self._current(),
                DiagnosticCode.INVALID_SYNTAX,
                "A parameter list cannot be empty.",
                "Omit the parentheses for a parameterless procedure.",
            )

        parameters: list[ProcedureParameter] = []
        while True:
            name = self._expect(
                TokenKind.IDENTIFIER,
                "Expected a parameter name.",
            )
            self._expect(TokenKind.COLON, "Expected ':' after the parameter name.")
            type_token = self._current()
            declared_type = self._parse_type()
            parameters.append(
                ProcedureParameter(
                    name.text,
                    declared_type,
                    SourcePosition(name.line, name.column),
                    SourcePosition(type_token.line, type_token.column),
                )
            )
            if not self._match(TokenKind.SEMICOLON):
                break
        self._expect(
            TokenKind.RIGHT_PAREN,
            "Expected ')' after the parameter list.",
        )
        return parameters

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

    def _parse_statement(self, consume_terminator: bool = True) -> Statement:
        if self._check(TokenKind.IF):
            return self._parse_if_statement(consume_terminator)
        if self._check(TokenKind.WHILE):
            return self._parse_while_statement(consume_terminator)
        if self._check(TokenKind.REPEAT):
            return self._parse_repeat_statement(consume_terminator)
        if self._check(TokenKind.FOR):
            return self._parse_for_statement(consume_terminator)
        if self._check(TokenKind.INC):
            return self._parse_update_statement(
                TokenKind.INC,
                consume_terminator,
            )
        if self._check(TokenKind.DEC):
            return self._parse_update_statement(
                TokenKind.DEC,
                consume_terminator,
            )
        if self._check(TokenKind.BREAK):
            return self._parse_loop_control_statement(
                TokenKind.BREAK,
                consume_terminator,
            )
        if self._check(TokenKind.CONTINUE):
            return self._parse_loop_control_statement(
                TokenKind.CONTINUE,
                consume_terminator,
            )
        if self._check(TokenKind.IDENTIFIER) and self._peek_kind() is TokenKind.ASSIGN:
            return self._parse_assignment(consume_terminator)
        if self._check(TokenKind.IDENTIFIER) and self._peek_kind() in (
            TokenKind.LEFT_PAREN,
            TokenKind.SEMICOLON,
        ):
            return self._parse_procedure_call(consume_terminator)

        namespace = self._expect(
            TokenKind.IDENTIFIER,
            "Expected an assignment, update, control-flow statement, "
            "a NES background or palette command, callback registration, "
            "nes.wait_frame, or nes.run.",
        )
        self._expect(TokenKind.DOT, "Expected '.' after 'nes'.")
        command = self._expect(TokenKind.IDENTIFIER, "Expected a command name.")
        qualified_name = f"{namespace.text}.{command.text}"
        normalized = qualified_name.lower()

        if namespace.text.lower() != "nes":
            self._unknown_command(namespace, qualified_name)
        if normalized == "nes.set_background_color":
            return self._parse_background_color(
                SourcePosition(namespace.line, namespace.column),
                consume_terminator,
            )
        if normalized == "nes.set_sprite_zero":
            arguments = self._parse_expression_arguments(normalized)
            if consume_terminator:
                self._expect(
                    TokenKind.SEMICOLON,
                    "Expected ';' after 'nes.set_sprite_zero(...)'.",
                )
            return SetSpriteZero(
                arguments,
                SourcePosition(namespace.line, namespace.column),
            )
        sprite_commands = {
            "nes.sprite_set_x": SpriteOperationKind.SET_X,
            "nes.sprite_set_y": SpriteOperationKind.SET_Y,
            "nes.sprite_set_tile": SpriteOperationKind.SET_TILE,
            "nes.sprite_set_palette": SpriteOperationKind.SET_PALETTE,
            "nes.sprite_set_attributes": SpriteOperationKind.SET_ATTRIBUTES,
            "nes.sprite_hide": SpriteOperationKind.HIDE,
            "nes.sprite_show": SpriteOperationKind.SHOW,
            "nes.sprite_set_flip_horizontal": (
                SpriteOperationKind.SET_FLIP_HORIZONTAL
            ),
            "nes.sprite_set_flip_vertical": SpriteOperationKind.SET_FLIP_VERTICAL,
            "nes.sprite_set_behind_background": (
                SpriteOperationKind.SET_BEHIND_BACKGROUND
            ),
        }
        sprite_kind = sprite_commands.get(normalized)
        if sprite_kind is not None:
            arguments = self._parse_expression_arguments(normalized)
            if consume_terminator:
                self._expect(
                    TokenKind.SEMICOLON,
                    f"Expected ';' after '{normalized}(...)'.",
                )
            return SpriteOperation(
                sprite_kind,
                arguments,
                SourcePosition(namespace.line, namespace.column),
            )
        if normalized == "nes.load_background":
            arguments = self._parse_expression_arguments(normalized)
            if consume_terminator:
                self._expect(
                    TokenKind.SEMICOLON,
                    "Expected ';' after 'nes.load_background()'.",
                )
            return LoadBackground(
                arguments,
                SourcePosition(namespace.line, namespace.column),
            )
        background_update_commands = {
            "nes.set_tile": SetTile,
            "nes.set_attribute": SetAttribute,
            "nes.clear_background_updates": ClearBackgroundUpdates,
            "nes.clear_background_update_overflow": ClearBackgroundUpdateOverflow,
        }
        background_update = background_update_commands.get(normalized)
        if background_update is not None:
            arguments = self._parse_expression_arguments(normalized)
            if consume_terminator:
                self._expect(
                    TokenKind.SEMICOLON,
                    f"Expected ';' after '{normalized}(...)'.",
                )
            return background_update(
                arguments,
                SourcePosition(namespace.line, namespace.column),
            )
        if normalized == "nes.set_scroll":
            arguments = self._parse_expression_arguments(normalized)
            if consume_terminator:
                self._expect(
                    TokenKind.SEMICOLON,
                    "Expected ';' after 'nes.set_scroll(...)'.",
                )
            return SetScroll(
                arguments,
                SourcePosition(namespace.line, namespace.column),
            )
        palette_commands = {
            "nes.set_background_palette": (PaletteKind.BACKGROUND, False),
            "nes.set_sprite_palette": (PaletteKind.SPRITE, False),
            "nes.set_background_palette_color": (PaletteKind.BACKGROUND, True),
            "nes.set_sprite_palette_color": (PaletteKind.SPRITE, True),
        }
        palette_command = palette_commands.get(normalized)
        if palette_command is not None:
            kind, individual = palette_command
            arguments = self._parse_expression_arguments(normalized)
            if consume_terminator:
                self._expect(
                    TokenKind.SEMICOLON,
                    f"Expected ';' after '{normalized}(...)'.",
                )
            position = SourcePosition(namespace.line, namespace.column)
            if individual:
                return SetPaletteColor(kind, arguments, position)
            return SetPalette(kind, arguments, position)
        if normalized == "nes.run":
            if consume_terminator:
                self._expect(TokenKind.SEMICOLON, "Expected ';' after 'nes.run'.")
            return Run(SourcePosition(namespace.line, namespace.column))
        if normalized == "nes.wait_frame":
            if consume_terminator:
                self._expect(
                    TokenKind.SEMICOLON,
                    "Expected ';' after 'nes.wait_frame'.",
                )
            return WaitFrame(SourcePosition(namespace.line, namespace.column))
        if normalized in ("nes.on_update", "nes.on_vblank"):
            kind = (
                CallbackKind.UPDATE
                if normalized == "nes.on_update"
                else CallbackKind.VBLANK
            )
            return self._parse_callback_registration(
                kind,
                SourcePosition(namespace.line, namespace.column),
                consume_terminator,
            )
        self._unknown_command(command, qualified_name)
        raise AssertionError("unreachable")

    def _parse_assignment(self, consume_terminator: bool) -> Assignment:
        target = self._expect(TokenKind.IDENTIFIER, "Expected an assignment target.")
        self._expect(TokenKind.ASSIGN, "Expected ':=' after the assignment target.")
        value = self._parse_expression()
        if consume_terminator:
            self._expect(TokenKind.SEMICOLON, "Expected ';' after the assignment.")
        return Assignment(
            target.text,
            SourcePosition(target.line, target.column),
            value,
        )

    def _parse_procedure_call(
        self,
        consume_terminator: bool,
    ) -> ProcedureCall:
        name = self._expect(
            TokenKind.IDENTIFIER,
            "Expected a procedure name.",
        )
        arguments: list[ValueExpression] = []
        if self._match(TokenKind.LEFT_PAREN):
            if self._check(TokenKind.RIGHT_PAREN):
                self._error(
                    self._current(),
                    DiagnosticCode.INVALID_SYNTAX,
                    "A procedure call argument list cannot be empty.",
                    "Omit the parentheses when calling a parameterless procedure.",
                )
            while True:
                arguments.append(self._parse_expression())
                if not self._match(TokenKind.COMMA):
                    break
            self._expect(
                TokenKind.RIGHT_PAREN,
                "Expected ')' after the procedure arguments.",
            )
        if consume_terminator:
            self._expect(
                TokenKind.SEMICOLON,
                "Expected ';' after the procedure call.",
            )
        return ProcedureCall(
            name.text,
            SourcePosition(name.line, name.column),
            tuple(arguments),
        )

    def _parse_background_color(
        self,
        position: SourcePosition,
        consume_terminator: bool,
    ) -> SetBackgroundColor:
        self._expect(
            TokenKind.LEFT_PAREN,
            "Expected '(' after 'nes.set_background_color'.",
        )
        argument = self._parse_expression()
        self._expect(
            TokenKind.RIGHT_PAREN,
            "Expected ')' after the background color.",
        )
        if consume_terminator:
            self._expect(
                TokenKind.SEMICOLON,
                "Expected ';' after 'nes.set_background_color(...)'.",
            )
        return SetBackgroundColor(argument, position)

    def _parse_callback_registration(
        self,
        kind: CallbackKind,
        position: SourcePosition,
        consume_terminator: bool,
    ) -> CallbackRegistration:
        command = f"nes.on_{kind.value}"
        self._expect(
            TokenKind.LEFT_PAREN,
            f"Expected '(' after '{command}'.",
        )
        procedure = self._expect(
            TokenKind.IDENTIFIER,
            f"Expected a direct procedure name in '{command}'.",
        )
        self._expect(
            TokenKind.RIGHT_PAREN,
            f"Expected ')' after the callback procedure name.",
        )
        if consume_terminator:
            self._expect(
                TokenKind.SEMICOLON,
                f"Expected ';' after '{command}(...)'.",
            )
        return CallbackRegistration(
            kind,
            procedure.text,
            position,
            SourcePosition(procedure.line, procedure.column),
        )

    def _parse_expression_arguments(
        self,
        qualified_name: str,
    ) -> tuple[ValueExpression, ...]:
        self._expect(
            TokenKind.LEFT_PAREN,
            f"Expected '(' after '{qualified_name}'.",
        )
        arguments: list[ValueExpression] = []
        if not self._check(TokenKind.RIGHT_PAREN):
            while True:
                arguments.append(self._parse_expression())
                if not self._match(TokenKind.COMMA):
                    break
        self._expect(
            TokenKind.RIGHT_PAREN,
            f"Expected ')' after '{qualified_name}' arguments.",
        )
        return tuple(arguments)

    def _parse_if_statement(self, consume_terminator: bool) -> IfStatement:
        if_token = self._expect(TokenKind.IF, "Expected 'if'.")
        condition = self._parse_expression()
        self._expect(TokenKind.THEN, "Expected 'then' after the if condition.")
        then_branch = self._parse_conditional_branch()
        else_branch = None
        if self._match(TokenKind.ELSE):
            else_branch = self._parse_conditional_branch()
        if consume_terminator:
            self._expect(
                TokenKind.SEMICOLON,
                "Expected ';' after the if statement.",
            )
        return IfStatement(
            condition,
            then_branch,
            else_branch,
            SourcePosition(if_token.line, if_token.column),
        )

    def _parse_while_statement(
        self,
        consume_terminator: bool,
    ) -> WhileStatement:
        while_token = self._expect(TokenKind.WHILE, "Expected 'while'.")
        condition = self._parse_expression()
        self._expect(TokenKind.DO, "Expected 'do' after the while condition.")
        body = self._parse_conditional_branch()
        if consume_terminator:
            self._expect(
                TokenKind.SEMICOLON,
                "Expected ';' after the while statement.",
            )
        return WhileStatement(
            condition,
            body,
            SourcePosition(while_token.line, while_token.column),
        )

    def _parse_repeat_statement(
        self,
        consume_terminator: bool,
    ) -> RepeatStatement:
        repeat_token = self._expect(TokenKind.REPEAT, "Expected 'repeat'.")
        body: list[Statement] = []
        while not self._check(TokenKind.UNTIL):
            if self._check(TokenKind.EOF):
                self._error(
                    self._current(),
                    DiagnosticCode.INVALID_SYNTAX,
                    "Reached the end of the file before 'until'.",
                    "Finish the repeat loop with 'until condition;'.",
                )
            body.append(self._parse_statement())
        self._expect(TokenKind.UNTIL, "Expected 'until' after the repeat body.")
        condition = self._parse_expression()
        if consume_terminator:
            self._expect(
                TokenKind.SEMICOLON,
                "Expected ';' after the repeat loop condition.",
            )
        return RepeatStatement(
            tuple(body),
            condition,
            SourcePosition(repeat_token.line, repeat_token.column),
        )

    def _parse_loop_control_statement(
        self,
        kind: TokenKind,
        consume_terminator: bool,
    ) -> BreakStatement | ContinueStatement:
        token = self._expect(kind, f"Expected '{kind.name.lower()}'.")
        if consume_terminator:
            self._expect(
                TokenKind.SEMICOLON,
                f"Expected ';' after '{token.text.lower()}'.",
            )
        position = SourcePosition(token.line, token.column)
        if kind is TokenKind.BREAK:
            return BreakStatement(position)
        return ContinueStatement(position)

    def _parse_update_statement(
        self,
        kind: TokenKind,
        consume_terminator: bool,
    ) -> IncrementStatement | DecrementStatement:
        command = self._expect(kind, f"Expected '{kind.name.lower()}'.")
        self._expect(
            TokenKind.LEFT_PAREN,
            f"Expected '(' after '{command.text.lower()}'.",
        )
        target = self._expect(
            TokenKind.IDENTIFIER,
            f"Expected a variable name in '{command.text.lower()}'.",
        )
        amount = None
        if self._match(TokenKind.COMMA):
            amount = self._parse_expression()
        self._expect(
            TokenKind.RIGHT_PAREN,
            f"Expected ')' after '{command.text.lower()}'.",
        )
        if consume_terminator:
            self._expect(
                TokenKind.SEMICOLON,
                f"Expected ';' after '{command.text.lower()}(...)'.",
            )
        position = SourcePosition(command.line, command.column)
        target_position = SourcePosition(target.line, target.column)
        if kind is TokenKind.INC:
            return IncrementStatement(
                target.text,
                target_position,
                amount,
                position,
            )
        return DecrementStatement(
            target.text,
            target_position,
            amount,
            position,
        )

    def _parse_for_statement(
        self,
        consume_terminator: bool,
    ) -> ForStatement:
        for_token = self._expect(TokenKind.FOR, "Expected 'for'.")
        target = self._expect(
            TokenKind.IDENTIFIER,
            "Expected a control variable after 'for'.",
        )
        self._expect(
            TokenKind.ASSIGN,
            "Expected ':=' after the for control variable.",
        )
        initial = self._parse_expression()
        direction_token = self._current()
        if self._match(TokenKind.TO):
            direction = ForDirection.TO
        elif self._match(TokenKind.DOWNTO):
            direction = ForDirection.DOWNTO
        else:
            self._error(
                direction_token,
                DiagnosticCode.INVALID_SYNTAX,
                "Expected 'to' or 'downto' after the initial value.",
                "Use 'for Counter := $00 to $10 do' or use 'downto'.",
            )
        final = self._parse_expression()
        self._expect(TokenKind.DO, "Expected 'do' after the final value.")
        body = self._parse_conditional_branch()
        if consume_terminator:
            self._expect(
                TokenKind.SEMICOLON,
                "Expected ';' after the for statement.",
            )
        return ForStatement(
            target.text,
            SourcePosition(target.line, target.column),
            initial,
            final,
            direction,
            body,
            SourcePosition(for_token.line, for_token.column),
        )

    def _parse_conditional_branch(self) -> tuple[Statement, ...]:
        if not self._match(TokenKind.BEGIN):
            return (self._parse_statement(consume_terminator=False),)

        statements: list[Statement] = []
        while not self._check(TokenKind.END):
            if self._check(TokenKind.EOF):
                self._error(
                    self._current(),
                    DiagnosticCode.INVALID_SYNTAX,
                    "Reached the end of the file before the branch block ended.",
                    "Finish the branch block with 'end'.",
                )
            statements.append(self._parse_statement())
        self._expect(TokenKind.END, "Expected 'end' after the branch block.")
        return tuple(statements)

    def _parse_expression(self) -> ValueExpression:
        return self._parse_or_expression()

    def _parse_or_expression(self) -> ValueExpression:
        expression = self._parse_and_expression()
        while self._check(TokenKind.OR):
            operator_token = self._current()
            self.position += 1
            expression = BooleanBinaryExpression(
                expression,
                BooleanOperator.OR,
                self._parse_and_expression(),
                SourcePosition(operator_token.line, operator_token.column),
            )
        return expression

    def _parse_and_expression(self) -> ValueExpression:
        expression = self._parse_comparison_expression()
        while self._check(TokenKind.AND):
            operator_token = self._current()
            self.position += 1
            expression = BooleanBinaryExpression(
                expression,
                BooleanOperator.AND,
                self._parse_comparison_expression(),
                SourcePosition(operator_token.line, operator_token.column),
            )
        return expression

    def _parse_comparison_expression(self) -> ValueExpression:
        expression = self._parse_arithmetic_expression()
        comparison_operators = {
            TokenKind.EQUAL: ComparisonOperator.EQUAL,
            TokenKind.NOT_EQUAL: ComparisonOperator.NOT_EQUAL,
            TokenKind.LESS: ComparisonOperator.LESS,
            TokenKind.GREATER: ComparisonOperator.GREATER,
            TokenKind.LESS_EQUAL: ComparisonOperator.LESS_EQUAL,
            TokenKind.GREATER_EQUAL: ComparisonOperator.GREATER_EQUAL,
        }
        token = self._current()
        operator = comparison_operators.get(token.kind)
        if operator is None:
            return expression
        self.position += 1
        return ComparisonExpression(
            expression,
            operator,
            self._parse_arithmetic_expression(),
            SourcePosition(token.line, token.column),
        )

    def _parse_arithmetic_expression(self) -> ValueExpression:
        expression = self._parse_unary_expression()
        while self._current().kind in (TokenKind.PLUS, TokenKind.MINUS):
            operator_token = self._current()
            self.position += 1
            operator = (
                BinaryOperator.ADD
                if operator_token.kind is TokenKind.PLUS
                else BinaryOperator.SUBTRACT
            )
            right = self._parse_unary_expression()
            expression = BinaryExpression(
                expression,
                operator,
                right,
                SourcePosition(operator_token.line, operator_token.column),
            )
        return expression

    def _parse_unary_expression(self) -> ValueExpression:
        token = self._current()
        if token.kind is TokenKind.NOT:
            self.position += 1
            return BooleanNotExpression(
                self._parse_unary_expression(),
                SourcePosition(token.line, token.column),
            )
        if token.kind in (TokenKind.PLUS, TokenKind.MINUS):
            self.position += 1
            operator = (
                UnaryOperator.PLUS
                if token.kind is TokenKind.PLUS
                else UnaryOperator.NEGATE
            )
            return UnaryExpression(
                operator,
                self._parse_unary_expression(),
                SourcePosition(token.line, token.column),
            )
        return self._parse_primary_expression()

    def _parse_primary_expression(self) -> ValueExpression:
        token = self._current()
        if token.kind in (
            TokenKind.HEX_LITERAL,
            TokenKind.TRUE,
            TokenKind.FALSE,
        ):
            return self._parse_literal("value")
        if self._match(TokenKind.IDENTIFIER):
            position = SourcePosition(token.line, token.column)
            if self._match(TokenKind.DOT):
                member = self._expect(
                    TokenKind.IDENTIFIER,
                    "Expected a built-in name after '.'.",
                )
                qualified_name = f"{token.text}.{member.text}"
                normalized = qualified_name.lower()
                query_kinds = {
                    "nes.controller_down": ControllerQueryKind.DOWN,
                    "nes.controller_pressed": ControllerQueryKind.PRESSED,
                    "nes.controller_released": ControllerQueryKind.RELEASED,
                }
                query_kind = query_kinds.get(normalized)
                if query_kind is not None:
                    return ControllerQuery(
                        query_kind,
                        self._parse_expression_arguments(normalized),
                        position,
                    )
                if normalized == "nes.get_tile":
                    return GetTile(
                        self._parse_expression_arguments(normalized),
                        position,
                    )
                if normalized == "nes.background_updates_overflowed":
                    return BackgroundUpdatesOverflowed(
                        self._parse_expression_arguments(normalized),
                        position,
                    )
                return ConstantReference(qualified_name, position)
            if token.text.lower() in (
                self.variable_names | self.parameter_names
            ):
                return VariableReference(token.text, position)
            return ConstantReference(token.text, position)
        if self._match(TokenKind.LEFT_PAREN):
            expression = self._parse_expression()
            self._expect(
                TokenKind.RIGHT_PAREN,
                "Expected ')' after the expression.",
            )
            return expression
        self._error(
            token,
            DiagnosticCode.INVALID_SYNTAX,
            "Expected a literal, identifier, or parenthesized expression.",
            "Use a hexadecimal value, boolean value, constant, variable, "
            "or an expression in parentheses.",
        )
        raise AssertionError("unreachable")

    def _unknown_command(self, token: Token, name: str) -> None:
        self._error(
            token,
            DiagnosticCode.UNKNOWN_COMMAND,
            f"Unknown command: {name}.",
            "Use an assignment, procedure call, inc/dec update, "
            "control-flow statement, "
            "nes.load_background();, a background tile/attribute update, "
            "a nes.set_* palette call, "
            "nes.set_scroll(...);, "
            "a nes.sprite_* call, "
            "nes.set_sprite_zero(...);, "
            "nes.on_update(Procedure);, nes.on_vblank(Procedure);, "
            "nes.wait_frame;, or nes.run;.",
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
