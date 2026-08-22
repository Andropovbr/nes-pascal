runtime_collision_point_in_rect:
    jsr runtime_collision_validate_left
    beq @collision_point_false
    lda runtime_collision_point_x
    cmp runtime_collision_left_x
    bcc @collision_point_false
    sec
    sbc runtime_collision_left_x
    cmp runtime_collision_left_width
    bcs @collision_point_false
---
runtime_collision_rects:
    jsr runtime_collision_validate_left
    beq @collision_rects_false
    jsr runtime_collision_validate_right
    beq @collision_rects_false
    lda runtime_collision_left_x
    cmp runtime_collision_right_x
    bcc @collision_left_starts_first_x
---
runtime_collision_sprite_bounds:
    lda runtime_collision_point_x
    cmp #$40
    bcs runtime_collision_store_invalid_bounds
    tax
    lda runtime_sprite_logical_y, x
---
metasprite_collision_x:
    .byte $F4, $F4, $F4, $F4, $F4, $F4
metasprite_collision_y:
    .byte $F4, $F4, $F4, $F4, $F4, $F4
metasprite_collision_width:
    .byte $18, $18, $18, $18, $18, $18
metasprite_collision_height:
    .byte $18, $18, $18, $18, $18, $18
---
runtime_collision_background:
    lda runtime_collision_point_y
    cmp #$F0                ; rows 0..29 occupy pixels 0..239
    bcs @collision_background_false
    and #$F8
    lsr a                   ; (pixel_y >> 3) * 4 packed bytes per row
---
collision_bit_masks:
    .byte $01, $02, $04, $08, $10, $20, $40, $80
collision_map_data:
    .byte $FF, $FF, $FF, $FF, $01, $00, $00, $80
