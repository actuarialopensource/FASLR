from faslr.project_item import ProjectItem

def test_project_item() -> None:

    project_item = ProjectItem(
        text="My Project"
    )

    assert project_item.text() == "My Project"