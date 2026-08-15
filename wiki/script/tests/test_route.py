import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import route  # noqa: E402


def make_routing():
    return {
        "domains": ["onboarding", "app-side"],
        "intents": {
            "query": {"files": ["wiki/domains/{domain}.md"]},
            "ingest": {"files": ["raw/{domain}/*.md", "wiki/domains/{domain}.md"]},
            "lint": {"files": ["wiki/domains/*.md"]},
            "add-domain": {"files": ["wiki/conventions.md"]},
        },
    }


class ResolveFilesTests(unittest.TestCase):
    def test_query_resolves_single_domain_file(self):
        files = route.resolve_files(make_routing(), "query", "onboarding", Path("/repo"))
        self.assertEqual(files, ["wiki/domains/onboarding.md"])

    def test_unknown_domain_raises(self):
        with self.assertRaises(ValueError) as ctx:
            route.resolve_files(make_routing(), "query", "unknown", Path("/repo"))
        self.assertIn("unknown domain", str(ctx.exception))

    def test_query_without_domain_raises(self):
        with self.assertRaises(ValueError) as ctx:
            route.resolve_files(make_routing(), "query", None, Path("/repo"))
        self.assertIn("--domain is required", str(ctx.exception))

    def test_ingest_expands_glob(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "raw" / "onboarding").mkdir(parents=True)
            (root / "raw" / "onboarding" / "onboarding-policy.md").write_text("x")
            (root / "wiki" / "domains").mkdir(parents=True)
            (root / "wiki" / "domains" / "onboarding.md").write_text("y")

            files = route.resolve_files(make_routing(), "ingest", "onboarding", root)
            self.assertEqual(
                files, ["raw/onboarding/onboarding-policy.md", "wiki/domains/onboarding.md"]
            )

    def test_add_domain_allows_unregistered_domain(self):
        files = route.resolve_files(
            make_routing(), "add-domain", "brand-new-domain", Path("/repo")
        )
        self.assertEqual(files, ["wiki/conventions.md"])

    def test_lint_expands_glob_across_domains(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "wiki" / "domains").mkdir(parents=True)
            (root / "wiki" / "domains" / "onboarding.md").write_text("a")
            (root / "wiki" / "domains" / "app-side.md").write_text("b")

            files = route.resolve_files(make_routing(), "lint", None, root)
            self.assertEqual(
                files, ["wiki/domains/app-side.md", "wiki/domains/onboarding.md"]
            )


if __name__ == "__main__":
    unittest.main()
