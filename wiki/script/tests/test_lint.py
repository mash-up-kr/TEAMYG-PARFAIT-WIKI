import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lint  # noqa: E402


VALID_APP_SIDE_FRONTMATTER = (
    "---\n"
    "title: 앱 사이드메뉴 정책\n"
    "domain: app-side\n"
    "doc_code: SM-001\n"
    "status: draft\n"
    "source: raw/app-side/app-side-policy.md\n"
    "updated: 2026-08-14\n"
    "---\n"
)


class ParseFrontmatterTests(unittest.TestCase):
    def test_extracts_fields(self):
        text = "---\ntitle: 앱 사이드메뉴 정책\ndomain: app-side\n---\n\n# 본문\n"
        fields = lint.parse_frontmatter(text)
        self.assertEqual(fields["title"], "앱 사이드메뉴 정책")
        self.assertEqual(fields["domain"], "app-side")

    def test_returns_empty_without_frontmatter(self):
        self.assertEqual(lint.parse_frontmatter("# 본문만 있음\n"), {})


class CheckDomainsTests(unittest.TestCase):
    def test_flags_missing_file(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "wiki" / "domains").mkdir(parents=True)
            routing = {"domains": ["onboarding", "app-side"]}
            errors = lint.check_domains(routing, root)
            self.assertTrue(any("missing wiki/domains/onboarding.md" in e for e in errors))
            self.assertTrue(
                any("missing wiki/domains/app-side.md" in e for e in errors)
            )

    def test_flags_missing_required_field(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            domains_dir = root / "wiki" / "domains"
            domains_dir.mkdir(parents=True)
            (domains_dir / "app-side.md").write_text(
                "---\ntitle: 앱 사이드메뉴 정책\ndomain: app-side\n---\n\n본문\n",
                encoding="utf-8",
            )
            routing = {"domains": ["app-side"]}
            errors = lint.check_domains(routing, root)
            self.assertTrue(
                any("missing frontmatter field 'doc_code'" in e for e in errors)
            )

    def test_flags_domain_mismatch(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            domains_dir = root / "wiki" / "domains"
            domains_dir.mkdir(parents=True)
            text = VALID_APP_SIDE_FRONTMATTER.replace(
                "domain: app-side", "domain: onboarding"
            )
            (domains_dir / "app-side.md").write_text(text, encoding="utf-8")
            (root / "raw" / "app-side").mkdir(parents=True)
            (root / "raw" / "app-side" / "app-side-policy.md").write_text("x")

            routing = {"domains": ["app-side"]}
            errors = lint.check_domains(routing, root)
            self.assertTrue(any("does not match filename" in e for e in errors))

    def test_flags_missing_source(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            domains_dir = root / "wiki" / "domains"
            domains_dir.mkdir(parents=True)
            (domains_dir / "app-side.md").write_text(
                VALID_APP_SIDE_FRONTMATTER, encoding="utf-8"
            )
            routing = {"domains": ["app-side"]}
            errors = lint.check_domains(routing, root)
            self.assertTrue(any("does not exist" in e for e in errors))

    def test_passes_with_valid_doc(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            domains_dir = root / "wiki" / "domains"
            domains_dir.mkdir(parents=True)
            (domains_dir / "app-side.md").write_text(
                VALID_APP_SIDE_FRONTMATTER, encoding="utf-8"
            )
            (root / "raw" / "app-side").mkdir(parents=True)
            (root / "raw" / "app-side" / "app-side-policy.md").write_text("x")

            routing = {"domains": ["app-side"]}
            errors = lint.check_domains(routing, root)
            self.assertEqual(errors, [])


class CheckIndexLinksTests(unittest.TestCase):
    def test_flags_missing_domain(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "wiki").mkdir(parents=True)
            (root / "wiki" / "index.md").write_text(
                "# 위키 허브\n\n- [온보딩](domains/onboarding.md)\n", encoding="utf-8"
            )
            routing = {"domains": ["onboarding", "app-side"]}
            errors = lint.check_index_links(routing, root)
            self.assertEqual(len(errors), 1)
            self.assertIn("app-side", errors[0])


if __name__ == "__main__":
    unittest.main()
