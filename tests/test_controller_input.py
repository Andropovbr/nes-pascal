from pathlib import Path
import unittest

from nes_pascal.ast import (
    Assignment,
    ControllerQuery,
    ControllerQueryKind,
    ResolvedAssignment,
    ResolvedControllerQuery,
)
from nes_pascal.backend_ca65 import generate
from nes_pascal.diagnostics import CompilerError
from nes_pascal.memory_layout import build_memory_layout
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


ROOT = Path(__file__).resolve().parents[1]


def controller_program(body: str, variables: str = "Result: boolean;") -> str:
    return f"""program ControllerTest;
var
    {variables}
begin
    {body}
    nes.set_background_color($21);
    nes.run;
end.
"""


def analyze_source(source: str, filename: str = "controller_test.nsp"):
    return analyze(parse(source, filename), source, filename)


class ControllerParserTests(unittest.TestCase):
    def test_parses_all_three_controller_queries_as_boolean_expressions(self) -> None:
        source = controller_program(
            "Result := nes.controller_down($01, nes.button_a);\n"
            "    Result := nes.controller_pressed($02, nes.button_start);\n"
            "    Result := nes.controller_released($01, nes.button_b);"
        )

        program = parse(source)
        queries = []
        for statement in program.statements[:3]:
            self.assertIsInstance(statement, Assignment)
            assert isinstance(statement, Assignment)
            self.assertIsInstance(statement.value, ControllerQuery)
            assert isinstance(statement.value, ControllerQuery)
            queries.append(statement.value.kind)

        self.assertEqual(
            queries,
            [
                ControllerQueryKind.DOWN,
                ControllerQueryKind.PRESSED,
                ControllerQueryKind.RELEASED,
            ],
        )

    def test_parses_qualified_button_constants(self) -> None:
        source = controller_program(
            "Result := nes.controller_down($01, nes.button_right);"
        )
        statement = parse(source).statements[0]
        assert isinstance(statement, Assignment)
        query = statement.value
        assert isinstance(query, ControllerQuery)
        self.assertEqual(query.arguments[1].name, "nes.button_right")


class ControllerSemanticTests(unittest.TestCase):
    def test_resolves_standard_button_masks_and_both_controllers(self) -> None:
        buttons = (
            ("a", 0x01),
            ("b", 0x02),
            ("select", 0x04),
            ("start", 0x08),
            ("up", 0x10),
            ("down", 0x20),
            ("left", 0x40),
            ("right", 0x80),
        )
        statements = []
        for index, (name, _) in enumerate(buttons):
            controller = 1 if index % 2 == 0 else 2
            statements.append(
                f"Result := nes.controller_down(${controller:02X}, "
                f"nes.button_{name});"
            )
        resolved = analyze_source(controller_program("\n    ".join(statements)))
        queries = []
        for statement in resolved.statements[: len(buttons)]:
            assert isinstance(statement, ResolvedAssignment)
            assert isinstance(statement.value, ResolvedControllerQuery)
            queries.append(statement.value)

        self.assertEqual(
            [(item.controller_index, item.button_mask) for item in queries],
            [
                (1 if index % 2 == 0 else 2, mask)
                for index, (_, mask) in enumerate(buttons)
            ],
        )

    def test_accepts_declared_compile_time_controller_constant(self) -> None:
        source = """program ConstantController;
const
    Player: byte = $02;
var
    Result: boolean;
begin
    Result := nes.controller_down(Player, nes.button_a);
    nes.set_background_color($21);
    nes.run;
end.
"""
        resolved = analyze_source(source)
        statement = resolved.statements[0]
        assert isinstance(statement, ResolvedAssignment)
        assert isinstance(statement.value, ResolvedControllerQuery)
        self.assertEqual(statement.value.controller_index, 2)

    def test_rejects_zero_three_and_dynamic_indexes(self) -> None:
        cases = {
            "$00": "E3026",
            "$03": "E3026",
            "Controller": "E3027",
        }
        for argument, code in cases.items():
            with self.subTest(argument=argument):
                source = controller_program(
                    f"Controller := $01;\n"
                    f"    Result := nes.controller_down({argument}, nes.button_a);",
                    "Controller: byte;\n    Result: boolean;",
                )
                with self.assertRaises(CompilerError) as context:
                    analyze_source(source)
                self.assertEqual(context.exception.code, code)

    def test_rejects_invalid_button_count_and_types_with_stable_diagnostics(self) -> None:
        fixtures = {
            "invalid_controller_index.nsp": "E3026",
            "dynamic_controller_index.nsp": "E3027",
            "invalid_controller_button.nsp": "E3028",
            "controller_argument_count.nsp": "E3029",
            "sprite_zero_argument_count.nsp": "E3030",
            "controller_argument_type.nsp": "E4006",
        }
        directory = ROOT / "tests" / "fixtures" / "diagnostics"
        for filename, code in fixtures.items():
            with self.subTest(filename=filename):
                path = directory / filename
                source = path.read_text(encoding="utf-8")
                with self.assertRaises(CompilerError) as context:
                    analyze_source(source, str(path))
                self.assertEqual(context.exception.code, code)

    def test_rejects_controller_query_transitively_from_vblank(self) -> None:
        source = """program VBlankController;
var
    Result: boolean;
procedure Helper;
begin
    Result := nes.controller_down($01, nes.button_a);
end;
procedure VBlank;
begin
    Helper;
end;
begin
    Result := false;
    nes.set_background_color($21);
    nes.on_vblank(VBlank);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E3023")
        self.assertIn("controller polling runs outside NMI", str(context.exception))


class ControllerMemoryAndBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = ROOT / "examples" / "controller_input.nsp"
        cls.source = path.read_text(encoding="utf-8")
        cls.resolved = analyze_source(cls.source, str(path))
        cls.layout = build_memory_layout(cls.resolved)
        cls.assembly = generate(cls.resolved, cls.layout)

    def test_runtime_controller_state_has_stable_zero_page_addresses(self) -> None:
        addresses = {
            symbol.assembly_symbol: symbol.address
            for symbol in self.layout.runtime_symbols
        }
        self.assertEqual(addresses["runtime_controller_1_current"], 0x0003)
        self.assertEqual(addresses["runtime_controller_1_previous"], 0x0004)
        self.assertEqual(addresses["runtime_controller_2_current"], 0x0005)
        self.assertEqual(addresses["runtime_controller_2_previous"], 0x0006)
        self.assertEqual(addresses["runtime_controller_polled_frame"], 0x0007)
        self.assertEqual(addresses["runtime_controller_poll_valid"], 0x0008)

    def test_serial_reader_uses_standard_parallel_bit_order(self) -> None:
        routine = self.assembly.split("runtime_read_controller_ports:", 1)[1].split(
            "; Source: procedure declarations", 1
        )[0]
        self.assertIn("lda #$01\n    sta $4016", routine)
        self.assertIn("lda #$00\n    sta $4016", routine)
        self.assertIn("ldx #$08", routine)
        self.assertIn("lda $4016", routine)
        self.assertIn("ror runtime_controller_1_current", routine)
        self.assertIn("lda $4017", routine)
        self.assertIn("ror runtime_controller_2_current", routine)
        self.assertEqual(routine.count("bne @read_controller_bits"), 1)

    def test_polling_copies_previous_state_once_and_guards_by_frame(self) -> None:
        routine = self.assembly.split("runtime_update_controllers:", 1)[1].split(
            "runtime_read_controller_ports:", 1
        )[0]
        self.assertIn("cmp runtime_controller_polled_frame", routine)
        self.assertIn("lda runtime_controller_poll_valid", routine)
        self.assertIn("beq @controllers_need_poll", routine)
        self.assertIn("sta runtime_controller_poll_valid", routine)
        self.assertIn("beq @controllers_already_current", routine)
        self.assertIn("sta runtime_controller_polled_frame", routine)
        self.assertIn(
            "lda runtime_controller_1_current\n"
            "    sta runtime_controller_1_previous",
            routine,
        )
        self.assertIn(
            "lda runtime_controller_2_current\n"
            "    sta runtime_controller_2_previous",
            routine,
        )
        self.assertEqual(routine.count("jsr runtime_read_controller_ports"), 1)

    def test_first_frame_zero_poll_is_not_confused_with_cleared_ram(self) -> None:
        routine = self.assembly.split("runtime_update_controllers:", 1)[1].split(
            "runtime_read_controller_ports:", 1
        )[0]
        valid_check = routine.index("lda runtime_controller_poll_valid")
        frame_compare = routine.index("cmp runtime_controller_polled_frame")
        valid_publish = routine.index("sta runtime_controller_poll_valid")
        self.assertLess(valid_check, frame_compare)
        self.assertLess(frame_compare, valid_publish)

    def test_callback_loop_polls_outside_nmi_before_update(self) -> None:
        nmi = self.assembly.split("NMI:", 1)[1].split("IRQ:", 1)[0]
        loop = self.assembly.split("@runtime_update_loop:", 1)[1].split(
            "runtime_update_controllers:", 1
        )[0]
        self.assertNotIn("runtime_update_controllers", nmi)
        self.assertNotIn("$4016", nmi)
        self.assertNotIn("$4017", nmi)
        self.assertLess(
            loop.index("jsr runtime_update_controllers"),
            loop.index("jsr procedure_Update"),
        )
        self.assertIn(
            "lda runtime_last_processed_frame\n"
            "    jsr runtime_update_controllers",
            loop,
        )
        self.assertEqual(loop.count("jsr runtime_update_controllers"), 1)

    def test_wait_frame_uses_the_same_idempotent_polling_abstraction(self) -> None:
        source = """program WaitController;
var
    Result: boolean;
begin
    Result := false;
    nes.set_background_color($21);
    nes.run;
    while true do
    begin
        nes.wait_frame;
        Result := nes.controller_pressed($01, nes.button_a);
    end;
end.
"""
        assembly = generate(analyze_source(source))
        wait = assembly.split("; Source: nes.wait_frame", 1)[1].split(
            "; Source: Result := value", 1
        )[0]
        self.assertIn("cmp runtime_frame_counter", wait)
        self.assertIn(
            "lda runtime_frame_counter ; accepted frame for polling\n"
            "    jsr runtime_update_controllers",
            wait,
        )
        self.assertEqual(wait.count("jsr runtime_update_controllers"), 1)

    def test_queries_are_canonical_booleans_and_do_not_mutate_state(self) -> None:
        for name in ("down", "pressed", "released"):
            self.assertIn(f"; nes.controller_{name}", self.assembly)
        query_area = self.assembly.split("; Procedure: Update", 1)[1]
        self.assertIn("lda #$00              ; false", query_area)
        self.assertIn("lda #$01              ; true", query_area)
        self.assertNotIn("sta runtime_controller_1_current", query_area)
        self.assertNotIn("sta runtime_controller_1_previous", query_area)

    def test_fixed_sprite_zero_support_commits_before_oam_dma(self) -> None:
        nmi = self.assembly.split("NMI:", 1)[1].split("IRQ:", 1)[0]
        self.assertIn("lda runtime_sprite_zero_ready", nmi)
        self.assertLess(
            nmi.index("sta runtime_oam_shadow + 3"),
            nmi.index("sta $4014"),
        )
        self.assertIn("sta runtime_sprite_zero_ready", self.assembly)
        self.assertIn("ora #$1E", self.assembly)
        self.assertIn("sta runtime_ppumask_shadow", self.assembly)
        self.assertIn("tile 1 plane 0", self.assembly)
        self.assertIn("tile 2 plane 1", self.assembly)

    def test_controller_assembly_is_deterministic(self) -> None:
        self.assertEqual(
            generate(self.resolved, self.layout),
            generate(self.resolved, self.layout),
        )

    def test_controller_example_matches_golden_assembly(self) -> None:
        expected = (
            ROOT / "tests" / "golden" / "controller_input.asm"
        ).read_text(encoding="utf-8")
        self.assertEqual(self.assembly, expected)


if __name__ == "__main__":
    unittest.main()
