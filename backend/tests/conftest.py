"""Pytest options for the backend tests.

`--baseline` opts in to the tests marked `baseline`: the ones that reproduce the DAT7 baseline against private reference
files (see `test_baseline_regression.py` and the section "Reference files" of `backend/README.md`). Without the option those
tests are deselected, so pytest reports them as "deselected" and never as "skipped". Every other test is selected as usual.
"""


def pytest_addoption(parser):
    parser.addoption(
        "--baseline",
        action="store_true",
        default=False,
        help="also run the tests marked `baseline` (they need the private DAT7 baseline reference files)",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--baseline"):
        return
    deselected = [item for item in items if item.get_closest_marker("baseline")]
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = [item for item in items if item not in deselected]
