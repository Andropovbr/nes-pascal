procedure_Update:

; Source: if condition then
    ; comparison =: direct right operand
    lda variable_State
    cmp #$00
    beq @if_then_35
    jmp @if_else_37       ; long-branch-safe false path
@if_then_35:

; Source: UpdateTitle
    jsr procedure_UpdateTitle
    jmp @if_end_36
@if_else_37:

; Source: if condition then
    ; comparison =: direct right operand
    lda variable_State
    cmp #$01
    beq @if_then_38
    jmp @if_else_40       ; long-branch-safe false path
@if_then_38:

; Source: UpdatePlaying
    jsr procedure_UpdatePlaying
    jmp @if_end_39
@if_else_40:

; Source: if condition then
    ; comparison =: direct right operand
    lda variable_State
    cmp #$02
    beq @if_then_41
    jmp @if_else_43       ; long-branch-safe false path
@if_then_41:

; Source: UpdatePaused
    jsr procedure_UpdatePaused
    jmp @if_end_42
@if_else_43:

; Source: if condition then
    ; comparison =: direct right operand
    lda variable_State
    cmp #$03
    beq @if_then_44
    jmp @if_end_45       ; long-branch-safe false path
@if_then_44:

; Source: UpdateGameOver
    jsr procedure_UpdateGameOver
@if_end_45:
@if_end_42:
@if_end_39:
@if_end_36:
    rts
