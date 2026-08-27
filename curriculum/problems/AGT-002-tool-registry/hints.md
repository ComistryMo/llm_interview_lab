# Hints — AGT-002

## H1 — concept

Define the accepted action or event shapes before writing the loop. Invalid data is an explicit state transition, not an implicit exception leak.

## H2 — structure

Keep validation, registry/storage, and orchestration responsibilities separate. Copy caller-owned containers at the boundary.

## H3 — steps

Validate outer inputs, process one action/event at a time in physical order, append one explicit result, and check termination after every step. Test one invalid action and one max-step path.

No complete implementation is included.

