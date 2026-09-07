`summarize.py` is a small CSV summariser. Add a `--top N` option that limits the
output to the N largest groups by total, keeping the existing sort order.

`test_summarize.py` already covers the new behaviour and currently fails. Run the
suite with `python3 -m unittest discover -s . -p 'test_*.py'`. Do not change the tests.
