Verification step. Call run_command exactly once with this command (copy it exactly):
echo "== repro =="; timeout 30 python _repro_check.py 2>&1 | tail -8; echo "== exit $? =="; echo "== changed =="; git diff --name-only; echo "== tests =="; for f in $(git diff --name-only | grep '\.py$'); do m=$(basename "$f" .py); grep -rlE "import .*\b$m\b|from .*\b$m\b|test_$m" tests 2>/dev/null | head -2; done | sort -u | head -3 | xargs -r timeout 120 python -m pytest -q -x -p no:cacheprovider 2>&1 | tail -10

Then reply without any other tool call: "VERIFIED" if the repro exit is 0 and the tests pass, otherwise "NOT VERIFIED" with the exact failing lines.
