    sta expression_temporary_0
    jsr function_Middle       ; result returned in A
    sbc expression_temporary_0
; Function: Leaf
function_Leaf:
    sta expression_temporary_2
    sbc expression_temporary_2
; Function: Middle
function_Middle:
    sta expression_temporary_1
    jsr function_Leaf       ; result returned in A
    sbc expression_temporary_1
