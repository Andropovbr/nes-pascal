from collections import Counter
from pathlib import Path
import shutil
import unittest

from nes_pascal.ast import BuiltInType, ImmediateValue, ResolvedBuiltinCall
from nes_pascal.backend_ca65 import generate
from nes_pascal.builtins import (
    BackendEmitter,
    BuiltinId,
    RuntimeFeature,
    SemanticHook,
    builtin_by_id,
)
from nes_pascal.diagnostics import CompilerError, DiagnosticCode
from nes_pascal.memory_layout import (
    build_memory_layout,
    collect_runtime_features,
    detect_random_runtime_features,
)
from nes_pascal.parser import parse
from nes_pascal.random_runtime import (
    LFSR16_PERIOD,
    LFSR16_XOR_MASK,
    ZERO_SEED_STATE,
    automatic_seed_state,
    lfsr16_step,
    random_byte_from_state,
    reduce_accepted_byte,
    rejection_cutoff,
    seed_to_state,
)
from nes_pascal.semantic import analyze
from tools.measure_benchmarks import BENCHMARKS, measure_benchmark


ROOT = Path(__file__).resolve().parents[1]


def program_with(body: str, declarations: str = "") -> str:
    return f"""program RandomTest;
{declarations}
begin
    {body}
    nes.set_background_color($0F);
    nes.run;
end.
"""


def resolve(source: str):
    return analyze(parse(source, "random_test.nsp"), source, "random_test.nsp")


class RandomAlgorithmTests(unittest.TestCase):
    def test_frozen_seed_expansion_and_known_output_vector(self) -> None:
        self.assertEqual(LFSR16_XOR_MASK, 0xB400)
        self.assertEqual(seed_to_state(0), ZERO_SEED_STATE)
        self.assertEqual(seed_to_state(0x2A), 0x2A2A)
        state = seed_to_state(0x2A)
        outputs = []
        for _ in range(16):
            state, output = random_byte_from_state(state)
            outputs.append(output)
        self.assertEqual(
            outputs,
            [
                0x15, 0x8A, 0x45, 0xA2, 0xD1, 0xE8, 0x74, 0xBA,
                0x5D, 0x2E, 0x97, 0x4B, 0xA5, 0xD2, 0x69, 0x34,
            ],
        )

    def test_lfsr_visits_every_nonzero_state_once(self) -> None:
        initial = ZERO_SEED_STATE
        state = initial
        seen: set[int] = set()
        for _ in range(LFSR16_PERIOD):
            self.assertNotEqual(state, 0)
            self.assertNotIn(state, seen)
            seen.add(state)
            state = lfsr16_step(state)
        self.assertEqual(state, initial)
        self.assertEqual(len(seen), LFSR16_PERIOD)

    def test_automatic_timing_and_controller_mix_is_deterministic_but_variable(self) -> None:
        early = automatic_seed_state(1, 0, 0)
        delayed_start = automatic_seed_state(7, 0x08, 0)
        self.assertNotEqual(early, delayed_start)
        self.assertNotEqual(early, 0)
        self.assertNotEqual(delayed_start, 0)
        self.assertEqual(automatic_seed_state(7, 0x08, 0), delayed_start)

    def test_rejection_mapping_is_uniform_for_representative_spans(self) -> None:
        for span in (3, 5, 6, 7, 10, 100, 255):
            with self.subTest(span=span):
                mapped = [reduce_accepted_byte(value, span) for value in range(256)]
                accepted = [value for value in mapped if value is not None]
                counts = Counter(accepted)
                self.assertEqual(len(counts), span)
                self.assertEqual(len(set(counts.values())), 1)
                self.assertEqual(mapped[: rejection_cutoff(span)], [None] * rejection_cutoff(span))

    def test_full_byte_and_power_of_two_spans_accept_every_source(self) -> None:
        for span in (1, 2, 4, 8, 16, 32, 64, 128, 256):
            with self.subTest(span=span):
                self.assertEqual(rejection_cutoff(span), 0)
                self.assertTrue(
                    all(reduce_accepted_byte(value, span) is not None for value in range(256))
                )

    def test_inclusive_range_boundaries_cover_full_byte_arithmetic(self) -> None:
        for minimum, maximum in (
            (0, 0),
            (0, 1),
            (0, 255),
            (1, 255),
            (10, 20),
            (250, 255),
        ):
            with self.subTest(minimum=minimum, maximum=maximum):
                span = maximum - minimum + 1
                results = [
                    minimum + reduced
                    for source in range(256)
                    if (reduced := reduce_accepted_byte(source, span)) is not None
                ]
                self.assertTrue(results)
                self.assertGreaterEqual(min(results), minimum)
                self.assertLessEqual(max(results), maximum)
                counts = Counter(results)
                self.assertEqual(set(counts), set(range(minimum, maximum + 1)))
                self.assertEqual(len(set(counts.values())), 1)


class RandomBuiltinTests(unittest.TestCase):
    def test_rng_builtins_are_declarative_and_strongly_typed(self) -> None:
        expected = {
            BuiltinId.SEED_RANDOM: (
                BackendEmitter.SEED_RANDOM,
                SemanticHook.DEFAULT,
                (RuntimeFeature.RANDOM,),
            ),
            BuiltinId.RANDOM_BYTE: (
                BackendEmitter.RANDOM_BYTE,
                SemanticHook.DEFAULT,
                (RuntimeFeature.RANDOM,),
            ),
            BuiltinId.RANDOM_RANGE: (
                BackendEmitter.RANDOM_RANGE,
                SemanticHook.RANDOM_RANGE,
                (RuntimeFeature.RANDOM, RuntimeFeature.RANDOM_RANGE),
            ),
        }
        for builtin_id, (emitter, hook, features) in expected.items():
            descriptor = builtin_by_id(builtin_id)
            self.assertIs(descriptor.emitter, emitter)
            self.assertIs(descriptor.semantic_hook, hook)
            self.assertEqual(descriptor.runtime_features, features)
            self.assertTrue(descriptor.side_effecting)

        source = program_with(
            "nes.seed_random($2A); Value := nes.random_range($00, $FF);",
            "var Value: byte;",
        )
        resolved = resolve(source)
        seed = resolved.statements[0]
        call = resolved.statements[1].value
        self.assertIsInstance(seed, ResolvedBuiltinCall)
        self.assertIsInstance(call, ResolvedBuiltinCall)
        self.assertEqual(call.builtin, BuiltinId.RANDOM_RANGE)
        self.assertEqual(builtin_by_id(call.builtin).return_type, BuiltInType.BYTE)
        self.assertTrue(all(isinstance(arg, ImmediateValue) for arg in call.arguments))

    def test_invalid_constant_range_has_a_precise_diagnostic(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "diagnostics" / "invalid_random_range.nsp"
        source = fixture.read_text(encoding="utf-8")
        with self.assertRaises(CompilerError) as raised:
            analyze(parse(source, str(fixture)), source, str(fixture))
        self.assertEqual(raised.exception.code, DiagnosticCode.INVALID_RANDOM_RANGE.value)
        self.assertIn("minimum greater", raised.exception.message)

    def test_boolean_arguments_and_wrong_arity_use_normal_builtin_errors(self) -> None:
        cases = (
            ("Value := nes.random_range(true, $10);", "E4004"),
            ("Value := nes.random_byte($01);", "E3058"),
            ("nes.seed_random();", "E3058"),
        )
        for body, code in cases:
            with self.subTest(body=body):
                source = program_with(body, "var Value: byte;")
                with self.assertRaises(CompilerError) as raised:
                    resolve(source)
                self.assertEqual(raised.exception.code, code)

    def test_random_queries_are_rejected_from_vblank_paths(self) -> None:
        source = """program VBlankRandom;
var Value: byte;
procedure DuringVBlank;
begin
    Value := nes.random_byte();
end;
begin
    nes.on_vblank(DuringVBlank);
    nes.set_background_color($0F);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as raised:
            resolve(source)
        self.assertEqual(raised.exception.code, DiagnosticCode.VBLANK_UNSAFE_OPERATION.value)
        self.assertIn("nes.random_byte", raised.exception.message)
        self.assertIn("shared mutable state", raised.exception.suggestion or "")


class RandomMemoryAndBackendTests(unittest.TestCase):
    def test_no_rng_program_has_zero_rng_code_and_ram(self) -> None:
        resolved = resolve(program_with(""))
        layout = build_memory_layout(resolved)
        assembly = generate(resolved, layout)
        self.assertFalse(detect_random_runtime_features(resolved).enabled)
        self.assertFalse(any("random" in symbol.assembly_symbol for symbol in layout.runtime_symbols))
        self.assertNotIn("runtime_random_", assembly)

    def test_random_byte_uses_two_regular_state_bytes_and_range_adds_two_scratch_bytes(self) -> None:
        byte_program = resolve(
            program_with("Value := nes.random_byte();", "var Value: byte;")
        )
        byte_layout = build_memory_layout(byte_program)
        byte_symbols = [s for s in byte_layout.runtime_symbols if "random" in s.assembly_symbol]
        self.assertEqual([s.assembly_symbol for s in byte_symbols], [
            "runtime_random_state_low", "runtime_random_state_high"
        ])
        self.assertTrue(all(s.address >= 0x0100 for s in byte_symbols))

        range_program = resolve(
            program_with("Value := nes.random_range($00, $06);", "var Value: byte;")
        )
        range_layout = build_memory_layout(range_program)
        range_symbols = [s for s in range_layout.runtime_symbols if "random" in s.assembly_symbol]
        self.assertEqual(sum(s.size for s in range_symbols), 4)
        self.assertIn(RuntimeFeature.RANDOM_RANGE, collect_runtime_features(range_program))

    def test_generated_runtime_freezes_step_seed_auto_mix_and_unbiased_reduction(self) -> None:
        source = program_with(
            "nes.seed_random($2A); Value := nes.random_range($0A, $14);",
            "var Value: byte;",
        )
        resolved = resolve(source)
        assembly = generate(resolved, build_memory_layout(resolved))
        expected_fragments = (
            ROOT / "tests" / "golden" / "random_numbers.asm"
        ).read_text(encoding="utf-8").split("\n---\n")
        for fragment in expected_fragments:
            self.assertIn(fragment.strip(), assembly)
        self.assertIn("jsr runtime_random_range", assembly)

    def test_controller_timing_is_mixed_only_when_controller_queries_are_already_linked(self) -> None:
        without = resolve(program_with("Value := nes.random_byte();", "var Value: byte;"))
        with_controller = resolve(
            program_with(
                "Pressed := nes.controller_down($01, nes.button_a); Value := nes.random_byte();",
                "var Value: byte; Pressed: boolean;",
            )
        )
        without_assembly = generate(without, build_memory_layout(without))
        with_assembly = generate(with_controller, build_memory_layout(with_controller))
        random_without = without_assembly.split("runtime_random_byte:", 1)[1].split("rts", 1)[0]
        random_with = with_assembly.split("runtime_random_byte:", 1)[1].split("rts", 1)[0]
        self.assertNotIn("runtime_controller_1_current", random_without)
        self.assertIn("runtime_controller_1_current", random_with)


class RandomBenchmarkTests(unittest.TestCase):
    @unittest.skipUnless(
        shutil.which("ca65") is not None and shutil.which("ld65") is not None,
        "random-number benchmark measurement requires ca65 and ld65",
    )
    def test_random_numbers_benchmark_metrics_are_stable(self) -> None:
        specification = next(item for item in BENCHMARKS if item.name == "random_numbers")
        metrics = measure_benchmark(specification)
        self.assertEqual(metrics.prg_code_bytes, 417)
        self.assertEqual(metrics.prg_total_used_bytes, 423)
        self.assertEqual(metrics.pattern_stats.total_instructions, 193)
        self.assertEqual(metrics.estimated_static_base_cycles, 659)
        self.assertEqual(metrics.memory.zp_benchmark_allocated_or_reserved_bytes, 9)
        self.assertEqual(metrics.memory.regular_runtime_user_allocated_bytes, 11)
        self.assertEqual(metrics.max_live_temporaries, 0)
        self.assertEqual(metrics.runtime_features, ("RANDOM", "RANDOM_RANGE"))
        self.assertEqual(metrics.ram_symbol_breakdown["runtime_random_state_low"], 1)
        self.assertEqual(metrics.ram_symbol_breakdown["runtime_random_state_high"], 1)
        self.assertEqual(metrics.ram_symbol_breakdown["runtime_random_span"], 1)
        self.assertEqual(metrics.ram_symbol_breakdown["runtime_random_cutoff"], 1)


if __name__ == "__main__":
    unittest.main()
