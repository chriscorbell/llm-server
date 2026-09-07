"""Write a copy of index.html with a layout self-check appended.

Kept outside the fixture so the agent under test cannot edit the check.
"""
import pathlib
import sys

out = pathlib.Path(sys.argv[1])
html = pathlib.Path("index.html").read_text()
check = (
    "<script>\n"
    "window.addEventListener('load', function () {\n"
    "  var bar = document.querySelector('.sidebar').getBoundingClientRect();\n"
    "  var main = document.querySelector('.content').getBoundingClientRect();\n"
    "  var h1 = document.querySelector('h1').getBoundingClientRect();\n"
    "  var overlaps = main.left < bar.right - 0.5 || h1.left < bar.right - 0.5;\n"
    "  var sidebarGone = bar.width < 200;\n"
    "  document.title = (overlaps || sidebarGone) ? 'LAYOUT_FAIL' : 'LAYOUT_PASS';\n"
    "});\n"
    "</script>\n"
)
(out / "index.html").write_text(html.replace("</body>", check + "</body>"))
