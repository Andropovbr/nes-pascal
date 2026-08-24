from pathlib import Path
import shutil
import unittest

from nes_pascal.ast import EnumType
from nes_pascal.backend_ca65 import generate
from nes_pascal.memory_layout import build_memory_layout, generate_memory_map
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze
from tools.measure_benchmarks import BENCHMARKS, measure_benchmark


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "game_state.nsp"


def resolve_example():
    source = EXAMPLE.read_text(encoding="utf-8")
    return source, analyze(parse(source, str(EXAMPLE)), source, str(EXAMPLE))


class GameStatePatternTests(unittest.TestCase):
    def test_sample_uses_one_byte_nominal_enum_without_hidden_state_manager(self) -> None:
        source, program = resolve_example()
        state = next(variable for variable in program.variables if variable.name == "State")
        layout = build_memory_layout(program, source=source, filename=str(EXAMPLE))
        state_symbol = next(
            symbol for symbol in layout.user_symbols if symbol.source_name == "State"
        )

        self.assertIsInstance(state.type, EnumType)
        self.assertEqual(state.type.name, "GameState")
        self.assertEqual(state.type.members, ("Title", "Playing", "Paused", "GameOver"))
        self.assertEqual(state_symbol.size, 1)
        self.assertNotIn("state_manager", generate_memory_map(layout).lower())
        self.assertNotIn("state_registry", generate_memory_map(layout).lower())

    def test_dispatcher_matches_direct_comparison_golden(self) -> None:
        source, program = resolve_example()
        assembly = generate(program, build_memory_layout(program))
        actual = assembly.split("procedure_Update:\n", 1)[1].split(
            "\n\n; Source: function declarations", 1
        )[0]
        actual = "procedure_Update:\n" + actual.rstrip() + "\n"
        expected = (ROOT / "tests" / "golden" / "game_state_dispatch.asm").read_text(
            encoding="utf-8"
        )

        self.assertEqual(actual, expected)
        for value in range(4):
            self.assertIn(f"cmp #${value:02X}", actual)
        self.assertNotIn("runtime_state", assembly)
        self.assertNotIn("state_dispatch", assembly)

    def test_transition_helpers_use_ordinary_calls_and_assign_state_last(self) -> None:
        source, program = resolve_example()
        assembly = generate(program, build_memory_layout(program))
        start_game = assembly.split("procedure_StartGame:\n", 1)[1].split(
            "\n\n; Procedure: PauseGame", 1
        )[0]
        reset = assembly.split("procedure_ResetGameplay:\n", 1)[1].split(
            "\n\n; Procedure: EnterTitle", 1
        )[0]

        self.assertIn("jsr procedure_ResetGameplay", start_game)
        self.assertIn("jsr runtime_seed_random", reset)
        self.assertIn("jsr runtime_random_byte", reset)
        self.assertLess(start_game.index("jsr procedure_ResetGameplay"), start_game.index("sta variable_State"))
        self.assertTrue(start_game.rstrip().endswith("sta variable_State\n    rts"))
        self.assertNotIn("jsr RESET", assembly)

    @unittest.skipUnless(
        shutil.which("ca65") is not None and shutil.which("ld65") is not None,
        "game-state benchmark measurement requires ca65 and ld65",
    )
    def test_game_state_benchmark_metrics_are_stable(self) -> None:
        specification = next(item for item in BENCHMARKS if item.name == "game_state")
        metrics = measure_benchmark(specification)

        self.assertEqual(metrics.prg_code_bytes, 1268)
        self.assertEqual(metrics.prg_total_used_bytes, 1274)
        self.assertEqual(metrics.pattern_stats.total_instructions, 567)
        self.assertEqual(metrics.estimated_static_base_cycles, 1876)
        self.assertEqual(metrics.max_expression_tree_depth, 1)
        self.assertEqual(metrics.max_live_temporaries, 0)
        self.assertEqual(metrics.max_call_depth, 4)
        self.assertEqual(metrics.max_call_stack_bytes, 8)
        self.assertEqual(metrics.memory.zp_promoted_user_bytes, 4)
        self.assertEqual(metrics.memory.regular_user_bytes, 4)
        self.assertEqual(metrics.memory.regular_compiler_bytes, 1)
        self.assertEqual(
            metrics.runtime_features,
            ("CONTROLLER_QUERY", "PALETTE_QUEUE", "RANDOM", "SPRITE_API", "SPRITE_SET_POSITION"),
        )


if __name__ == "__main__":
    unittest.main()
