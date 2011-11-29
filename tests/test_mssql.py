"""Test op functions against MSSQL."""

from tests import op_fixture, capture_context_buffer, no_sql_testing_config, staging_env, three_rev_fixture, clear_staging_env
from alembic import op, command
from sqlalchemy import Integer, Column, ForeignKey, \
            UniqueConstraint, Table, MetaData, String
from sqlalchemy.sql import table
from unittest import TestCase


class FullEnvironmentTests(TestCase):
    @classmethod
    def setup_class(cls):
        env = staging_env()
        cls.cfg = cfg = no_sql_testing_config("mssql")

        cls.a, cls.b, cls.c = \
            three_rev_fixture(cfg)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_begin_comit(self):
        with capture_context_buffer(transactional_ddl=True) as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert "BEGIN TRANSACTION" in buf.getvalue()
        assert "COMMIT" in buf.getvalue()

class OpTest(TestCase):
    def test_add_column(self):
        context = op_fixture('mssql')
        op.add_column('t1', Column('c1', Integer, nullable=False))
        context.assert_("ALTER TABLE t1 ADD c1 INTEGER NOT NULL")


    def test_add_column_with_default(self):
        context = op_fixture("mssql")
        op.add_column('t1', Column('c1', Integer, nullable=False, server_default="12"))
        context.assert_("ALTER TABLE t1 ADD c1 INTEGER NOT NULL DEFAULT '12'")

    def test_alter_column_rename_mssql(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", name="x")
        context.assert_(
            "EXEC sp_rename 't.c', 'x', 'COLUMN'"
        )

    def test_drop_column_w_default(self):
        context = op_fixture('mssql')
        op.drop_column('t1', 'c1', mssql_drop_default=True)
        context.assert_contains("exec('alter table t1 drop constraint ' + @const_name)")
        context.assert_contains("ALTER TABLE t1 DROP COLUMN c1")


    def test_drop_column_w_check(self):
        context = op_fixture('mssql')
        op.drop_column('t1', 'c1', mssql_drop_check=True)
        context.assert_contains("exec('alter table t1 drop constraint ' + @const_name)")
        context.assert_contains("ALTER TABLE t1 DROP COLUMN c1")

    def test_alter_column_nullable(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", nullable=True)
        context.assert_(
            "ALTER TABLE t ALTER COLUMN c NULL"
        )

    def test_alter_column_not_nullable(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", nullable=False)
        context.assert_(
            "ALTER TABLE t ALTER COLUMN c SET NOT NULL"
        )

    # TODO: when we add schema support
    #def test_alter_column_rename_mssql_schema(self):
    #    context = op_fixture('mssql')
    #    op.alter_column("t", "c", name="x", schema="y")
    #    context.assert_(
    #        "EXEC sp_rename 'y.t.c', 'x', 'COLUMN'"
    #    )
