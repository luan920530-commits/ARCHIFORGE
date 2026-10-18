import csv
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from af_quantities_io import (
    collect_quantities,
    format_number,
    summarize,
    write_csv,
)


class QuantityCollectionTests(unittest.TestCase):
    def test_default_pointer_groups_are_not_counted(self):
        cube = SimpleNamespace(
            name="Cube",
            archiforge_wall=SimpleNamespace(
                is_af_wall=True,
                object_name="",
                height=2.7,
                width=0.2,
                parts=[SimpleNamespace(length=2.0, enabled=True)],
            ),
        )

        self.assertEqual(collect_quantities([cube]), [])

    def test_wall_uses_enabled_segment_lengths_not_thickness(self):
        wall_props = SimpleNamespace(
            is_af_wall=True,
            object_name="AF_Wall",
            height=3.0,
            width=0.2,
            parts=[
                SimpleNamespace(length=3.0, enabled=True),
                SimpleNamespace(length=1.25, enabled=True),
                SimpleNamespace(length=8.0, enabled=False),
            ],
        )
        wall = SimpleNamespace(name="AF_Wall", archiforge_wall=wall_props)

        rows = collect_quantities([wall])

        self.assertEqual([row[4] for row in rows], ["m2", "m3"])
        self.assertAlmostEqual(rows[0][3], 12.75)
        self.assertAlmostEqual(rows[1][3], 2.55)
        self.assertIn("L=4,25", rows[0][5])

    def test_custom_slab_uses_polygon_area_and_subtracts_holes(self):
        slab_props = SimpleNamespace(
            is_af_slab=True,
            object_name="AF_Slab",
            slab_type="CUSTOM",
            slab_system="MACIZA",
            width=99.0,
            depth=99.0,
            thickness=0.2,
            overhang=0.0,
            vertices=[
                SimpleNamespace(x=0.0, y=0.0),
                SimpleNamespace(x=4.0, y=0.0),
                SimpleNamespace(x=4.0, y=3.0),
                SimpleNamespace(x=0.0, y=3.0),
            ],
            holes=[SimpleNamespace(width=1.0, depth=2.0, enabled=True)],
        )
        slab = SimpleNamespace(name="AF_Slab", archiforge_slab=slab_props)

        rows = collect_quantities([slab])

        self.assertEqual([(row[3], row[4]) for row in rows], [
            (10.0, "m2"),
            (2.0, "m3"),
        ])
        self.assertIn("4,00x3,00", rows[0][5])

    def test_plural_stair_property_is_included(self):
        stair_props = SimpleNamespace(
            is_af_stair=True,
            object_name="AF_Stairs",
            item_type="RAMP",
            width=1.2,
            total_rise=0.8,
            n_risers=5,
            ramp_slope=0.08,
        )
        obj = SimpleNamespace(name="AF_Stairs", archiforge_stairs=stair_props)

        rows = collect_quantities([obj])

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][:5], ("Escaleras", "RAMP", "AF_Stairs", 1, "und"))
        self.assertIn("pendiente=8,00%", rows[0][5])


class CsvExportTests(unittest.TestCase):
    def test_number_format_is_spanish_and_rejects_non_finite_values(self):
        self.assertEqual(format_number(1234.567), "1234,57")
        with self.assertRaises(ValueError):
            format_number(float("inf"))

    def test_summaries_are_grouped_and_stable(self):
        rows = [
            ("Muros", "Muro", "A", 2.5, "m2", ""),
            ("Muros", "Muro", "B", 3.0, "m2", ""),
            ("Losas", "MACIZA", "C", 1, "und", ""),
        ]

        self.assertEqual(summarize(rows), [
            (("Losas", "MACIZA", "und"), 1.0),
            (("Muros", "Muro", "m2"), 5.5),
        ])

    def test_csv_quotes_fields_and_neutralizes_spreadsheet_formulas(self):
        row_name = ' =HYPERLINK("https://example.test";"click")\nSala'
        rows = [("Muros", "Muro", row_name, 2.5, "m2", "L=2,00; H=2,50 m")]

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cantidades.csv"
            self.assertEqual(write_csv(path, rows), 1)
            raw = path.read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
            content = raw.decode("utf-8-sig")
            parsed = list(csv.reader(io.StringIO(content, newline=""), delimiter=";"))

        self.assertEqual(parsed[0], ["Categoría", "Tipo", "Objeto", "Cantidad", "Unidad", "Medidas"])
        self.assertEqual(parsed[1][2], "'" + row_name)
        self.assertEqual(parsed[1][3], "2,50")
        self.assertEqual(parsed[1][5], "L=2,00; H=2,50 m")
        self.assertEqual(parsed[2], [])
        self.assertEqual(parsed[3], ["RESUMEN"])
        self.assertEqual(parsed[-1], ["Muros", "Muro", "m2", "2,50"])

    def test_invalid_negative_quantities_do_not_create_a_partial_file(self):
        rows = [("Muros", "Muro", "A", -1, "m2", "")]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "invalid.csv"
            with self.assertRaises(ValueError):
                write_csv(path, rows)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
