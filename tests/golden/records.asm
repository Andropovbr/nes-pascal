; Source: Index := value
    lda #$01
    sta variable_Index

; Source: Player.X := value
    lda #$20
    sta variable_Player

; Source: Player.Y := value
    lda variable_Player
    sta variable_Player + 1

; Source: Player.Active := value
    lda #$01              ; true
    sta variable_Player + 2

; Source: Player.State := value
    lda #$01
    sta variable_Player + 3

; Source: if condition then
    lda variable_Player + 2
    bne @if_then_0
    jmp @if_end_1       ; long-branch-safe false path
@if_then_0:

; Source: Counter := value
    lda variable_Player
    sta variable_Counter
@if_end_1:

; Source: if condition then
    ; comparison =: direct right operand
    lda variable_Player + 3
    cmp #$01
    beq @if_then_2
    jmp @if_end_3       ; long-branch-safe false path
@if_then_2:

; Source: Counter := value
    lda variable_Player + 1
    sta variable_Counter
@if_end_3:

; Source: Entities[constant].X := value
    lda #$40
    sta variable_Entities + 8

; Source: Counter := value
    lda variable_Entities + 8
    sta variable_Counter

; Source: Entities[index].Y := value
; evaluate index and scale to byte offset before value
    lda variable_Index
    asl a                   ; scale record index
    asl a                   ; scale record index
    clc
    adc #$01          ; record field offset
    pha                     ; preserve scaled field offset
    lda variable_Counter
    tay                     ; preserve assigned value
    pla
    tax                     ; scaled record field offset
    tya
    sta variable_Entities,x

; Source: Counter := value
    ; record array field: scale index by 4
    lda variable_Index
    asl a                   ; scale record index
    asl a                   ; scale record index
    clc
    adc #$01          ; record field offset
    tax                     ; scaled record field offset
    lda variable_Entities,x
    sta variable_Counter
