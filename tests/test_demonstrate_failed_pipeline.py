"""INTENTIONAL FAILURE — demo/ci-no-go branch ONLY.

This branch exists to demonstrate that failed tests block release evidence
collection on a genuine GitLab pipeline. NEVER merge this file to main.
This failure uses no credentials, secrets, network, or production code.
"""
import unittest


class IntentionalReleaseBlocker(unittest.TestCase):
    def test_demo_ci_fails_closed(self):
        self.fail("DEMONSTRATION ONLY: test failure must block CI admission.")


if __name__=="__main__":
    unittest.main()
