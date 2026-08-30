# Hints — INF-003

## H1 — concept

Keep request lifecycle state separate from the two budgets.  Prefill consumes
prompt tokens once; decode consumes one resident token per scheduled request.
Terminal transitions must release the same capacity that admission charged.

## H2 — structure

Use a FIFO queue for pending requests and a deque for the persistent
round-robin active order.  Validate a complete request before mutating any
queue.  At each step, expire old requests, admit without skipping the head,
then decode at most one token per selected active request.

## H3 — debugging questions

- What happens if the first queued prompt is larger than the remaining
  prefill budget but a later prompt would fit?
- Does a request admitted during this call receive a decode token immediately?
- After cancellation or automatic completion, which token count must be
  released, and can a new request use it in the next step?
- Where should an absolute deadline be checked relative to admission and
  decode?
- How will you prevent a caller from mutating the internal queue through a
  returned snapshot?

No complete implementation is included.
