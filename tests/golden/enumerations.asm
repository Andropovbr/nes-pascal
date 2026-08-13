; Source: State := value
    lda #$00
    sta variable_State

; Source: Previous := value
    lda #$01
    sta variable_Previous

; Source: State := value
    lda variable_Previous
    sta variable_State

; Source: Enabled := value
    ; comparison <>: direct right operand
    lda variable_State
    cmp #$02
    bne @comparison_true_0
@comparison_false_1:
    lda #$00              ; false
    jmp @comparison_end_2
@comparison_true_0:
    lda #$01              ; true
@comparison_end_2:
    sta variable_Enabled

; Source: StoredEqual := value
    ; comparison =: direct right operand
    lda variable_State
    cmp #$01
    beq @comparison_true_3
@comparison_false_4:
    lda #$00              ; false
    jmp @comparison_end_5
@comparison_true_3:
    lda #$01              ; true
@comparison_end_5:
    sta variable_StoredEqual

; Source: if condition then
    ; comparison =: direct right operand
    lda variable_State
    cmp #$01
    beq @if_then_6
    jmp @if_end_7       ; long-branch-safe false path
@if_then_6:

; Source: State := value
    lda #$03
    sta variable_State
@if_end_7:
