import json


def write_html(path, body):
    path.write_text(body, encoding="utf-8")
    return str(path)


def test_html_diff_detects_text_attribute_resource_table_and_move(tmp_path):
    from app.diff_engine.html_diff import HtmlDiffEngine

    old_path = write_html(
        tmp_path / "old.html",
        """
        <!doctype html>
        <html>
          <head><title>Old</title><script>console.log('ignore')</script></head>
          <body>
            <h1 id="title">Product A</h1>
            <p id="intro" class="lead">Hello world</p>
            <img id="hero" src="/img/a.png" alt="Hero A">
            <ul>
              <li id="first">First</li>
              <li id="second">Second</li>
            </ul>
            <table id="price">
              <tr><th>Name</th><th>Price</th></tr>
              <tr><td>Basic</td><td>10</td></tr>
            </table>
            <a id="cta" href="/old">Buy</a>
          </body>
        </html>
        """,
    )
    new_path = write_html(
        tmp_path / "new.html",
        """
        <!doctype html>
        <html>
          <head><title>New</title><style>.ignored { color: red }</style></head>
          <body>
            <h1 id="title">Product A Plus</h1>
            <p id="intro" class="lead strong">Hello brave world</p>
            <img id="hero" src="/img/b.png" alt="Hero B">
            <ul>
              <li id="second">Second</li>
              <li id="first">First</li>
              <li id="third">Third</li>
            </ul>
            <table id="price">
              <tr><th>Name</th><th>Price</th></tr>
              <tr><td>Basic</td><td>12</td></tr>
              <tr><td>Pro</td><td>20</td></tr>
            </table>
            <a id="cta" href="/new">Buy now</a>
          </body>
        </html>
        """,
    )

    result = HtmlDiffEngine().compare(old_path, new_path)

    assert result["type"] == "html_diff"
    assert result["metadata"]["old_node_count"] > 0
    assert result["metadata"]["new_node_count"] > result["metadata"]["old_node_count"]
    assert result["stats"]["text_modified"] >= 2
    assert result["stats"]["nodes_added"] >= 1
    assert result["stats"]["nodes_moved"] >= 1
    assert result["stats"]["attributes_changed"] >= 2
    assert result["stats"]["resources_changed"] >= 1
    assert result["stats"]["tables_changed"] >= 1
    assert result["stats"]["total_changes"] >= 8

    assert any(item["change_type"] == "modified" and item["tag"] == "h1" for item in result["text"])
    assert any(item["change_type"] == "moved" and item["tag"] == "li" for item in result["nodes"])
    assert any(item["attribute"] == "src" for item in result["resources"])
    assert any(item["attribute"] == "class" for item in result["attributes"])
    assert any(item["change_type"] == "modified" for item in result["tables"])

    serialized = json.dumps(result, ensure_ascii=False)
    assert "<script>" not in serialized
    assert "console.log" not in serialized
    assert "<style>" not in serialized


def test_html_diff_is_registered_for_html_and_htm():
    from app.diff_engine.factory import get_diff_engine, is_supported
    from app.diff_engine.html_diff import HtmlDiffEngine

    assert is_supported("html") is True
    assert is_supported("htm") is True
    assert isinstance(get_diff_engine("html"), HtmlDiffEngine)
    assert isinstance(get_diff_engine(".htm"), HtmlDiffEngine)
