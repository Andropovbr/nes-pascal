.segment "FUNCTION_RESULTS"
function_result_Identity: .res 1 ; $0204: static return storage for function Identity
function_result_Add: .res 1 ; $0205: static return storage for function Add
function_result_Equal: .res 1 ; $0206: static return storage for function Equal
    jsr function_Identity       ; result returned in A
    sta expression_temporary_0 ; preserve across later call
    jsr function_Identity       ; result returned in A
    sta expression_temporary_1 ; preserve across later call
    jsr function_Identity       ; result returned in A
    lda expression_temporary_1
    jsr function_Add       ; result returned in A
    lda expression_temporary_0
    jsr function_Add       ; result returned in A
    jsr function_Equal       ; result returned in A
    ; comparison =: evaluate right operand
    jsr function_Identity       ; result returned in A
    sta expression_temporary_0
    jsr function_Identity       ; result returned in A
    cmp expression_temporary_0
    ; boolean and: evaluate left operand
    jsr function_Equal       ; result returned in A
    jmp @boolean_false_5       ; short-circuit false
    jsr function_Equal       ; result returned in A
; Function: Identity
function_Identity:
    sta function_result_Identity
    lda function_result_Identity ; return value in A
; Function: Add
function_Add:
    sta function_result_Add
    lda function_result_Add ; return value in A
; Function: Equal
function_Equal:
    ; comparison =: direct right operand
    sta function_result_Equal
    lda function_result_Equal ; return value in A
