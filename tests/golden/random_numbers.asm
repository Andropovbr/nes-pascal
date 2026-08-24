runtime_random_state_low: .res 1 ; $0204: low byte of the feature-gated 16-bit Galois LFSR state
runtime_random_state_high: .res 1 ; $0205: high byte of the feature-gated 16-bit Galois LFSR state
runtime_random_span: .res 1 ; $0206: inclusive random-range span used by bounded reduction
runtime_random_cutoff: .res 1 ; $0207: rejection cutoff used by unbiased bounded reduction
---
runtime_seed_random:
    beq @random_seed_zero
    sta runtime_random_state_low  ; nonzero byte is replicated
    sta runtime_random_state_high
    rts
@random_seed_zero:
    lda #$E1                ; zero seed normalizes to $ACE1
    sta runtime_random_state_low
    lda #$AC
    sta runtime_random_state_high
    rts
---
runtime_random_byte:
    lda runtime_random_state_low
    ora runtime_random_state_high
    bne @random_step
    ; Zero is the cleared-RAM marker for one-time automatic timing seeding.
    lda runtime_frame_counter
    tax                     ; coherent timing/input snapshot for both bytes
    eor #$E1
    sta runtime_random_state_low
    txa
    eor #$AC               ; differing constants guarantee nonzero state
    sta runtime_random_state_high
@random_step:
    lsr runtime_random_state_high
    ror runtime_random_state_low
    bcc @random_output
    lda runtime_random_state_high
    eor #$B4               ; high byte of Galois mask $B400
    sta runtime_random_state_high
@random_output:
    lda runtime_random_state_low
    rts
---
    ; cutoff = 256 mod span, calculated without generic division/modulo.
    lda #$FF
@random_cutoff_loop:
    sec
    sbc runtime_random_span
    bcs @random_cutoff_loop
    clc
    adc runtime_random_span ; 255 mod span
    clc
    adc #$01               ; 256 mod span, except divisible spans
    cmp runtime_random_span
    bcc @random_cutoff_ready
    lda #$00
@random_cutoff_ready:
    sta runtime_random_cutoff

@random_range_sample:
    jsr runtime_random_byte
    cmp runtime_random_cutoff
    bcc @random_range_sample ; reject the short low tail
