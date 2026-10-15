import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "evaluation" / "harness"))
import delivery_report  # noqa: E402
import generate_ai_bom  # noqa: E402
import graders  # noqa: E402
import passk  # noqa: E402
import run_eval  # noqa: E402

HOOKS = ROOT / ".claude" / "hooks"


def run_hook(name, event, project):
    return subprocess.run([sys.executable, str(HOOKS / name)], input=json.dumps(event), text=True,
                          capture_output=True, env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)})


class HookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)
        (self.project / ".claude").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def bash(self, command):
        return run_hook("block_secrets.py", {"tool_name": "Bash", "tool_input": {"command": command}}, self.project).returncode

    def test_blocks_secret_reads(self):
        for command in ("cat .env", "head -5 api/.env.local", "printenv", "docker compose config", "grep -rn KEY .", "less secrets/x"):
            self.assertEqual(self.bash(command), 2, command)

    def test_allows_normal_commands(self):
        for command in ("make test", "docker compose --env-file .env up -d", "cat .env.example | wc -l",
                        "grep -rn --exclude=.env* KEY api", "python3 scripts/trace_check.py"):
            self.assertEqual(self.bash(command), 0, command)

    def test_blocks_read_tool_and_logs(self):
        result = run_hook("block_secrets.py", {"tool_name": "Read", "tool_input": {"file_path": str(self.project / ".env")}}, self.project)
        self.assertEqual(result.returncode, 2)
        log = (self.project / "reports/hooks/events.jsonl").read_text(encoding="utf-8")
        self.assertIn('"decision": "deny"', log)
        self.assertNotIn("sk-", log)

    def test_protect_approved_tests(self):
        (self.project / ".claude/approved-tests.txt").write_text("# comment\napi/tests/test_owner*.py\n", encoding="utf-8")
        edit = lambda path: run_hook("protect_approved_tests.py", {"tool_name": "Edit", "tool_input": {"file_path": path}}, self.project).returncode  # noqa: E731
        self.assertEqual(edit("api/tests/test_owner_notebook.py"), 2)
        self.assertEqual(edit(".claude/approved-tests.txt"), 2)
        self.assertEqual(edit("api/app/routers/chat.py"), 0)

    def test_protect_approved_tests_from_playwright_generator(self):
        (self.project / ".claude/approved-tests.txt").write_text("web/e2e/notebook-*.spec.ts\n", encoding="utf-8")
        write = lambda name: run_hook("protect_approved_tests.py", {"tool_name": "mcp__playwright-test__generator_write_test", "tool_input": {"fileName": name, "code": "x"}}, self.project).returncode  # noqa: E731
        self.assertEqual(write("web/e2e/notebook-owner.spec.ts"), 2)
        self.assertEqual(write("web/e2e/generated/new-journey.spec.ts"), 0)

    def test_empty_approved_list_is_noop(self):
        result = run_hook("protect_approved_tests.py", {"tool_name": "Write", "tool_input": {"file_path": "api/tests/test_new.py"}}, self.project)
        self.assertEqual(result.returncode, 0)


class ApprovedTestsGuardTests(unittest.TestCase):
    # Git mới (runner GitHub) tự chạy maintenance nền sau commit và ghi vào .git trong lúc
    # TemporaryDirectory dọn dẹp, gây "Directory not empty". Tắt maintenance tự động cho repo tạm.
    GIT_QUIET = ("-c", "maintenance.auto=false", "-c", "gc.auto=0")

    def git(self, *args):
        return subprocess.run(["git", *self.GIT_QUIET, *args], cwd=self.repo, check=True, capture_output=True, text=True).stdout

    def commit(self, message):
        self.git("add", "-A")
        self.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", message)

    def test_trailer_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.repo = Path(tmp)
            self.git("init", "-q")
            (self.repo / ".claude").mkdir()
            (self.repo / ".claude/approved-tests.txt").write_text("tests/test_a.py\n")
            (self.repo / "tests").mkdir()
            (self.repo / "tests/test_a.py").write_text("assert 1\n")
            self.commit("base")
            base = self.git("rev-parse", "HEAD").strip()
            (self.repo / "tests/test_a.py").write_text("assert 2\n")
            self.commit("agent changed test")
            script = ROOT / "scripts" / "check_approved_tests.py"
            fail = subprocess.run([sys.executable, str(script), "--base", base], cwd=self.repo, capture_output=True, text=True)
            self.assertEqual(fail.returncode, 1)
            self.git("reset", "-q", "--hard", base)
            (self.repo / "tests/test_a.py").write_text("assert 3\n")
            self.commit("test: fix expected\n\nTest-Change-Approved: expected sai so voi SRS IH-NB-004-AC01")
            ok = subprocess.run([sys.executable, str(script), "--base", base], cwd=self.repo, capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stdout)

    def test_new_test_can_be_approved_without_trailer_but_not_weakened(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.repo = Path(tmp)
            self.git("init", "-q")
            (self.repo / ".claude").mkdir()
            (self.repo / ".claude/approved-tests.txt").write_text("# none yet\n")
            self.commit("base")
            base = self.git("rev-parse", "HEAD").strip()
            script = ROOT / "scripts" / "check_approved_tests.py"
            check = lambda: subprocess.run([sys.executable, str(script), "--base", base], cwd=self.repo, capture_output=True, text=True)  # noqa: E731
            (self.repo / "tests").mkdir()
            (self.repo / "tests/test_b.py").write_text("assert 1\n")
            (self.repo / ".claude/approved-tests.txt").write_text("tests/test_b.py\n")
            self.commit("test: add and approve red test")
            self.assertEqual(check().returncode, 0)
            (self.repo / "tests/test_b.py").write_text("assert 0\n")
            self.commit("feat: agent weakened test")
            self.assertEqual(check().returncode, 1)
            self.git("reset", "-q", "--hard", "HEAD~1")
            (self.repo / ".claude/approved-tests.txt").write_text("# removed\n")
            self.commit("chore: drop approval")
            result = check()
            self.assertEqual(result.returncode, 1)
            self.assertIn("removed patterns", result.stdout)


class EvalHarnessTests(unittest.TestCase):
    def quiz_case(self):
        return {"id": "Q", "tool": "quiz", "expected_status": "Succeeded", "config": {"question_count": 5}, "sources": ["01_quy_trinh_vi.md"]}

    def test_quiz_structure(self):
        good = {"status": "Succeeded", "citations": [{"citation_id": "c1", "document_id": 1}],
                "quiz": {"questions": [{"text": f"Q{i}", "options": ["a", "b", "c", "d"], "answer_index": 1,
                                        "explanation": "vì", "citation_ids": ["c1"]} for i in range(5)]}}
        passed, _ = graders.grade(self.quiz_case(), good, {1})
        self.assertTrue(passed)
        good["quiz"]["questions"][0]["options"] = ["a", "a", "c", "d"]
        passed, checks = graders.grade(self.quiz_case(), good, {1})
        self.assertFalse(passed)
        self.assertIn("distinct", checks["quiz_structure"]["detail"])

    def test_citation_scope_and_noevidence(self):
        case = {"id": "C", "tool": "chat", "expected_status": "NoEvidence", "sources": ["01_quy_trinh_vi.md"]}
        out = {"status": "NoEvidence", "claims": [], "citations": [{"citation_id": "x", "document_id": 9}]}
        passed, checks = graders.grade(case, out, {1})
        self.assertFalse(passed)
        self.assertFalse(checks["citation_scope"]["passed"])

    def test_summary_length(self):
        case = {"tool": "summary", "expected_status": "Succeeded", "config": {"length": "short"}}
        self.assertTrue(graders.summary_length(case, {"text": "từ " * 200})[0])
        self.assertFalse(graders.summary_length(case, {"text": "từ " * 100})[0])

    def test_pass_hat_k(self):
        per_case = passk.aggregate([{"case_id": "a", "passed": True}, {"case_id": "a", "passed": False}, {"case_id": "b", "passed": True}])
        self.assertFalse(per_case["a"]["pass_hat_k"])
        self.assertTrue(per_case["a"]["pass_at_k"])
        self.assertEqual(passk.suite_rate(per_case), 0.5)

    def test_example_suite_valid_and_bad_suite_rejected(self):
        suite = json.loads((ROOT / "evaluation/harness/suites/example-chat.json").read_text(encoding="utf-8"))
        self.assertEqual(run_eval.validate_suite(suite), [])
        suite["cases"][0]["expected_points"] = []
        suite["cases"][0]["sources"] = ["missing.md"]
        self.assertGreaterEqual(len(run_eval.validate_suite(suite)), 2)


class HandoverToolTests(unittest.TestCase):
    def test_ai_bom_never_reads_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            env.write_text("LLM_PROVIDER=deepseek\nDEEPSEEK_API_KEY=sk-secret\nDATABASE_URL=postgresql://u:p@db/x\n")
            bom = generate_ai_bom.build(env)
            text = json.dumps(bom)
            self.assertNotIn("sk-secret", text)
            self.assertNotIn("u:p@", text)
            self.assertEqual(bom["models_and_providers"]["llm_provider"], "deepseek")
            self.assertTrue(bom["prompts"])

    def test_delivery_metrics_treat_blank_as_unmeasured(self):
        rows = [{"milestone": "M1", "review_minutes": "20", "diff_lines": "100", "ai_findings": "4", "ai_findings_valid": "1",
                 "rework_rounds": "0", "outcome": "accepted", "ci_first_run": "pass", "cost_usd": "", "tokens": "",
                 "pr_opened": "2026-10-01T09:00", "pr_merged": "2026-10-01T11:00", "author_minutes": "30"}]
        m = delivery_report.metrics(rows)
        self.assertEqual(m["AI review precision"], 0.25)
        self.assertIsNone(m["Cost USD/accepted change"])
        self.assertEqual(m["PR lead time median, giờ (proxy)"], 2.0)

    def test_agent_first_pass_and_cost_include_rejected_work(self):
        rows = [
            {"agent_mode": "edit", "outcome": "accepted", "rework_rounds": "1", "cost_usd": "1.0"},
            {"agent_mode": "edit", "outcome": "accepted", "rework_rounds": "3", "cost_usd": "2.0"},
            {"agent_mode": "auto", "outcome": "rejected", "rework_rounds": "0", "cost_usd": "1.0"},
            {"agent_mode": "edit", "outcome": "", "rework_rounds": "", "cost_usd": ""},
            {"agent_mode": "chat", "outcome": "accepted", "rework_rounds": "0", "cost_usd": ""},
        ]
        m = delivery_report.metrics(rows)
        self.assertAlmostEqual(m["PR agent được chấp nhận lần đầu (tối đa 1 vòng sửa)"], 1 / 3)
        self.assertAlmostEqual(m["Cost USD/accepted change"], 4.0 / 3)


if __name__ == "__main__":
    unittest.main()
