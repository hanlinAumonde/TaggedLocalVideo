def assert_no_errors(result):
    assert result.errors is None or result.errors == [], (
        f"Expected no GraphQL errors, got: {result.errors}"
    )


def make_browse_input(relative_path=None, skip_cache=False, recursive=True):
    return {
        "relativePath": relative_path,
        "skipCache": skip_cache,
        "recursiveCalculation": recursive,
    }


def make_search_input(**overrides):
    base = {
        "titleKeyword": {"keyWord": None},
        "author": {"keyWord": None},
        "tags": [],
        "sortBy": "Latest",
        "fromPage": "SearchPage",
        "currentPageNumber": 1,
    }
    base.update(overrides)
    return base