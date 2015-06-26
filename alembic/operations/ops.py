from .. import util
from ..util import sqla_compat
from . import schemaobj
from sqlalchemy.types import NULLTYPE
from sqlalchemy import schema as sa_schema

to_impl = util.Dispatcher()


class MigrateOperation(object):
    """base class for migration command and organization objects."""


class AddConstraintOp(MigrateOperation):
    @classmethod
    def from_constraint(cls, constraint):
        funcs = {
            "unique_constraint": CreateUniqueConstraintOp.from_constraint,
            "foreign_key_constraint": CreateForeignKeyOp.from_constraint,
            "primary_key_constraint": CreatePrimaryKeyOp.from_constraint,
            "check_constraint": CreateCheckConstraintOp.from_constraint,
            "column_check_constraint": CreateCheckConstraintOp.from_constraint,
        }
        return funcs[constraint.__visit_name__](constraint)


class DropConstraintOp(MigrateOperation):
    def __init__(self, constraint_name, table_name, type_=None, schema=None):
        self.constraint_name = constraint_name
        self.table_name = table_name
        self.constraint_type = type_
        self.schema = schema

    @classmethod
    def from_constraint(cls, constraint):
        types = {
            "unique_constraint": "unique",
            "foreign_key_constraint": "foreignkey",
            "primary_key_constraint": "primary",
            "check_constraint": "check",
            "column_check_constraint": "check",
        }

        constraint_table = sqla_compat._table_for_constraint(constraint)
        return DropConstraintOp(
            constraint.name,
            constraint_table.name,
            schema=constraint_table.schema,
            type_=types[constraint.__visit_name__]
        )


class CreatePrimaryKeyOp(AddConstraintOp):
    def __init__(
            self, constraint_name, table_name, columns, schema=None, **kw):
        self.constraint_name = constraint_name
        self.table_name = table_name
        self.columns = columns
        self.schema = schema
        self.kw = kw

    @classmethod
    def from_constraint(cls, constraint):
        constraint_table = sqla_compat._table_for_constraint(constraint)

        return CreatePrimaryKeyOp(
            constraint.name,
            constraint_table.name,
            schema=constraint_table.schema,
            *constraint.columns
        )

    def to_constraint(self, migration_context=None):
        schema_obj = schemaobj.SchemaObjects(migration_context)
        return schema_obj.primary_key_constraint(
            self.constraint_name, self.table_name,
            self.columns, schema=self.schema)


class CreateUniqueConstraintOp(AddConstraintOp):
    def __init__(
            self, constraint_name, table_name, columns, schema=None, **kw):
        self.constraint_name = constraint_name
        self.table_name = table_name
        self.columns = columns
        self.schema = schema
        self.kw = kw

    @classmethod
    def from_constraint(cls, constraint):
        constraint_table = sqla_compat._table_for_constraint(constraint)

        kw = {}
        if constraint.deferrable:
            kw['deferrable'] = constraint.deferrable
        if constraint.initially:
            kw['initially'] = constraint.initially

        return CreateUniqueConstraintOp(
            constraint.name,
            constraint_table.name,
            [c.name for c in constraint.columns],
            schema=constraint_table.schema,
            **kw
        )

    def to_constraint(self, migration_context=None):
        schema_obj = schemaobj.SchemaObjects(migration_context)
        return schema_obj.unique_constraint(
            self.constraint_name, self.table_name, self.columns,
            schema=self.schema, **self.kw)


class CreateForeignKeyOp(AddConstraintOp):
    def __init__(
            self, constraint_name, source_table, referent_table, local_cols,
            remote_cols, **kw):
        self.constraint_name = constraint_name
        self.source_table = source_table
        self.referent_table = referent_table
        self.local_cols = local_cols
        self.remote_cols = remote_cols
        self.kw = kw

    @classmethod
    def from_constraint(cls, constraint):
        kw = {}
        if constraint.onupdate:
            kw['onupdate'] = constraint.onupdate
        if constraint.ondelete:
            kw['ondelete'] = constraint.ondelete
        if constraint.initially:
            kw['initially'] = constraint.initially
        if constraint.deferrable:
            kw['deferrable'] = constraint.deferrable
        if constraint.use_alter:
            kw['use_alter'] = constraint.use_alter

        source_schema, source_table, \
            source_columns, target_schema, \
            target_table, target_columns = sqla_compat._fk_spec(constraint)

        kw['source_schema'] = source_schema
        kw['referent_schema'] = target_schema

        return CreateForeignKeyOp(
            constraint.name,
            source_table,
            target_table,
            source_columns,
            target_columns,
            **kw
        )

    def to_constraint(self, migration_context=None):
        schema_obj = schemaobj.SchemaObjects(migration_context)
        return schema_obj.foreign_key_constraint(
            self.constraint_name,
            self.source_table, self.referent_table,
            self.local_cols, self.remote_cols,
            **self.kw)


class CreateCheckConstraintOp(AddConstraintOp):
    def __init__(
            self, constraint_name, table_name, condition, schema=None, **kw):
        self.constraint_name = constraint_name
        self.table_name = table_name
        self.condition = condition
        self.schema = schema
        self.kw = kw

    @classmethod
    def from_constraint(cls, constraint):
        constraint_table = sqla_compat._table_for_constraint(constraint)

        return CreateCheckConstraintOp(
            constraint.name,
            constraint_table.name,
            constraint.condition,
            schema=constraint_table.schema
        )

    def to_constraint(self, migration_context=None):
        schema_obj = schemaobj.SchemaObjects(migration_context)
        return schema_obj.check_constraint(
            self.constraint_name, self.table_name,
            self.condition, schema=self.schema, **self.kw)


class CreateIndexOp(MigrateOperation):
    def __init__(
            self, index_name, table_name, columns, schema=None,
            unique=False, quote=None, _orig_index=None, **kw):
        self.index_name = index_name
        self.table_name = table_name
        self.columns = columns
        self.schema = schema
        self.unique = unique
        self.quote = quote
        self.kw = kw
        self._orig_index = _orig_index

    @classmethod
    def from_index(cls, index):
        return CreateIndexOp(
            index.name,
            index.table.name,
            sqla_compat._get_index_expressions(index),
            schema=index.table.schema,
            unique=index.unique,
            quote=index.name.quote,
            _orig_index=index,
            **index.dialect_kwargs
        )

    def to_index(self, migration_context=None):
        if self._orig_index:
            return self._orig_index
        schema_obj = schemaobj.SchemaObjects(migration_context)
        return schema_obj.index(
            self.index_name, self.table_name, self.columns, schema=self.schema,
            unique=self.unique, quote=self.quote, **self.kw)


class DropIndexOp(MigrateOperation):
    def __init__(self, index_name, table_name=None, schema=None):
        self.index_name = index_name
        self.table_name = table_name
        self.schema = schema

    @classmethod
    def from_index(cls, index):
        return DropIndexOp(
            index.name,
            index.table.name,
            schema=index.table.schema,
        )

    def to_index(self, migration_context=None):
        schema_obj = schemaobj.SchemaObjects(migration_context)

        # need a dummy column name here since SQLAlchemy
        # 0.7.6 and further raises on Index with no columns
        return schema_obj.index(
            self.index_name, self.table_name, ['x'], schema=self.schema)


class CreateTableOp(MigrateOperation):
    def __init__(
            self, table_name, columns, schema=None, _orig_table=None, **kw):
        self.table_name = table_name
        self.columns = columns
        self.schema = schema
        self.kw = kw
        self._orig_table = _orig_table

    @classmethod
    def from_table(cls, table):
        return CreateTableOp(
            table.name,
            list(table.c) + list(table.constraints),
            schema=table.schema,
            _orig_table=table,
            **table.kwargs
        )

    def to_table(self, migration_context=None):
        if self._orig_table is not None:
            return self._orig_table
        schema_obj = schemaobj.SchemaObjects(migration_context)

        return schema_obj.table(
            self.table_name, *self.columns, schema=self.schema, **self.kw
        )


class DropTableOp(MigrateOperation):
    def __init__(self, table_name, schema=None, table_kw=None):
        self.table_name = table_name
        self.schema = schema
        self.table_kw = table_kw or {}

    @classmethod
    def from_table(cls, table):
        return DropTableOp(table.name, schema=table.schema)

    def to_table(self, migration_context):
        schema_obj = schemaobj.SchemaObjects(migration_context)
        return schema_obj.table(
            self.table_name,
            schema=self.schema,
            **self.table_kw)


class AlterTableOp(MigrateOperation):

    def __init__(self, table_name, schema=None):
        self.table_name = table_name
        self.schema = schema


class RenameTableOp(AlterTableOp):

    def __init__(self, old_table_name, new_table_name, schema=None):
        super(RenameTableOp, self).__init__(old_table_name, schema=schema)
        self.new_table_name = new_table_name


class AlterColumnOp(AlterTableOp):

    def __init__(
            self, table_name, column_name, schema=None,
            existing_type=None,
            existing_server_default=False,
            existing_nullable=None,
            modify_nullable=None,
            modify_server_default=False,
            modify_name=None,
            modify_type=None,
            **kw

    ):
        super(AlterColumnOp, self).__init__(table_name, schema=schema)
        self.column_name = column_name
        self.existing_type = existing_type
        self.existing_server_default = existing_server_default
        self.existing_nullable = existing_nullable
        self.modify_nullable = modify_nullable
        self.modify_server_default = modify_server_default
        self.modify_name = modify_name
        self.modify_type = modify_type
        self.kw = kw


class AddColumnOp(AlterTableOp):

    def __init__(self, table_name, column, schema=None):
        super(AddColumnOp, self).__init__(table_name, schema=schema)
        self.column = column

    @classmethod
    def from_column(cls, col):
        return AddColumnOp(col.table.name, col, schema=col.table.schema)

    @classmethod
    def from_column_and_tablename(cls, schema, tname, col):
        return AddColumnOp(tname, col, schema=schema)


class DropColumnOp(AlterTableOp):

    def __init__(self, table_name, column_name, schema=None, **kw):
        super(DropColumnOp, self).__init__(table_name, schema=schema)
        self.column_name = column_name
        self.kw = kw

    @classmethod
    def from_column_and_tablename(cls, schema, tname, col):
        return DropColumnOp(tname, col.name, schema=schema)

    def to_column(self, migration_context=None):
        schema_obj = schemaobj.SchemaObjects(migration_context)
        return schema_obj.column(self.column_name, NULLTYPE)


class BulkInsertOp(MigrateOperation):
    def __init__(self, table, rows, multiinsert=True):
        self.table = table
        self.rows = rows
        self.multiinsert = multiinsert


class OpContainer(MigrateOperation):
    def __init__(self, ops):
        self.ops = ops


class ModifyTableOps(OpContainer):
    """Contains a sequence of operations that all apply to a single Table."""

    def __init__(self, table_name, ops, schema=None):
        super(ModifyTableOps, self).__init__(ops)
        self.table_name = table_name
        self.schema = schema


class UpgradeOps(OpContainer):
    """contains a sequence of operations that would apply to the
    'upgrade' stream of a script."""


class DowngradeOps(OpContainer):
    """contains a sequence of operations that would apply to the
    'downgrade' stream of a script."""


class MigrationScript(MigrateOperation):
    """represents a migration script.

    E.g. when autogenerate encounters this object, this corresponds to the
    production of an actual script file.

    A normal :class:`.MigrationScript` object would contain a single
    :class:`.UpgradeOps` and a single :class:`.DowngradeOps` directive.

    """

    def __init__(
            self, rev_id, upgrade_ops, downgrade_ops,
            message=None,
            imports=None, head=None, splice=None,
            branch_label=None, version_path=None):
        self.rev_id = rev_id
        self.message = message
        self.imports = imports
        self.head = head
        self.splice = splice
        self.branch_label = branch_label
        self.version_path = version_path
        self.upgrade_ops = upgrade_ops
        self.downgrade_ops = downgrade_ops
