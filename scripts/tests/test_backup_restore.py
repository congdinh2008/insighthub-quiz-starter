"""Backup/restore table selection is checked without Docker or a database."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backup_restore_check import TABLES, resolve_tables


class BackupTableSelectionTests(unittest.TestCase):
    def test_default_is_exactly_the_starter_tables(self):
        self.assertEqual(resolve_tables(environ={}), TABLES)
        self.assertEqual(len(TABLES), 8)

    def test_cli_extra_tables_are_appended_once_in_order(self):
        tables = resolve_tables(' users, notebooks,users,,documents ', environ={})
        self.assertEqual(tables, TABLES + ('users', 'notebooks'))

    def test_environment_extension_point(self):
        tables = resolve_tables(environ={'BACKUP_EXTRA_TABLES': 'notes,app.ai_outputs'})
        self.assertEqual(tables[-2:], ('notes', 'app.ai_outputs'))

    def test_cli_value_overrides_environment(self):
        tables = resolve_tables('quiz_attempts', environ={'BACKUP_EXTRA_TABLES': 'notes'})
        self.assertEqual(tables, TABLES + ('quiz_attempts',))

    def test_unsafe_table_names_are_rejected(self):
        for name in ['users;drop table documents', 'Users', '"users"', 'a b', '1users', 'x.y.z']:
            with self.subTest(name=name), self.assertRaises(SystemExit):
                resolve_tables(name, environ={})


if __name__ == '__main__':
    unittest.main()
