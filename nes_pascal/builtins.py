"""Static registry for ordinary ``nes.*`` builtins.

The registry is compiler metadata only.  It gives every ordinary builtin a
stable identity shared by semantic analysis, memory-feature discovery, and
the ca65 backend; it does not add runtime dispatch to generated ROMs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from types import MappingProxyType

from .ast import BuiltInType
from .diagnostics import DiagnosticCode


class BuiltinId(Enum):
    SET_BACKGROUND_COLOR = auto()
    SET_BACKGROUND_PALETTE = auto()
    SET_SPRITE_PALETTE = auto()
    SET_BACKGROUND_PALETTE_COLOR = auto()
    SET_SPRITE_PALETTE_COLOR = auto()
    SET_TILE = auto()
    GET_TILE = auto()
    SET_ATTRIBUTE = auto()
    CLEAR_BACKGROUND_UPDATES = auto()
    BACKGROUND_UPDATES_OVERFLOWED = auto()
    CLEAR_BACKGROUND_UPDATE_OVERFLOW = auto()
    SET_SCROLL = auto()
    WAIT_FRAME = auto()
    SET_SPRITE_ZERO = auto()
    SPRITE_CREATE = auto()
    SPRITE_SET_POSITION = auto()
    SPRITE_SET_X = auto()
    SPRITE_SET_Y = auto()
    SPRITE_SET_TILE = auto()
    SPRITE_SET_PALETTE = auto()
    SPRITE_SET_ATTRIBUTES = auto()
    SPRITE_HIDE = auto()
    SPRITE_SHOW = auto()
    SPRITE_SET_FLIP_HORIZONTAL = auto()
    SPRITE_SET_FLIP_VERTICAL = auto()
    SPRITE_SET_BEHIND_BACKGROUND = auto()
    METASPRITE_CREATE = auto()
    METASPRITE_SET_POSITION = auto()
    METASPRITE_SET_FRAME = auto()
    METASPRITE_SET_ANIMATION = auto()
    METASPRITE_RESTART_ANIMATION = auto()
    METASPRITE_HIDE = auto()
    METASPRITE_SHOW = auto()
    METASPRITE_SET_FLIP_HORIZONTAL = auto()
    METASPRITE_SET_FLIP_VERTICAL = auto()
    METASPRITE_ANIMATION_FINISHED = auto()
    CONTROLLER_DOWN = auto()
    CONTROLLER_PRESSED = auto()
    CONTROLLER_RELEASED = auto()


class BuiltinKind(Enum):
    STATEMENT = auto()
    VALUE = auto()


class PaletteKind(Enum):
    BACKGROUND = "background"
    SPRITE = "sprite"


class SemanticHook(Enum):
    DEFAULT = auto()
    PALETTE = auto()
    PALETTE_COLOR = auto()
    TILE_COORDINATES = auto()
    ATTRIBUTE_COORDINATES = auto()
    CONTROLLER_QUERY = auto()
    SPRITE_CREATE = auto()
    SPRITE_OPERATION = auto()
    METASPRITE_CREATE = auto()
    METASPRITE_OPERATION = auto()


class BackendEmitter(Enum):
    SET_BACKGROUND_COLOR = auto()
    SET_PALETTE = auto()
    SET_PALETTE_COLOR = auto()
    SET_TILE = auto()
    GET_TILE = auto()
    SET_ATTRIBUTE = auto()
    CLEAR_BACKGROUND_UPDATES = auto()
    BACKGROUND_UPDATES_OVERFLOWED = auto()
    CLEAR_BACKGROUND_UPDATE_OVERFLOW = auto()
    SET_SCROLL = auto()
    WAIT_FRAME = auto()
    SET_SPRITE_ZERO = auto()
    SPRITE_CREATE = auto()
    SPRITE_OPERATION = auto()
    METASPRITE_CREATE = auto()
    METASPRITE_OPERATION = auto()
    METASPRITE_ANIMATION_FINISHED = auto()
    CONTROLLER_QUERY = auto()


class RuntimeFeature(Enum):
    CONTROLLER_QUERY = auto()
    PALETTE_QUEUE = auto()
    LEGACY_SPRITE_ZERO = auto()
    SPRITE_API = auto()
    SPRITE_SET_POSITION = auto()
    METASPRITE_API = auto()
    METASPRITE_ANIMATION = auto()
    BACKGROUND_SET_TILE = auto()
    BACKGROUND_GET_TILE = auto()
    BACKGROUND_SET_ATTRIBUTE = auto()
    BACKGROUND_CLEAR_UPDATES = auto()
    BACKGROUND_INSPECT_OVERFLOW = auto()
    BACKGROUND_CLEAR_OVERFLOW = auto()
    SCROLL = auto()


@dataclass(frozen=True, slots=True)
class BuiltinDescriptor:
    id: BuiltinId
    public_name: str
    kind: BuiltinKind
    parameter_types: tuple[BuiltInType, ...]
    return_type: BuiltInType | None
    semantic_hook: SemanticHook
    emitter: BackendEmitter
    runtime_features: tuple[RuntimeFeature, ...] = ()
    queued_runtime_features: tuple[RuntimeFeature, ...] = ()
    argument_count_diagnostic: DiagnosticCode = (
        DiagnosticCode.INVALID_BUILTIN_ARGUMENT_COUNT
    )
    argument_count_suggestion: str = "Pass the documented arguments."
    bare_statement: bool = False


def _statement(
    id: BuiltinId,
    public_name: str,
    parameters: tuple[BuiltInType, ...],
    emitter: BackendEmitter,
    *,
    hook: SemanticHook = SemanticHook.DEFAULT,
    features: tuple[RuntimeFeature, ...] = (),
    queued_features: tuple[RuntimeFeature, ...] = (),
    count_code: DiagnosticCode = DiagnosticCode.INVALID_BUILTIN_ARGUMENT_COUNT,
    count_suggestion: str = "Pass the documented arguments.",
    bare: bool = False,
) -> BuiltinDescriptor:
    return BuiltinDescriptor(
        id,
        public_name,
        BuiltinKind.STATEMENT,
        parameters,
        None,
        hook,
        emitter,
        features,
        queued_features,
        count_code,
        count_suggestion,
        bare,
    )


def _value(
    id: BuiltinId,
    public_name: str,
    parameters: tuple[BuiltInType, ...],
    return_type: BuiltInType,
    emitter: BackendEmitter,
    *,
    hook: SemanticHook = SemanticHook.DEFAULT,
    features: tuple[RuntimeFeature, ...] = (),
    count_code: DiagnosticCode = DiagnosticCode.INVALID_BUILTIN_ARGUMENT_COUNT,
    count_suggestion: str = "Pass the documented arguments.",
) -> BuiltinDescriptor:
    return BuiltinDescriptor(
        id,
        public_name,
        BuiltinKind.VALUE,
        parameters,
        return_type,
        hook,
        emitter,
        features,
        (),
        count_code,
        count_suggestion,
    )


_SPRITE = BuiltInType.SPRITE
_METASPRITE = BuiltInType.METASPRITE
_BYTE = BuiltInType.BYTE
_BOOLEAN = BuiltInType.BOOLEAN
_COLOR = BuiltInType.NES_COLOR

_DESCRIPTORS = (
    _statement(BuiltinId.SET_BACKGROUND_COLOR, "nes.set_background_color", (_COLOR,), BackendEmitter.SET_BACKGROUND_COLOR, queued_features=(RuntimeFeature.PALETTE_QUEUE,), count_suggestion="Pass exactly one nes_color value."),
    _statement(BuiltinId.SET_BACKGROUND_PALETTE, "nes.set_background_palette", (_BYTE, _COLOR, _COLOR, _COLOR, _COLOR), BackendEmitter.SET_PALETTE, hook=SemanticHook.PALETTE, queued_features=(RuntimeFeature.PALETTE_QUEUE,), count_code=DiagnosticCode.INVALID_PALETTE_ARGUMENT_COUNT, count_suggestion="Pass a palette index followed by four nes_color values."),
    _statement(BuiltinId.SET_SPRITE_PALETTE, "nes.set_sprite_palette", (_BYTE, _COLOR, _COLOR, _COLOR, _COLOR), BackendEmitter.SET_PALETTE, hook=SemanticHook.PALETTE, queued_features=(RuntimeFeature.PALETTE_QUEUE,), count_code=DiagnosticCode.INVALID_PALETTE_ARGUMENT_COUNT, count_suggestion="Pass a palette index followed by four nes_color values."),
    _statement(BuiltinId.SET_BACKGROUND_PALETTE_COLOR, "nes.set_background_palette_color", (_BYTE, _BYTE, _COLOR), BackendEmitter.SET_PALETTE_COLOR, hook=SemanticHook.PALETTE_COLOR, queued_features=(RuntimeFeature.PALETTE_QUEUE,), count_code=DiagnosticCode.INVALID_PALETTE_ARGUMENT_COUNT, count_suggestion="Pass palette index, color index, and nes_color value."),
    _statement(BuiltinId.SET_SPRITE_PALETTE_COLOR, "nes.set_sprite_palette_color", (_BYTE, _BYTE, _COLOR), BackendEmitter.SET_PALETTE_COLOR, hook=SemanticHook.PALETTE_COLOR, queued_features=(RuntimeFeature.PALETTE_QUEUE,), count_code=DiagnosticCode.INVALID_PALETTE_ARGUMENT_COUNT, count_suggestion="Pass palette index, color index, and nes_color value."),
    _statement(BuiltinId.SET_TILE, "nes.set_tile", (_BYTE, _BYTE, _BYTE), BackendEmitter.SET_TILE, hook=SemanticHook.TILE_COORDINATES, features=(RuntimeFeature.BACKGROUND_SET_TILE,), count_code=DiagnosticCode.INVALID_SET_TILE_ARGUMENT_COUNT, count_suggestion="Pass x, y, and tile as byte values."),
    _value(BuiltinId.GET_TILE, "nes.get_tile", (_BYTE, _BYTE), _BYTE, BackendEmitter.GET_TILE, hook=SemanticHook.TILE_COORDINATES, features=(RuntimeFeature.BACKGROUND_GET_TILE,), count_code=DiagnosticCode.INVALID_GET_TILE_ARGUMENT_COUNT, count_suggestion="Pass x and y as byte values."),
    _statement(BuiltinId.SET_ATTRIBUTE, "nes.set_attribute", (_BYTE, _BYTE, _BYTE), BackendEmitter.SET_ATTRIBUTE, hook=SemanticHook.ATTRIBUTE_COORDINATES, features=(RuntimeFeature.BACKGROUND_SET_ATTRIBUTE,), count_code=DiagnosticCode.INVALID_SET_ATTRIBUTE_ARGUMENT_COUNT, count_suggestion="Pass attribute X, attribute Y, and value as byte values."),
    _statement(BuiltinId.CLEAR_BACKGROUND_UPDATES, "nes.clear_background_updates", (), BackendEmitter.CLEAR_BACKGROUND_UPDATES, features=(RuntimeFeature.BACKGROUND_CLEAR_UPDATES,), count_code=DiagnosticCode.INVALID_CLEAR_BACKGROUND_UPDATES_ARGUMENT_COUNT, count_suggestion="Call nes.clear_background_updates() without arguments."),
    _value(BuiltinId.BACKGROUND_UPDATES_OVERFLOWED, "nes.background_updates_overflowed", (), _BOOLEAN, BackendEmitter.BACKGROUND_UPDATES_OVERFLOWED, features=(RuntimeFeature.BACKGROUND_INSPECT_OVERFLOW,), count_code=DiagnosticCode.INVALID_BACKGROUND_OVERFLOW_QUERY_ARGUMENT_COUNT, count_suggestion="Call nes.background_updates_overflowed() without arguments."),
    _statement(BuiltinId.CLEAR_BACKGROUND_UPDATE_OVERFLOW, "nes.clear_background_update_overflow", (), BackendEmitter.CLEAR_BACKGROUND_UPDATE_OVERFLOW, features=(RuntimeFeature.BACKGROUND_CLEAR_OVERFLOW,), count_code=DiagnosticCode.INVALID_BACKGROUND_OVERFLOW_CLEAR_ARGUMENT_COUNT, count_suggestion="Call nes.clear_background_update_overflow() without arguments."),
    _statement(BuiltinId.SET_SCROLL, "nes.set_scroll", (_BYTE, _BYTE), BackendEmitter.SET_SCROLL, features=(RuntimeFeature.SCROLL,), count_code=DiagnosticCode.INVALID_SET_SCROLL_ARGUMENT_COUNT, count_suggestion="Pass horizontal and vertical scroll as byte values."),
    _statement(BuiltinId.WAIT_FRAME, "nes.wait_frame", (), BackendEmitter.WAIT_FRAME, bare=True, count_suggestion="Write nes.wait_frame; without arguments."),
    _statement(BuiltinId.SET_SPRITE_ZERO, "nes.set_sprite_zero", (_BYTE, _BYTE, _BYTE, _BYTE), BackendEmitter.SET_SPRITE_ZERO, features=(RuntimeFeature.LEGACY_SPRITE_ZERO,), count_code=DiagnosticCode.INVALID_SPRITE_ZERO_ARGUMENT_COUNT, count_suggestion="Pass x, y, tile, and attributes as byte values."),
    _value(BuiltinId.SPRITE_CREATE, "nes.sprite_create", (), _SPRITE, BackendEmitter.SPRITE_CREATE, hook=SemanticHook.SPRITE_CREATE, features=(RuntimeFeature.SPRITE_API,), count_code=DiagnosticCode.INVALID_SPRITE_CREATE_ARGUMENT_COUNT, count_suggestion="Call nes.sprite_create() without arguments."),
    _statement(BuiltinId.SPRITE_SET_POSITION, "nes.sprite_set_position", (_SPRITE, _BYTE, _BYTE), BackendEmitter.SPRITE_OPERATION, hook=SemanticHook.SPRITE_OPERATION, features=(RuntimeFeature.SPRITE_API, RuntimeFeature.SPRITE_SET_POSITION), count_code=DiagnosticCode.INVALID_SPRITE_ARGUMENT_COUNT),
    _statement(BuiltinId.SPRITE_SET_X, "nes.sprite_set_x", (_SPRITE, _BYTE), BackendEmitter.SPRITE_OPERATION, hook=SemanticHook.SPRITE_OPERATION, features=(RuntimeFeature.SPRITE_API,), count_code=DiagnosticCode.INVALID_SPRITE_ARGUMENT_COUNT),
    _statement(BuiltinId.SPRITE_SET_Y, "nes.sprite_set_y", (_SPRITE, _BYTE), BackendEmitter.SPRITE_OPERATION, hook=SemanticHook.SPRITE_OPERATION, features=(RuntimeFeature.SPRITE_API,), count_code=DiagnosticCode.INVALID_SPRITE_ARGUMENT_COUNT),
    _statement(BuiltinId.SPRITE_SET_TILE, "nes.sprite_set_tile", (_SPRITE, _BYTE), BackendEmitter.SPRITE_OPERATION, hook=SemanticHook.SPRITE_OPERATION, features=(RuntimeFeature.SPRITE_API,), count_code=DiagnosticCode.INVALID_SPRITE_ARGUMENT_COUNT),
    _statement(BuiltinId.SPRITE_SET_PALETTE, "nes.sprite_set_palette", (_SPRITE, _BYTE), BackendEmitter.SPRITE_OPERATION, hook=SemanticHook.SPRITE_OPERATION, features=(RuntimeFeature.SPRITE_API,), count_code=DiagnosticCode.INVALID_SPRITE_ARGUMENT_COUNT),
    _statement(BuiltinId.SPRITE_SET_ATTRIBUTES, "nes.sprite_set_attributes", (_SPRITE, _BYTE), BackendEmitter.SPRITE_OPERATION, hook=SemanticHook.SPRITE_OPERATION, features=(RuntimeFeature.SPRITE_API,), count_code=DiagnosticCode.INVALID_SPRITE_ARGUMENT_COUNT),
    _statement(BuiltinId.SPRITE_HIDE, "nes.sprite_hide", (_SPRITE,), BackendEmitter.SPRITE_OPERATION, hook=SemanticHook.SPRITE_OPERATION, features=(RuntimeFeature.SPRITE_API,), count_code=DiagnosticCode.INVALID_SPRITE_ARGUMENT_COUNT),
    _statement(BuiltinId.SPRITE_SHOW, "nes.sprite_show", (_SPRITE,), BackendEmitter.SPRITE_OPERATION, hook=SemanticHook.SPRITE_OPERATION, features=(RuntimeFeature.SPRITE_API,), count_code=DiagnosticCode.INVALID_SPRITE_ARGUMENT_COUNT),
    _statement(BuiltinId.SPRITE_SET_FLIP_HORIZONTAL, "nes.sprite_set_flip_horizontal", (_SPRITE, _BOOLEAN), BackendEmitter.SPRITE_OPERATION, hook=SemanticHook.SPRITE_OPERATION, features=(RuntimeFeature.SPRITE_API,), count_code=DiagnosticCode.INVALID_SPRITE_ARGUMENT_COUNT),
    _statement(BuiltinId.SPRITE_SET_FLIP_VERTICAL, "nes.sprite_set_flip_vertical", (_SPRITE, _BOOLEAN), BackendEmitter.SPRITE_OPERATION, hook=SemanticHook.SPRITE_OPERATION, features=(RuntimeFeature.SPRITE_API,), count_code=DiagnosticCode.INVALID_SPRITE_ARGUMENT_COUNT),
    _statement(BuiltinId.SPRITE_SET_BEHIND_BACKGROUND, "nes.sprite_set_behind_background", (_SPRITE, _BOOLEAN), BackendEmitter.SPRITE_OPERATION, hook=SemanticHook.SPRITE_OPERATION, features=(RuntimeFeature.SPRITE_API,), count_code=DiagnosticCode.INVALID_SPRITE_ARGUMENT_COUNT),
    _value(BuiltinId.METASPRITE_CREATE, "nes.metasprite_create", (BuiltInType.METASPRITE_FRAME,), _METASPRITE, BackendEmitter.METASPRITE_CREATE, hook=SemanticHook.METASPRITE_CREATE, features=(RuntimeFeature.METASPRITE_API,), count_code=DiagnosticCode.INVALID_METASPRITE_CREATE, count_suggestion="Pass an imported frame such as player.idle_0."),
    _statement(BuiltinId.METASPRITE_SET_POSITION, "nes.metasprite_set_position", (_METASPRITE, _BYTE, _BYTE), BackendEmitter.METASPRITE_OPERATION, hook=SemanticHook.METASPRITE_OPERATION, features=(RuntimeFeature.METASPRITE_API,), count_code=DiagnosticCode.INVALID_METASPRITE_ARGUMENT_COUNT),
    _statement(BuiltinId.METASPRITE_SET_FRAME, "nes.metasprite_set_frame", (_METASPRITE, BuiltInType.METASPRITE_FRAME), BackendEmitter.METASPRITE_OPERATION, hook=SemanticHook.METASPRITE_OPERATION, features=(RuntimeFeature.METASPRITE_API,), count_code=DiagnosticCode.INVALID_METASPRITE_ARGUMENT_COUNT),
    _statement(BuiltinId.METASPRITE_SET_ANIMATION, "nes.metasprite_set_animation", (_METASPRITE, BuiltInType.METASPRITE_ANIMATION), BackendEmitter.METASPRITE_OPERATION, hook=SemanticHook.METASPRITE_OPERATION, features=(RuntimeFeature.METASPRITE_API, RuntimeFeature.METASPRITE_ANIMATION), count_code=DiagnosticCode.INVALID_METASPRITE_ARGUMENT_COUNT),
    _statement(BuiltinId.METASPRITE_RESTART_ANIMATION, "nes.metasprite_restart_animation", (_METASPRITE,), BackendEmitter.METASPRITE_OPERATION, hook=SemanticHook.METASPRITE_OPERATION, features=(RuntimeFeature.METASPRITE_API, RuntimeFeature.METASPRITE_ANIMATION), count_code=DiagnosticCode.INVALID_METASPRITE_ARGUMENT_COUNT),
    _statement(BuiltinId.METASPRITE_HIDE, "nes.metasprite_hide", (_METASPRITE,), BackendEmitter.METASPRITE_OPERATION, hook=SemanticHook.METASPRITE_OPERATION, features=(RuntimeFeature.METASPRITE_API,), count_code=DiagnosticCode.INVALID_METASPRITE_ARGUMENT_COUNT),
    _statement(BuiltinId.METASPRITE_SHOW, "nes.metasprite_show", (_METASPRITE,), BackendEmitter.METASPRITE_OPERATION, hook=SemanticHook.METASPRITE_OPERATION, features=(RuntimeFeature.METASPRITE_API,), count_code=DiagnosticCode.INVALID_METASPRITE_ARGUMENT_COUNT),
    _statement(BuiltinId.METASPRITE_SET_FLIP_HORIZONTAL, "nes.metasprite_set_flip_horizontal", (_METASPRITE, _BOOLEAN), BackendEmitter.METASPRITE_OPERATION, hook=SemanticHook.METASPRITE_OPERATION, features=(RuntimeFeature.METASPRITE_API,), count_code=DiagnosticCode.INVALID_METASPRITE_ARGUMENT_COUNT),
    _statement(BuiltinId.METASPRITE_SET_FLIP_VERTICAL, "nes.metasprite_set_flip_vertical", (_METASPRITE, _BOOLEAN), BackendEmitter.METASPRITE_OPERATION, hook=SemanticHook.METASPRITE_OPERATION, features=(RuntimeFeature.METASPRITE_API,), count_code=DiagnosticCode.INVALID_METASPRITE_ARGUMENT_COUNT),
    _value(BuiltinId.METASPRITE_ANIMATION_FINISHED, "nes.metasprite_animation_finished", (_METASPRITE,), _BOOLEAN, BackendEmitter.METASPRITE_ANIMATION_FINISHED, features=(RuntimeFeature.METASPRITE_API, RuntimeFeature.METASPRITE_ANIMATION), count_code=DiagnosticCode.INVALID_METASPRITE_ARGUMENT_COUNT, count_suggestion="Pass the metasprite instance to query."),
    _value(BuiltinId.CONTROLLER_DOWN, "nes.controller_down", (_BYTE, _BYTE), _BOOLEAN, BackendEmitter.CONTROLLER_QUERY, hook=SemanticHook.CONTROLLER_QUERY, features=(RuntimeFeature.CONTROLLER_QUERY,), count_code=DiagnosticCode.INVALID_CONTROLLER_ARGUMENT_COUNT),
    _value(BuiltinId.CONTROLLER_PRESSED, "nes.controller_pressed", (_BYTE, _BYTE), _BOOLEAN, BackendEmitter.CONTROLLER_QUERY, hook=SemanticHook.CONTROLLER_QUERY, features=(RuntimeFeature.CONTROLLER_QUERY,), count_code=DiagnosticCode.INVALID_CONTROLLER_ARGUMENT_COUNT),
    _value(BuiltinId.CONTROLLER_RELEASED, "nes.controller_released", (_BYTE, _BYTE), _BOOLEAN, BackendEmitter.CONTROLLER_QUERY, hook=SemanticHook.CONTROLLER_QUERY, features=(RuntimeFeature.CONTROLLER_QUERY,), count_code=DiagnosticCode.INVALID_CONTROLLER_ARGUMENT_COUNT),
)


def _build_registry(
    descriptors: tuple[BuiltinDescriptor, ...],
) -> tuple[
    MappingProxyType[str, BuiltinDescriptor],
    MappingProxyType[BuiltinId, BuiltinDescriptor],
]:
    by_name: dict[str, BuiltinDescriptor] = {}
    by_id: dict[BuiltinId, BuiltinDescriptor] = {}
    for descriptor in descriptors:
        if descriptor.public_name in by_name:
            raise ValueError(f"duplicate builtin name: {descriptor.public_name}")
        if descriptor.id in by_id:
            raise ValueError(f"duplicate builtin identity: {descriptor.id.name}")
        if (descriptor.return_type is None) != (
            descriptor.kind is BuiltinKind.STATEMENT
        ):
            raise ValueError(f"invalid builtin result metadata: {descriptor.public_name}")
        by_name[descriptor.public_name] = descriptor
        by_id[descriptor.id] = descriptor
    return MappingProxyType(by_name), MappingProxyType(by_id)


BUILTINS_BY_NAME, BUILTINS_BY_ID = _build_registry(_DESCRIPTORS)


def builtin_by_name(public_name: str) -> BuiltinDescriptor | None:
    return BUILTINS_BY_NAME.get(public_name.lower())


def builtin_by_id(builtin_id: BuiltinId) -> BuiltinDescriptor:
    return BUILTINS_BY_ID[builtin_id]
