"""Shared analyses and scoped storage for ca65 expression lowering."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from .ast import (
    ImmediateValue,
    ResolvedArrayElement,
    ResolvedArrayElementAssignment,
    ResolvedAssignment,
    ResolvedBinaryExpression,
    ResolvedBooleanBinaryExpression,
    ResolvedBooleanNotExpression,
    ResolvedBuiltinCall,
    ResolvedComparisonExpression,
    ResolvedDecrementStatement,
    ResolvedForStatement,
    ResolvedIfStatement,
    ResolvedIncrementStatement,
    ResolvedProcedureCall,
    ResolvedProgram,
    ResolvedRecordField,
    ResolvedRecordFieldAssignment,
    ResolvedRepeatStatement,
    ResolvedStatement,
    ResolvedUnaryExpression,
    ResolvedValue,
    ResolvedWhileStatement,
    VariableValue,
)


class TemporaryPoolExhausted(RuntimeError):
    """Raised when lowering requests a slot outside its reserved pool."""


@dataclass(slots=True)
class TemporarySlot:
    """One explicitly leased expression-temporary slot."""

    pool: "TemporaryPool"
    index: int
    _released: bool = False

    @property
    def name(self) -> str:
        return f"expression_temporary_{self.index}"

    def release(self) -> None:
        if self._released:
            raise AssertionError(f"temporary slot {self.index} released twice")
        self.pool.release(self.index)
        self._released = True

    def __enter__(self) -> "TemporarySlot":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.release()


class TemporaryPool:
    """Deterministic scoped allocator for compiler expression bytes.

    Slots are leased from the lowest available index. Active caller slots stay
    leased across ``call_scope`` boundaries, so nested expression-producing
    calls can only receive non-aliasing slots. This is the compile-time rule
    that future function lowering must preserve; no runtime frame is needed by
    the current procedure-only language.
    """

    def __init__(self, capacity: int | None = None) -> None:
        if capacity is not None and capacity < 0:
            raise ValueError("temporary pool capacity cannot be negative")
        self.capacity = capacity
        self._active: set[int] = set()
        self.max_live = 0

    @property
    def live_count(self) -> int:
        return len(self._active)

    def acquire(self) -> TemporarySlot:
        index = 0
        while index in self._active:
            index += 1
        if self.capacity is not None and index >= self.capacity:
            raise TemporaryPoolExhausted(
                f"temporary pool requires slot {index}, but only "
                f"{self.capacity} slots were reserved"
            )
        self._active.add(index)
        self.max_live = max(self.max_live, len(self._active))
        return TemporarySlot(self, index)

    def release(self, index: int) -> None:
        if index not in self._active:
            raise AssertionError(f"temporary slot {index} is not active")
        self._active.remove(index)

    @contextmanager
    def call_scope(self) -> Iterator["TemporaryPool"]:
        """Preserve every caller-owned lease across a nested call boundary."""

        caller_slots = frozenset(self._active)
        try:
            yield self
        finally:
            if frozenset(self._active) != caller_slots:
                raise AssertionError("nested call leaked an expression temporary")

    def assert_all_released(self) -> None:
        if self._active:
            raise AssertionError(
                "expression temporary leak: "
                + ", ".join(str(index) for index in sorted(self._active))
            )


@dataclass(frozen=True, slots=True)
class TemporaryRequirements:
    """Whole-program expression-pool and separate compiler-cache demand."""

    expression_temporaries: int
    compiler_caches: int

    @property
    def total_bytes(self) -> int:
        return self.expression_temporaries + self.compiler_caches


def is_side_effect_free_value(value: ResolvedValue) -> bool:
    """Return whether reordering reads inside ``value`` is semantically inert."""

    if isinstance(value, (ImmediateValue, VariableValue)):
        return True
    if isinstance(value, ResolvedRecordField):
        return value.index is None or is_side_effect_free_value(value.index)
    if isinstance(value, ResolvedArrayElement):
        return is_side_effect_free_value(value.index)
    if isinstance(value, (ResolvedUnaryExpression, ResolvedBooleanNotExpression)):
        return is_side_effect_free_value(value.operand)
    if isinstance(
        value,
        (
            ResolvedBinaryExpression,
            ResolvedComparisonExpression,
            ResolvedBooleanBinaryExpression,
        ),
    ):
        return is_side_effect_free_value(value.left) and is_side_effect_free_value(
            value.right
        )
    if isinstance(value, ResolvedBuiltinCall):
        return False
    return False


def can_use_direct_rhs_operand(left: ResolvedValue, right: ResolvedValue) -> bool:
    """Return whether ca65 can consume ``right`` without temporary staging.

    Constants are independent of evaluation order. A variable is also safe when
    evaluating the left side cannot perform a runtime call that might make the
    original right-first read order observable.
    """

    if isinstance(right, ImmediateValue):
        return True
    direct_memory = isinstance(right, VariableValue) or (
        isinstance(right, ResolvedArrayElement)
        and isinstance(right.index, ImmediateValue)
    ) or (
        isinstance(right, ResolvedRecordField)
        and (right.index is None or isinstance(right.index, ImmediateValue))
    )
    return direct_memory and is_side_effect_free_value(left)


def analyze_expression_temporaries(
    value: ResolvedValue,
    pool: TemporaryPool,
) -> None:
    """Replay the backend's acquire/use/release lifetime for ``value``."""

    if isinstance(value, (ResolvedBinaryExpression, ResolvedComparisonExpression)):
        if can_use_direct_rhs_operand(value.left, value.right):
            analyze_expression_temporaries(value.left, pool)
            return
        # The right result is only leased after its own evaluation completes.
        analyze_expression_temporaries(value.right, pool)
        with pool.acquire():
            analyze_expression_temporaries(value.left, pool)
        return
    if isinstance(value, (ResolvedUnaryExpression, ResolvedBooleanNotExpression)):
        analyze_expression_temporaries(value.operand, pool)
        return
    if isinstance(value, ResolvedBooleanBinaryExpression):
        # Short-circuit branches evaluate only one operand at a time.
        analyze_expression_temporaries(value.left, pool)
        analyze_expression_temporaries(value.right, pool)
        return
    if isinstance(value, ResolvedBuiltinCall):
        # Arguments are evaluated sequentially. Existing builtins stage values
        # in runtime bytes or on the hardware stack, outside this ZP pool.
        with pool.call_scope():
            for argument in value.arguments:
                analyze_expression_temporaries(argument, pool)
        return
    if isinstance(value, ResolvedArrayElement):
        analyze_expression_temporaries(value.index, pool)
        return
    if isinstance(value, ResolvedRecordField) and value.index is not None:
        analyze_expression_temporaries(value.index, pool)


def expression_temporary_requirement(value: ResolvedValue) -> int:
    """Return the actual maximum live expression slots required by ``value``."""

    pool = TemporaryPool()
    analyze_expression_temporaries(value, pool)
    pool.assert_all_released()
    return pool.max_live


def analyze_program_temporaries(program: ResolvedProgram) -> TemporaryRequirements:
    """Calculate exact expression-pool demand and independent loop caches."""

    pool = TemporaryPool()
    for statement in program.statements:
        _analyze_statement_temporaries(statement, pool)
    for procedure in program.procedures:
        for statement in procedure.body:
            _analyze_statement_temporaries(statement, pool)
    pool.assert_all_released()

    compiler_caches = sum(
        _count_for_statements(statement) for statement in program.statements
    ) + sum(
        _count_for_statements(statement)
        for procedure in program.procedures
        for statement in procedure.body
    )
    return TemporaryRequirements(pool.max_live, compiler_caches)


def _analyze_statement_temporaries(
    statement: ResolvedStatement,
    pool: TemporaryPool,
) -> None:
    if isinstance(statement, ResolvedRecordFieldAssignment):
        if statement.index is not None:
            analyze_expression_temporaries(statement.index, pool)
        analyze_expression_temporaries(statement.value, pool)
        return
    if isinstance(statement, ResolvedArrayElementAssignment):
        analyze_expression_temporaries(statement.index, pool)
        analyze_expression_temporaries(statement.value, pool)
        return
    if isinstance(statement, ResolvedAssignment):
        analyze_expression_temporaries(statement.value, pool)
        return
    if isinstance(statement, ResolvedBuiltinCall):
        with pool.call_scope():
            for argument in statement.arguments:
                analyze_expression_temporaries(argument, pool)
        return
    if isinstance(statement, (ResolvedIncrementStatement, ResolvedDecrementStatement)):
        if statement.amount is None:
            return
        if (
            isinstance(statement, ResolvedDecrementStatement)
            and not can_use_direct_rhs_operand(
                VariableValue(statement.target), statement.amount
            )
        ):
            analyze_expression_temporaries(statement.amount, pool)
            with pool.acquire():
                pass
            return
        analyze_expression_temporaries(statement.amount, pool)
        return
    if isinstance(statement, ResolvedIfStatement):
        analyze_expression_temporaries(statement.condition, pool)
        for item in statement.then_branch:
            _analyze_statement_temporaries(item, pool)
        if statement.else_branch is not None:
            for item in statement.else_branch:
                _analyze_statement_temporaries(item, pool)
        return
    if isinstance(statement, (ResolvedWhileStatement, ResolvedRepeatStatement)):
        analyze_expression_temporaries(statement.condition, pool)
        for item in statement.body:
            _analyze_statement_temporaries(item, pool)
        return
    if isinstance(statement, ResolvedForStatement):
        analyze_expression_temporaries(statement.initial, pool)
        analyze_expression_temporaries(statement.final, pool)
        for item in statement.body:
            _analyze_statement_temporaries(item, pool)
        return
    if isinstance(statement, ResolvedProcedureCall):
        with pool.call_scope():
            for argument in statement.arguments:
                analyze_expression_temporaries(argument.value, pool)


def _count_for_statements(statement: ResolvedStatement) -> int:
    if isinstance(statement, ResolvedForStatement):
        return 1 + sum(_count_for_statements(item) for item in statement.body)
    if isinstance(statement, ResolvedIfStatement):
        return sum(
            _count_for_statements(item) for item in statement.then_branch
        ) + sum(
            _count_for_statements(item)
            for item in statement.else_branch or ()
        )
    if isinstance(statement, (ResolvedWhileStatement, ResolvedRepeatStatement)):
        return sum(_count_for_statements(item) for item in statement.body)
    return 0
