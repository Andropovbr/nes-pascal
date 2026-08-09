local frames = 0
local sawInitializationPalette = false

local function fail(message, code)
    emu.log("Palette support validation failed: " .. message)
    emu.stop(code)
end

local function validatePaletteSupport()
    frames = frames + 1
    local universal = emu.read(0x3F00, emu.memType.nesPpuDebug)

    if universal == 0x21 then
        local initialBackground1 = emu.read(0x3F01, emu.memType.nesPpuDebug)
        local initialBackground2 = emu.read(0x3F02, emu.memType.nesPpuDebug)
        local initialBackground3 = emu.read(0x3F03, emu.memType.nesPpuDebug)
        local initialSprite1 = emu.read(0x3F11, emu.memType.nesPpuDebug)
        local initialSprite2 = emu.read(0x3F12, emu.memType.nesPpuDebug)
        local initialSprite3 = emu.read(0x3F13, emu.memType.nesPpuDebug)
        if initialBackground1 ~= 0x01 or initialBackground2 ~= 0x11
            or initialBackground3 ~= 0x31 or initialSprite1 ~= 0x06
            or initialSprite2 ~= 0x16 or initialSprite3 ~= 0x26 then
            fail("Initialization palettes were not uploaded in source order.", 6)
            return
        end
        sawInitializationPalette = true
    end

    if sawInitializationPalette and universal == 0x16 then
        local background1 = emu.read(0x3F01, emu.memType.nesPpuDebug)
        local background2 = emu.read(0x3F02, emu.memType.nesPpuDebug)
        local background3 = emu.read(0x3F03, emu.memType.nesPpuDebug)
        local sprite1 = emu.read(0x3F11, emu.memType.nesPpuDebug)
        local sprite2 = emu.read(0x3F12, emu.memType.nesPpuDebug)
        local sprite3 = emu.read(0x3F13, emu.memType.nesPpuDebug)
        if background1 ~= 0x06 or background2 ~= 0x17 or background3 ~= 0x27 then
            fail("The queued background palette was not uploaded completely.", 2)
            return
        end
        if sprite1 ~= 0x06 or sprite2 ~= 0x16 or sprite3 ~= 0x30 then
            fail("The initialized and individually updated sprite colors differ.", 3)
            return
        end
        for address = 0x0325, 0x032D do
            if emu.read(address, emu.memType.nesDebug) ~= 0 then
                fail("A consumed palette dirty flag remained set.", 4)
                return
            end
        end
        if emu.read(0x032E, emu.memType.nesDebug) ~= 0x80
            or emu.read(0x032F, emu.memType.nesDebug) ~= 0x1E
            or emu.read(0x0330, emu.memType.nesDebug) ~= 0x00
            or emu.read(0x0331, emu.memType.nesDebug) ~= 0x00 then
            fail("Palette upload did not preserve the compiler-owned PPU state.", 7)
            return
        end
        emu.log("Palette initialization and queued VBlank update validation passed.")
        emu.stop(0)
        return
    end

    if frames > 20 then
        fail("Timed out before observing initialization and runtime palettes.", 5)
    end
end

emu.addEventCallback(
    validatePaletteSupport,
    emu.eventType.endFrame
)
