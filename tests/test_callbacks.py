from pathlib import Path
import unittest

from nes_pascal.ast import (
    CallbackKind,
    CallbackRegistration,
    ResolvedCallbackRegistration,
)
from nes_pascal.backend_ca65 import generate
from nes_pascal.diagnostics import CompilerError
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


ROOT = Path(__file__).resolve().parents[1]


def analyze_source(source: str, filename: str = "callbacks.nsp"):
    return analyze(parse(source, filename), source, filename)


def callback_program(
    procedures: str,
    registrations: str,
    variables: str = "",
    initialization: str = "",
) -> str:
    var_section = f"var\n{variables}\n" if variables else ""
    return f"""program Callbacks;
{var_section}{procedures}
begin
{initialization}    nes.set_background_color($21);
{registrations}    nes.run;
end.
"""


class CallbackParserTests(unittest.TestCase):
    def test_parses_direct_static_callback_registrations(self) -> None:
        source = callback_program(
            """procedure Update;
begin
end;
procedure VBlank;
begin
end;
""",
            "    nes.on_update(Update);\n    nes.on_vblank(VBlank);\n",
        )
        program = parse(source)

        update = program.statements[1]
        vblank = program.statements[2]
        self.assertIsInstance(update, CallbackRegistration)
        self.assertIsInstance(vblank, CallbackRegistration)
        assert isinstance(update, CallbackRegistration)
        assert isinstance(vblank, CallbackRegistration)
        self.assertEqual(update.kind, CallbackKind.UPDATE)
        self.assertEqual(update.procedure_name, "Update")
        self.assertEqual(vblank.kind, CallbackKind.VBLANK)
        self.assertEqual(vblank.procedure_name, "VBlank")

    def test_rejects_non_identifier_callback_argument(self) -> None:
        source = callback_program(
            "",
            "    nes.on_update($01);\n",
        )

        with self.assertRaises(CompilerError) as context:
            parse(source)

        self.assertEqual(context.exception.code, "E2102")
        self.assertIn("direct procedure name", str(context.exception))


class CallbackSemanticTests(unittest.TestCase):
    def test_resolves_one_callback_of_each_kind(self) -> None:
        source = (ROOT / "examples" / "frame_callbacks.nsp").read_text(
            encoding="utf-8"
        )

        resolved = analyze_source(source)
        registrations = [
            statement
            for statement in resolved.statements
            if isinstance(statement, ResolvedCallbackRegistration)
        ]

        self.assertEqual(
            [(item.kind, item.procedure_label) for item in registrations],
            [
                (CallbackKind.UPDATE, "procedure_Update"),
                (CallbackKind.VBLANK, "procedure_VBlank"),
            ],
        )

    def test_update_callback_keeps_ordinary_main_context_features(self) -> None:
        source = callback_program(
            """procedure Helper;
begin
end;
procedure Update;
begin
    while false do
        Helper;
end;
""",
            "    nes.on_update(Update);\n",
        )

        analyze_source(source)

    def test_accepts_transitively_safe_vblank_call_graph(self) -> None:
        source = callback_program(
            """procedure Leaf;
begin
    inc(Counter);
end;
procedure Helper;
begin
    Leaf;
end;
procedure VBlank;
begin
    Helper;
end;
""",
            "    nes.on_vblank(VBlank);\n",
            variables="    Counter: byte;",
            initialization="    Counter := $00;\n",
        )

        analyze_source(source)

    def test_rejects_wait_frame_inside_update_callback(self) -> None:
        source = callback_program(
            """procedure Update;
begin
    nes.wait_frame;
end;
""",
            "    nes.on_update(Update);\n",
        )

        with self.assertRaises(CompilerError) as context:
            analyze_source(source)

        self.assertEqual(context.exception.code, "E3015")
        self.assertIn("nes.wait_frame", str(context.exception))

    def test_rejects_arithmetic_using_shared_temporary_in_vblank(self) -> None:
        source = callback_program(
            """procedure VBlank;
begin
    Counter := Counter + $01;
end;
""",
            "    nes.on_vblank(VBlank);\n",
            variables="    Counter: byte;",
            initialization="    Counter := $00;\n",
        )

        with self.assertRaises(CompilerError) as context:
            analyze_source(source)

        self.assertEqual(context.exception.code, "E3023")
        self.assertIn("shared compiler temporary storage", str(context.exception))

    def test_rejects_transitively_unsafe_vblank_loop(self) -> None:
        source = callback_program(
            """procedure UnsafeHelper;
begin
    repeat
    until true;
end;
procedure VBlank;
begin
    UnsafeHelper;
end;
""",
            "    nes.on_vblank(VBlank);\n",
        )

        with self.assertRaises(CompilerError) as context:
            analyze_source(source)

        self.assertEqual(context.exception.code, "E3023")
        self.assertIn("path through UnsafeHelper", str(context.exception))

    def test_rejects_wait_frame_directly_in_vblank(self) -> None:
        source = callback_program(
            """procedure VBlank;
begin
    nes.wait_frame;
end;
""",
            "    nes.on_vblank(VBlank);\n",
        )

        with self.assertRaises(CompilerError) as context:
            analyze_source(source)

        self.assertEqual(context.exception.code, "E3023")
        self.assertIn("nes.wait_frame", str(context.exception))

    def test_rejects_wait_frame_through_vblank_helper(self) -> None:
        source = callback_program(
            """procedure BlockingHelper;
begin
    nes.wait_frame;
end;
procedure VBlank;
begin
    BlockingHelper;
end;
""",
            "    nes.on_vblank(VBlank);\n",
        )

        with self.assertRaises(CompilerError) as context:
            analyze_source(source)

        self.assertEqual(context.exception.code, "E3023")
        self.assertIn("path through BlockingHelper", str(context.exception))
        self.assertIn("nes.wait_frame", str(context.exception))

    def test_rejects_parameterized_helper_in_vblank_graph(self) -> None:
        source = callback_program(
            """procedure Helper(Value: byte);
begin
end;
procedure VBlank;
begin
    Helper($01);
end;
""",
            "    nes.on_vblank(VBlank);\n",
        )

        with self.assertRaises(CompilerError) as context:
            analyze_source(source)

        self.assertEqual(context.exception.code, "E3024")
        self.assertIn("parameterized procedure Helper", str(context.exception))

    def test_recursion_reachable_from_vblank_keeps_recursion_diagnostic(self) -> None:
        source = callback_program(
            """procedure VBlank;
begin
    VBlank;
end;
""",
            "    nes.on_vblank(VBlank);\n",
        )

        with self.assertRaises(CompilerError) as context:
            analyze_source(source)

        self.assertEqual(context.exception.code, "E3014")

    def test_requires_vblank_inputs_to_be_initialized_before_run(self) -> None:
        source = callback_program(
            """procedure VBlank;
begin
    inc(Counter);
end;
""",
            "    nes.on_vblank(VBlank);\n",
            variables="    Counter: byte;",
        )

        with self.assertRaises(CompilerError) as context:
            analyze_source(source)

        self.assertEqual(context.exception.code, "E3008")
        self.assertIn("before nes.run enables NMI", str(context.exception))

    def test_each_callback_diagnostic_has_a_focused_fixture(self) -> None:
        fixtures = {
            "unknown_callback_procedure.nsp": "E3018",
            "invalid_callback_signature.nsp": "E3019",
            "duplicate_update_callback.nsp": "E3020",
            "duplicate_vblank_callback.nsp": "E3021",
            "invalid_callback_context.nsp": "E3022",
            "vblank_unsafe_operation.nsp": "E3023",
            "invalid_callback_call_graph.nsp": "E3024",
            "conflicting_callback_registration.nsp": "E3025",
        }
        fixture_directory = ROOT / "tests" / "fixtures" / "diagnostics"

        for filename, code in fixtures.items():
            with self.subTest(filename=filename):
                path = fixture_directory / filename
                source = path.read_text(encoding="utf-8")
                with self.assertRaises(CompilerError) as context:
                    analyze_source(source, str(path))
                self.assertEqual(context.exception.code, code)

    def test_rejects_registration_after_runtime_start(self) -> None:
        source = callback_program(
            """procedure Update;
begin
end;
""",
            "",
        ).replace(
            "    nes.run;",
            "    nes.run;\n    nes.on_update(Update);",
        )

        with self.assertRaises(CompilerError) as context:
            analyze_source(source)

        self.assertEqual(context.exception.code, "E3022")

    def test_rejects_registration_inside_procedure(self) -> None:
        source = callback_program(
            """procedure Update;
begin
end;
procedure Configure;
begin
    nes.on_update(Update);
end;
""",
            "",
        )

        with self.assertRaises(CompilerError) as context:
            analyze_source(source)

        self.assertEqual(context.exception.code, "E3022")
        self.assertIn("inside a procedure", str(context.exception))

    def test_accepts_callback_registrations_in_either_pre_run_order(self) -> None:
        source = callback_program(
            """procedure Update;
begin
end;
procedure VBlank;
begin
end;
""",
            "    nes.on_vblank(VBlank);\n    nes.on_update(Update);\n",
        )

        resolved = analyze_source(source)
        registrations = [
            statement.kind
            for statement in resolved.statements
            if isinstance(statement, ResolvedCallbackRegistration)
        ]
        self.assertEqual(
            registrations,
            [CallbackKind.VBLANK, CallbackKind.UPDATE],
        )


class CallbackBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = ROOT / "examples" / "frame_callbacks.nsp"
        cls.source = path.read_text(encoding="utf-8")
        cls.assembly = generate(analyze_source(cls.source, str(path)))

    def test_update_callback_waits_once_per_observed_frame_outside_nmi(self) -> None:
        nmi = self.assembly.split("NMI:", 1)[1].split("IRQ:", 1)[0]
        runtime_loop = self.assembly.split("@runtime_update_loop:", 1)[1].split(
            "; Source: procedure declarations", 1
        )[0]

        self.assertNotIn("jsr procedure_Update", nmi)
        self.assertIn("lda runtime_frame_counter", runtime_loop)
        self.assertIn("sta runtime_last_processed_frame", runtime_loop)
        self.assertIn("cmp runtime_last_processed_frame", runtime_loop)
        self.assertIn("beq @runtime_update_loop", runtime_loop)
        self.assertEqual(runtime_loop.count("jsr procedure_Update"), 1)
        self.assertIn("jmp @runtime_update_loop", runtime_loop)

    def test_update_only_program_keeps_nmi_free_of_update_logic(self) -> None:
        source = callback_program(
            """procedure Update;
begin
end;
""",
            "    nes.on_update(Update);\n",
        )
        assembly = generate(analyze_source(source))
        nmi = assembly.split("NMI:", 1)[1].split("IRQ:", 1)[0]

        self.assertNotIn("jsr procedure_Update", nmi)
        self.assertIn("jsr procedure_Update", assembly)
        self.assertIn("@runtime_update_loop:", assembly)

    def test_vblank_only_program_keeps_stable_main_idle_loop(self) -> None:
        source = callback_program(
            """procedure VBlank;
begin
end;
""",
            "    nes.on_vblank(VBlank);\n",
        )
        assembly = generate(analyze_source(source))
        nmi = assembly.split("NMI:", 1)[1].split("IRQ:", 1)[0]

        self.assertIn("jsr procedure_VBlank", nmi)
        self.assertIn("@runtime_idle_loop:", assembly)
        self.assertNotIn("@runtime_update_loop:", assembly)

    def test_program_without_callbacks_preserves_stable_idle_loop(self) -> None:
        source = callback_program("", "")
        assembly = generate(analyze_source(source))
        nmi = assembly.split("NMI:", 1)[1].split("IRQ:", 1)[0]

        self.assertIn("@runtime_idle_loop:", assembly)
        self.assertNotIn("@runtime_update_loop:", assembly)
        self.assertNotIn("jsr procedure_", nmi)

    def test_both_callbacks_use_their_distinct_execution_contexts(self) -> None:
        nmi = self.assembly.split("NMI:", 1)[1].split("IRQ:", 1)[0]
        runtime_loop = self.assembly.split("@runtime_update_loop:", 1)[1].split(
            "; Source: procedure declarations", 1
        )[0]

        self.assertIn("jsr procedure_VBlank", nmi)
        self.assertNotIn("jsr procedure_Update", nmi)
        self.assertIn("jsr procedure_Update", runtime_loop)
        self.assertNotIn("jsr procedure_VBlank", runtime_loop)

    def test_update_loop_preserves_pending_frame_across_slow_callback(self) -> None:
        runtime_loop = self.assembly.split("@runtime_update_loop:", 1)[1].split(
            "; Source: procedure declarations", 1
        )[0]
        callback_index = runtime_loop.index("jsr procedure_Update")
        back_edge_index = runtime_loop.index(
            "jmp @runtime_update_loop",
            callback_index,
        )

        self.assertNotIn(
            "sta runtime_last_processed_frame",
            runtime_loop[callback_index:back_edge_index],
        )
        self.assertIn(
            "cmp runtime_last_processed_frame",
            runtime_loop[:callback_index],
        )
        self.assertLess(
            runtime_loop.index("sta runtime_last_processed_frame"),
            callback_index,
        )
        self.assertNotIn("cmp runtime_frame_counter", runtime_loop)
        self.assertNotIn("lda runtime_frame_ready", runtime_loop)
        self.assertNotIn("cmp runtime_frame_ready", runtime_loop)

    def test_vblank_callback_runs_after_bookkeeping_before_restore(self) -> None:
        nmi = self.assembly.split("NMI:", 1)[1].split("IRQ:", 1)[0]

        self.assertLess(nmi.index("inc runtime_frame_counter"), nmi.index("jsr procedure_VBlank"))
        self.assertLess(nmi.index("jsr procedure_VBlank"), nmi.index("pla"))
        self.assertEqual(nmi.count("jsr procedure_VBlank"), 1)

    def test_nmi_preserves_registers_and_owns_rti_while_procedures_use_rts(self) -> None:
        nmi = self.assembly.split("NMI:", 1)[1].split("IRQ:", 1)[0]
        vblank = self.assembly.split("procedure_VBlank:", 1)[1]

        self.assertEqual(nmi.count("    pha"), 3)
        self.assertEqual(nmi.count("    pla"), 3)
        self.assertIn("    rti", nmi)
        self.assertNotIn("    rts", nmi)
        self.assertIn("    rts", vblank)

    def test_vblank_path_does_not_reference_expression_temporaries(self) -> None:
        nmi = self.assembly.split("NMI:", 1)[1].split("IRQ:", 1)[0]
        vblank = self.assembly.split("procedure_VBlank:", 1)[1].split(
            "    rts", 1
        )[0]
        helper = self.assembly.split("procedure_IncrementVBlankFrames:", 1)[
            1
        ].split("    rts", 1)[0]

        self.assertNotIn("expression_temporary", nmi + vblank + helper)
        self.assertIn("runtime_frame_counter: .res 1 ; $0000", self.assembly)
        self.assertIn("runtime_frame_ready: .res 1 ; $0001", self.assembly)
        self.assertIn(
            "runtime_last_processed_frame: .res 1 ; $0002",
            self.assembly,
        )

    def test_main_expression_temporary_exists_but_is_absent_from_nmi_graph(self) -> None:
        source = callback_program(
            """procedure Update;
begin
    UpdateFrames := $01 + (UpdateFrames + $01);
end;
procedure VBlank;
begin
    inc(VBlankFrames);
end;
""",
            "    nes.on_update(Update);\n    nes.on_vblank(VBlank);\n",
            variables="    UpdateFrames: byte;\n    VBlankFrames: byte;",
            initialization=(
                "    UpdateFrames := $00;\n"
                "    VBlankFrames := $00;\n"
            ),
        )
        assembly = generate(analyze_source(source))
        nmi = assembly.split("NMI:", 1)[1].split("IRQ:", 1)[0]
        vblank = assembly.split("procedure_VBlank:", 1)[1].split(
            "    rts", 1
        )[0]

        self.assertIn("expression_temporary_0: .res 1 ; $0010", assembly)
        self.assertNotIn("expression_temporary", nmi + vblank)

    def test_callback_assembly_is_deterministic(self) -> None:
        resolved = analyze_source(self.source)
        self.assertEqual(generate(resolved), generate(resolved))


if __name__ == "__main__":
    unittest.main()
