"""
The portability check, re-exported from ``inkfold.check.lint`` where it ships (#278).

The rules are product behaviour an installed copy needs, so they moved into the
package; this name stays so the harness and its tests import as before.
"""

from inkfold.check.lint import *  # noqa: F403
from inkfold.check.lint import __all__ as __all__
