import tempfile
import unittest
from zipfile import ZipFile

from host.scenario_converter import (
    extract_docx_text_without_dependency,
    fallback_structured_scenario,
    parse_json_response,
    render_markdown,
)


class ScenarioConverterTests(unittest.TestCase):
    def test_extract_docx_text_with_unicode_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            from pathlib import Path

            docx_path = Path(temp_dir) / "疯狂之馆(最终定稿) .docx"
            xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>测试剧本</w:t></w:r></w:p>
    <w:p><w:r><w:t>第二段</w:t></w:r></w:p>
  </w:body>
</w:document>
"""
            with ZipFile(docx_path, "w") as archive:
                archive.writestr("word/document.xml", xml)

            text = extract_docx_text_without_dependency(docx_path)

        self.assertIn("测试剧本", text)
        self.assertIn("第二段", text)

    def test_parse_json_response_from_fenced_text(self):
        parsed = parse_json_response('```json\n{"title":"館","rules":["待つ"]}\n```')

        self.assertEqual(parsed, {"title": "館", "rules": ["待つ"]})

    def test_fallback_scenario_renders_markdown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            from pathlib import Path

            source = Path(temp_dir) / "sample.txt"
            scenario = fallback_structured_scenario(source, "冒険が始まる。")
            markdown = render_markdown(scenario)

        self.assertEqual(scenario["title"], "sample")
        self.assertIn("# sample", markdown)
        self.assertIn("冒険が始まる。", markdown)


if __name__ == "__main__":
    unittest.main()
