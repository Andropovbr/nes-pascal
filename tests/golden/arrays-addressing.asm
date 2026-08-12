; Source: Index := value
    lda #$01
    sta variable_Index

; Source: Values[constant] := value
    lda #$10
    sta variable_Values

; Source: Values[index] := value
; evaluate index before value; preserve it on hardware stack
    lda variable_Index
    pha
    lda #$20
    tay                     ; preserve assigned value
    pla
    tax                     ; native array index
    tya
    sta variable_Values,x

; Source: Result := value
    lda variable_Values
    sta variable_Result

; Source: Result := value
    ; array element: native variable index
    lda variable_Index
    tax
    lda variable_Values,x
    sta variable_Result

; Source: Values[constant] := value
    ; binary +: direct right operand
    ; array element: native variable index
    lda variable_Index
    tax
    lda variable_Values,x
    clc
    adc #$01
    sta variable_Values + 2

; Source: Flags[constant] := value
    lda #$01              ; true
    sta variable_Flags

; Source: Flags[index] := value
; evaluate index before value; preserve it on hardware stack
    lda variable_Index
    pha
    lda #$00              ; false
    tay                     ; preserve assigned value
    pla
    tax                     ; native array index
    tya
    sta variable_Flags,x

; Source: Enabled := value
    lda variable_Flags
    sta variable_Enabled

; Source: Enabled := value
    ; array element: native variable index
    lda variable_Index
    tax
    lda variable_Flags,x
    sta variable_Enabled

; Source: Result := value
    ; binary +: direct right operand
    lda variable_Values + 1
    clc
    adc variable_Values + 2
    sta variable_Result

; Source: if condition then
    ; array element: native variable index
    lda variable_Index
    tax
    lda variable_Flags,x
    bne @if_then_0
    jmp @if_end_1       ; long-branch-safe false path
@if_then_0:

; Source: Result := value
    ; binary +: direct right operand
    lda variable_Result
    clc
    adc #$01
    sta variable_Result
@if_end_1:

; Source: if condition then
    ; comparison =: direct right operand
    ; array element: native variable index
    lda variable_Index
    tax
    lda variable_Values,x
    cmp #$20
    beq @if_then_2
    jmp @if_end_3       ; long-branch-safe false path
@if_then_2:

; Source: Enabled := value
    lda #$01              ; true
    sta variable_Enabled
@if_end_3:
