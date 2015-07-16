from .langhelpers import (  # noqa
    asbool, rev_id, to_tuple, to_list, memoized_property,
    immutabledict, _with_legacy_names, Dispatcher, ModuleClsProxy)
from .messaging import (  # noqa
    write_outstream, status, err, obfuscate_url_pw, warn, msg, format_as_comma)
from .pyfiles import (  # noqa
    template_to_file, coerce_resource_to_filename, simple_pyc_file_from_path,
    pyc_file_from_path, load_python_file)
from .sqla_compat import (  # noqa
    sqla_07, sqla_079, sqla_08, sqla_083, sqla_084, sqla_09, sqla_092,
    sqla_094, sqla_094, sqla_099, sqla_100, sqla_105)


class CommandError(Exception):
    pass


if not sqla_07:
    raise CommandError(
        "SQLAlchemy 0.7.3 or greater is required. ")
