from pathlib import Path
import re
import unittest

from nes_pascal.diagnostics import (
    DIAGNOSTIC_CATALOG,
    DiagnosticCategory,
    DiagnosticCode,
)


ROOT = Path(__file__).resolve().parents[1]

CATEGORY_RANGES = {
    DiagnosticCategory.LEXICAL: (1000, 1999),
    DiagnosticCategory.PARSER: (2000, 2999),
    DiagnosticCategory.SEMANTIC: (3000, 3999),
    DiagnosticCategory.TYPE_SYSTEM: (4000, 4999),
    DiagnosticCategory.CODE_GENERATION: (5000, 5999),
    DiagnosticCategory.RUNTIME: (6000, 6999),
}


class DiagnosticCatalogTests(unittest.TestCase):
    def test_every_code_is_unique_and_cataloged_once(self) -> None:
        values = [code.value for code in DiagnosticCode]
        self.assertEqual(len(values), len(set(values)))
        self.assertEqual(set(DiagnosticCode), set(DIAGNOSTIC_CATALOG))

    def test_every_error_uses_its_category_range(self) -> None:
        for code, definition in DIAGNOSTIC_CATALOG.items():
            with self.subTest(code=code.value):
                self.assertRegex(code.value, r"^E\d{4}$")
                number = int(code.value[1:])
                lower, upper = CATEGORY_RANGES[definition.category]
                self.assertGreaterEqual(number, lower)
                self.assertLessEqual(number, upper)

    def test_documentation_index_matches_the_catalog(self) -> None:
        documentation = (ROOT / "docs" / "DIAGNOSTICS.md").read_text(
            encoding="utf-8"
        )
        documented_codes = set(
            re.findall(r"^\| (E\d{4}) \|", documentation, re.MULTILINE)
        )
        self.assertEqual(
            documented_codes,
            {code.value for code in DiagnosticCode},
        )


if __name__ == "__main__":
    unittest.main()
