# tests/run_sanity.py
import unittest

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromName("tests.test_phase_b_sanity")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    # Return non-zero exit if any test failed, useful for CI/hooks
    raise SystemExit(0 if result.wasSuccessful() else 1)

