import unittest

from nes_pascal.diagnostics import CompilerError
from nes_pascal.lexer import TokenKind, tokenize


MINIMAL = """program Minimal;
const
    BackgroundColor: nes_color = $21;
begin
    nes.set_background_color(BackgroundColor);
    nes.run;
end.
"""


class LexerTests(unittest.TestCase):
    def test_tokenizes_minimal_program(self) -> None:
        tokens = tokenize(MINIMAL, "minimal.nsp")
        self.assertEqual(
            [token.kind for token in tokens],
            [
                TokenKind.PROGRAM,
                TokenKind.IDENTIFIER,
                TokenKind.SEMICOLON,
                TokenKind.CONST,
                TokenKind.IDENTIFIER,
                TokenKind.COLON,
                TokenKind.IDENTIFIER,
                TokenKind.EQUAL,
                TokenKind.HEX_LITERAL,
                TokenKind.SEMICOLON,
                TokenKind.BEGIN,
                TokenKind.IDENTIFIER,
                TokenKind.DOT,
                TokenKind.IDENTIFIER,
                TokenKind.LEFT_PAREN,
                TokenKind.IDENTIFIER,
                TokenKind.RIGHT_PAREN,
                TokenKind.SEMICOLON,
                TokenKind.IDENTIFIER,
                TokenKind.DOT,
                TokenKind.IDENTIFIER,
                TokenKind.SEMICOLON,
                TokenKind.END,
                TokenKind.DOT,
                TokenKind.EOF,
            ],
        )
        hexadecimal = tokens[8]
        self.assertEqual(hexadecimal.text, "$21")
        self.assertEqual(hexadecimal.value, 0x21)
        self.assertEqual((hexadecimal.line, hexadecimal.column), (3, 34))

    def test_keywords_are_case_insensitive_and_spelling_is_preserved(self) -> None:
        tokens = tokenize("PrOgRaM Demo; BeGiN EnD.")
        self.assertEqual(tokens[0].kind, TokenKind.PROGRAM)
        self.assertEqual(tokens[0].text, "PrOgRaM")
        self.assertEqual(tokens[3].kind, TokenKind.BEGIN)
        self.assertEqual(tokens[4].kind, TokenKind.END)

    def test_rejects_invalid_character_with_location(self) -> None:
        with self.assertRaises(CompilerError) as context:
            tokenize("program Demo; @", "broken.nsp")
        self.assertEqual(context.exception.code, "E1000")
        self.assertEqual(context.exception.location.column, 15)
        self.assertIn("Unexpected character", str(context.exception))

    def test_tokenizes_variable_declarations_assignments_and_booleans(self) -> None:
        tokens = tokenize(
            "var Counter: byte; Enabled: boolean; begin "
            "Counter := $01; Enabled := true; end."
        )
        self.assertIn(TokenKind.VAR, [token.kind for token in tokens])
        self.assertEqual(
            [token.kind for token in tokens].count(TokenKind.ASSIGN),
            2,
        )
        self.assertIn(TokenKind.TRUE, [token.kind for token in tokens])

    def test_tokenizes_arithmetic_operators(self) -> None:
        tokens = tokenize("begin Counter := -$01 + +$02 - $03; end.")
        kinds = [token.kind for token in tokens]
        self.assertEqual(kinds.count(TokenKind.PLUS), 2)
        self.assertEqual(kinds.count(TokenKind.MINUS), 2)


if __name__ == "__main__":
    unittest.main()
