"""Small, shared analyses for local ca65 expression lowering decisions."""

from __future__ import annotations

from .ast import (
    ImmediateValue,
    ResolvedArrayElement,
    ResolvedBinaryExpression,
    ResolvedBooleanBinaryExpression,
    ResolvedBooleanNotExpression,
    ResolvedBuiltinCall,
    ResolvedComparisonExpression,
    ResolvedUnaryExpression,
    ResolvedValue,
    VariableValue,
)


def is_side_effect_free_value(value: ResolvedValue) -> bool:
    """Return whether reordering reads inside ``value`` is semantically inert."""

    if isinstance(value, (ImmediateValue, VariableValue)):
        return True
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
    )
    return direct_memory and is_side_effect_free_value(left)


def expression_temporary_symbol_count(
    value: ResolvedValue,
    depth: int = 0,
) -> int:
    """Return the exclusive temporary-symbol depth required by code generation."""

    if isinstance(value, (ResolvedBinaryExpression, ResolvedComparisonExpression)):
        if can_use_direct_rhs_operand(value.left, value.right):
            return expression_temporary_symbol_count(value.left, depth)
        return max(
            depth + 1,
            expression_temporary_symbol_count(value.right, depth + 1),
            expression_temporary_symbol_count(value.left, depth + 1),
        )
    if isinstance(value, (ResolvedUnaryExpression, ResolvedBooleanNotExpression)):
        return expression_temporary_symbol_count(value.operand, depth)
    if isinstance(value, ResolvedBooleanBinaryExpression):
        return max(
            expression_temporary_symbol_count(value.left, depth),
            expression_temporary_symbol_count(value.right, depth),
        )
    if isinstance(value, ResolvedBuiltinCall):
        return max(
            (
                expression_temporary_symbol_count(argument, depth)
                for argument in value.arguments
            ),
            default=depth,
        )
    if isinstance(value, ResolvedArrayElement):
        return expression_temporary_symbol_count(value.index, depth)
    return depth
