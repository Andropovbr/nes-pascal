import hashlib
import unittest
from pathlib import Path

from nes_pascal.assets import load_chr_rom
from nes_pascal.metasprite_assets import load_metasprite_assets
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze
from tools.measure_benchmarks import BENCHMARKS, measure_benchmark


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "nes_survivor" / "nes_survivor_vertical_slice.nsp"
ASSETS = EXAMPLE.parent / "assets"
METADATA = tuple(
    ASSETS / name for name in ("player.json", "sword.json", "bat.json", "gem.json")
)


class NesSurvivorVerticalSliceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = EXAMPLE.read_text(encoding="utf-8")
        cls.chr_rom = load_chr_rom(ASSETS / "game.chr", EXAMPLE, cls.source)
        cls.assets = load_metasprite_assets(
            METADATA,
            EXAMPLE,
            cls.source,
            cls.chr_rom,
        )
        cls.program = analyze(
            parse(cls.source, str(EXAMPLE)),
            cls.source,
            str(EXAMPLE),
            metasprite_assets=cls.assets,
        )
        specification = next(
            item for item in BENCHMARKS if item.name == "nes_survivor_vertical_slice"
        )
        cls.metrics = measure_benchmark(specification)

    def test_frozen_chr_matches_the_reference_rom_composition(self) -> None:
        self.assertEqual(
            hashlib.sha256(self.chr_rom).hexdigest(),
            "285c4879a83641e45debc34e6c5ea889a8552e423cf0e24df88efcad7c7185e2",
        )
        self.assertEqual(len(self.chr_rom), 8192)
        self.assertEqual(
            [
                index
                for index in range(256)
                if any(self.chr_rom[index * 16 : (index + 1) * 16])
            ],
            list(range(21)),
        )
        self.assertEqual(
            [
                index
                for index in range(256, 512)
                if any(self.chr_rom[index * 16 : (index + 1) * 16])
            ],
            [321, 322, 323, 324, 325, 327, 328, 329, 333, 334, 335, 336,
             338, 339, 340, 341, 342, 345],
        )

    def test_adapted_metadata_preserves_reference_tiles_and_oam_budget(self) -> None:
        by_name = {asset.name: asset for asset in self.assets}
        self.assertEqual(set(by_name), {"player", "sword", "bat", "gem"})
        self.assertEqual(
            [len(frame.components) for frame in by_name["player"].frames],
            [7, 7, 7],
        )
        self.assertEqual(
            [len(frame.components) for frame in by_name["bat"].frames],
            [2, 2],
        )
        self.assertEqual(len(by_name["sword"].frames[0].components), 2)
        self.assertEqual(len(by_name["gem"].frames[0].components), 1)

        component_tiles = {
            asset.name: sorted(
                {
                    component.tile
                    for frame in asset.frames
                    for component in frame.components
                }
            )
            for asset in self.assets
        }
        self.assertEqual(component_tiles["player"], list(range(8)))
        self.assertEqual(component_tiles["sword"], [8, 9])
        self.assertEqual(component_tiles["bat"], [10, 11, 12, 13])
        self.assertEqual(component_tiles["gem"], [20])

        # 7 player + 2 sword + 12 two-tile Bats + 8 one-tile gems.
        self.assertEqual(7 + 2 + 12 * 2 + 8, 41)

    def test_static_arena_uses_a_blank_pattern_table_zero_tile(self) -> None:
        nametable = (ASSETS / "arena_blank.nam").read_bytes()
        self.assertEqual(len(nametable), 1024)
        self.assertEqual(
            hashlib.sha256(nametable).hexdigest(),
            "30a0c265f473bc034386a7d6c3f42b81ada1da6bccb03393602c2c240947896a",
        )
        self.assertEqual(nametable[:960], bytes((0x15,)) * 960)
        self.assertEqual(nametable[960:], bytes(64))
        self.assertEqual(self.chr_rom[0x15 * 16 : 0x16 * 16], bytes(16))

    def test_workload_exercises_the_expected_composed_runtime(self) -> None:
        self.assertIn("DamageFlashFrames: byte = $0A;", self.source)
        self.assertIn("nes.load_background();", self.source)
        self.assertEqual(
            self.metrics.runtime_features,
            (
                "COLLISION_RECTS",
                "CONTROLLER_QUERY",
                "METASPRITE_ANIMATION",
                "METASPRITE_API",
                "PALETTE_QUEUE",
                "RANDOM",
                "RANDOM_RANGE",
            ),
        )
        self.assertEqual(self.metrics.prg_code_bytes, 6991)
        self.assertEqual(self.metrics.prg_total_used_bytes, 6997)
        self.assertEqual(self.metrics.pattern_stats.total_instructions, 2678)
        self.assertEqual(self.metrics.estimated_static_base_cycles, 8175)
        self.assertEqual(self.metrics.max_expression_tree_depth, 2)
        self.assertEqual(self.metrics.max_live_temporaries, 0)

        memory = self.metrics.memory
        self.assertEqual(memory.zp_benchmark_allocated_or_reserved_bytes, 54)
        self.assertEqual(memory.zp_allocator_visible_free_bytes, 105)
        self.assertEqual(memory.regular_runtime_user_allocated_bytes, 359)
        self.assertEqual(memory.oam_shadow_allocated_bytes, 256)
        self.assertEqual(memory.regular_allocator_visible_free_bytes, 918)
        self.assertEqual(memory.total_allocator_visible_free_bytes, 1023)
        self.assertEqual(
            memory.total_committed_or_reserved_address_space_bytes
            + memory.total_allocator_visible_free_bytes,
            2048,
        )

    def test_structural_golden_snapshot(self) -> None:
        procedure_names = ",".join(item.name for item in self.program.procedures)
        function_names = ",".join(item.name for item in self.program.functions)
        snapshot = "\n".join(
            (
                f"program={self.program.name}",
                "reference_sha=af433de5ad5705d756e9f4cb9ff800fc91b6261c",
                "metasprite_instances=22",
                "reserved_oam_slots=41",
                f"procedures={procedure_names}",
                f"functions={function_names}",
                f"runtime_features={','.join(self.metrics.runtime_features)}",
                f"prg_code_bytes={self.metrics.prg_code_bytes}",
                f"instructions={self.metrics.pattern_stats.total_instructions}",
                "",
            )
        )
        expected = (
            ROOT / "tests" / "golden" / "nes_survivor_vertical_slice.structure"
        ).read_text(encoding="utf-8")
        self.assertEqual(snapshot, expected)


if __name__ == "__main__":
    unittest.main()
