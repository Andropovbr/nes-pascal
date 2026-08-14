"""Shared analyses and scoped storage for ca65 expression lowering."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, fields, is_dataclass
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
    ResolvedFunctionCall,
    ResolvedFunctionResultAssignment,
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
    calls can only receive non-aliasing slots. Function lowering preserves this
    compile-time rule, so the current non-recursive callable model needs no
    runtime frame.
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
    callable_bases: tuple[tuple[str, int], ...] = ()
    max_call_depth: int = 0

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
    if isinstance(value, ResolvedFunctionCall):
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
    if isinstance(value, ResolvedFunctionCall):
        leases: list[TemporarySlot] = []
        try:
            for index, argument in enumerate(value.arguments):
                analyze_expression_temporaries(argument.value, pool)
                if any(
                    value_contains_function_call(later.value)
                    for later in value.arguments[index + 1 :]
                ):
                    leases.append(pool.acquire())
        finally:
            for lease in reversed(leases):
                lease.release()
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

    analyzer = _ProgramTemporaryAnalyzer(program)
    analyzer.analyze()

    compiler_caches = sum(
        _count_for_statements(statement) for statement in program.statements
    ) + sum(
        _count_for_statements(statement)
        for procedure in program.procedures
        for statement in procedure.body
    ) + sum(
        _count_for_statements(statement)
        for function in program.functions
        for statement in function.body
    )
    return TemporaryRequirements(
        analyzer.pool.max_live,
        compiler_caches,
        tuple(sorted(analyzer.callable_bases.items())),
        analyzer.max_call_depth,
    )


def value_contains_function_call(value: ResolvedValue) -> bool:
    """Return whether evaluating ``value`` can execute a user function."""

    if isinstance(value, ResolvedFunctionCall):
        return True
    if not is_dataclass(value):
        return False
    for field in fields(value):
        child = getattr(value, field.name)
        if isinstance(child, tuple):
            for item in child:
                nested = getattr(item, "value", item)
                if is_dataclass(nested) and value_contains_function_call(nested):
                    return True
        elif is_dataclass(child) and value_contains_function_call(child):
            return True
    return False


class _ProgramTemporaryAnalyzer:
    """Replay whole-program temporary lifetimes across the acyclic call graph."""

    def __init__(self, program: ResolvedProgram) -> None:
        self.program = program
        self.pool = TemporaryPool()
        self.callables = {
            callable_.label: callable_
            for callable_ in (*program.procedures, *program.functions)
        }
        self.callable_bases: dict[str, int] = {
            label: 0 for label in self.callables
        }
        self.max_call_depth = 0

    def analyze(self) -> None:
        self._statements(self.program.statements, 0)
        # Unreachable declarations are still emitted and must remain safe.
        for callable_ in self.callables.values():
            self._statements(callable_.body, 1)
        self.pool.assert_all_released()

    def _call(self, label: str, arguments: tuple[object, ...], depth: int) -> None:
        leases: list[TemporarySlot] = []
        try:
            for index, argument in enumerate(arguments):
                value = argument.value
                self._value(value, depth)
                if any(
                    value_contains_function_call(later.value)
                    for later in arguments[index + 1 :]
                ):
                    leases.append(self.pool.acquire())
        finally:
            for lease in reversed(leases):
                lease.release()
        self.callable_bases[label] = max(
            self.callable_bases[label], self.pool.live_count
        )
        self.max_call_depth = max(self.max_call_depth, depth + 1)
        self._statements(self.callables[label].body, depth + 1)

    def _value(self, value: ResolvedValue, depth: int) -> None:
        if isinstance(value, (ResolvedBinaryExpression, ResolvedComparisonExpression)):
            if can_use_direct_rhs_operand(value.left, value.right):
                self._value(value.left, depth)
                return
            self._value(value.right, depth)
            with self.pool.acquire():
                self._value(value.left, depth)
            return
        if isinstance(value, (ResolvedUnaryExpression, ResolvedBooleanNotExpression)):
            self._value(value.operand, depth)
            return
        if isinstance(value, ResolvedBooleanBinaryExpression):
            self._value(value.left, depth)
            self._value(value.right, depth)
            return
        if isinstance(value, ResolvedFunctionCall):
            self._call(value.label, value.arguments, depth)
            return
        if isinstance(value, ResolvedBuiltinCall):
            for argument in value.arguments:
                self._value(argument, depth)
            return
        if isinstance(value, ResolvedArrayElement):
            self._value(value.index, depth)
            return
        if isinstance(value, ResolvedRecordField) and value.index is not None:
            self._value(value.index, depth)

    def _statements(
        self, statements: tuple[ResolvedStatement, ...], depth: int
    ) -> None:
        for statement in statements:
            if isinstance(statement, ResolvedRecordFieldAssignment):
                if statement.index is not None:
                    self._value(statement.index, depth)
                self._value(statement.value, depth)
            elif isinstance(statement, ResolvedArrayElementAssignment):
                self._value(statement.index, depth)
                self._value(statement.value, depth)
            elif isinstance(
                statement,
                (ResolvedAssignment, ResolvedFunctionResultAssignment),
            ):
                self._value(statement.value, depth)
            elif isinstance(statement, ResolvedBuiltinCall):
                for argument in statement.arguments:
                    self._value(argument, depth)
            elif isinstance(
                statement, (ResolvedIncrementStatement, ResolvedDecrementStatement)
            ):
                if statement.amount is not None:
                    if (
                        isinstance(statement, ResolvedDecrementStatement)
                        and not can_use_direct_rhs_operand(
                            VariableValue(statement.target), statement.amount
                        )
                    ):
                        self._value(statement.amount, depth)
                        with self.pool.acquire():
                            pass
                    else:
                        self._value(statement.amount, depth)
            elif isinstance(statement, ResolvedIfStatement):
                self._value(statement.condition, depth)
                self._statements(statement.then_branch, depth)
                self._statements(statement.else_branch or (), depth)
            elif isinstance(statement, (ResolvedWhileStatement, ResolvedRepeatStatement)):
                self._value(statement.condition, depth)
                self._statements(statement.body, depth)
            elif isinstance(statement, ResolvedForStatement):
                self._value(statement.initial, depth)
                self._value(statement.final, depth)
                self._statements(statement.body, depth)
            elif isinstance(statement, ResolvedProcedureCall):
                self._call(statement.label, statement.arguments, depth)

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
