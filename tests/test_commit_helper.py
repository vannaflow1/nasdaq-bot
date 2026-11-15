"""End-to-end: real git repositories in a temp folder, real .github/actions_common.sh, jobs racing each other."""
import json, os, shutil, subprocess, tempfile, unittest
from _util import ROOT


def sh(cmd, cwd, check=True):
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull, GIT_TERMINAL_PROMPT="0")
    return subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, check=check, env=env)


@unittest.skipUnless(shutil.which("git") and shutil.which("bash"), "needs git and bash")
class CommitHelper(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        sh("git init -q --bare -b main origin.git", self.d)
        sh("git clone -q origin.git seed", self.d); seed = os.path.join(self.d, "seed")
        sh("git checkout -q -b main", seed, check=False)
        os.makedirs(os.path.join(seed, "tools")); os.makedirs(os.path.join(seed, ".github"))
        shutil.copy(os.path.join(ROOT, "tools", "status_merge.py"), os.path.join(seed, "tools"))
        helper = open(os.path.join(ROOT, ".github", "actions_common.sh")).read().replace("sleep $((i*5))", "sleep 0")
        open(os.path.join(seed, ".github", "actions_common.sh"), "w").write(helper)
        shutil.copy(os.path.join(ROOT, ".gitattributes"), seed)
        json.dump({"alpha": ["a0"], "bias": ["b0"], "eta": ["e0"], "zeta": ["z0"]}, open(os.path.join(seed, "status.json"), "w"), indent=1)
        sh("git add -A && git -c user.name=t -c user.email=t@t commit -q -m seed && git push -q -u origin main", seed)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def job(self, name, changes):
        sh(f"git clone -q origin.git {name}", self.d); p = os.path.join(self.d, name)
        return p, changes

    def write(self, repo, changes):
        s = json.load(open(os.path.join(repo, "status.json"))); s.update(changes)
        json.dump(s, open(os.path.join(repo, "status.json"), "w"), indent=1)

    def save(self, repo, label="job"):
        return sh(f'bash .github/actions_common.sh "{label}"', repo, check=False)

    def remote_status(self):
        sh("rm -rf check && git clone -q origin.git check", self.d)
        return json.load(open(os.path.join(self.d, "check", "status.json")))

    def test_two_jobs_changing_neighbouring_entries_both_survive(self):
        a, _ = self.job("jobA", None); b, _ = self.job("jobB", None)       # both start from the same snapshot
        self.write(b, {"bias": ["B new", "B 2"], "alpha": ["B alpha"]}); self.assertIn("pushed", self.save(b).stdout)
        self.write(a, {"eta": ["A new"]}); self.assertIn("pushed", self.save(a).stdout)
        self.assertEqual(self.remote_status(), {"alpha": ["B alpha"], "bias": ["B new", "B 2"], "eta": ["A new"], "zeta": ["z0"]})

    def test_refused_upload_is_retried_on_the_next_call(self):
        hook = os.path.join(self.d, "origin.git", "hooks", "pre-receive"); flag = os.path.join(self.d, "REJECT")
        open(hook, "w").write(f'#!/bin/sh\n[ -f "{flag}" ] && exit 1\nexit 0\n'); os.chmod(hook, 0o755)
        c, _ = self.job("jobC", None); self.write(c, {"zeta": ["from C"]})
        open(flag, "w").close()
        r = self.save(c); self.assertNotEqual(r.returncode, 0); self.assertIn("NOT in the repo", r.stdout)
        os.remove(flag)
        r = self.save(c); self.assertEqual(r.returncode, 0); self.assertIn("retrying an earlier commit", r.stdout)
        self.assertEqual(self.remote_status()["zeta"], ["from C"])

    def test_nothing_to_save_is_quiet(self):
        c, _ = self.job("jobD", None)
        r = self.save(c); self.assertEqual(r.returncode, 0); self.assertIn("no state change", r.stdout)


if __name__ == "__main__":
    unittest.main()
