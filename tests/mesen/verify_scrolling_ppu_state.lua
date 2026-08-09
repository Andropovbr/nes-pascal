local frames = 0
local sawNonzeroScroll = false

local function fail(message, code)
    emu.log("Scrolling and PPU state validation failed: " .. message)
    emu.stop(code)
end

local function validateScrollingPpuState()
    frames = frames + 1
    local control = emu.read(0x0229, emu.memType.nesDebug)
    local mask = emu.read(0x022A, emu.memType.nesDebug)
    local scrollX = emu.read(0x022B, emu.memType.nesDebug)
    local scrollY = emu.read(0x022C, emu.memType.nesDebug)

    if control ~= 0x80 then
        return
    end
    if mask ~= 0x1E then
        fail("The authoritative PPUCTRL or PPUMASK shadow changed.", 2)
        return
    end
    if scrollX == 0x08 and scrollY == 0x04 then
        sawNonzeroScroll = true
    end
    if sawNonzeroScroll and scrollX == 0 and scrollY == 0 then
        if emu.read(0x022F, emu.memType.nesDebug) ~= 0 then
            fail("The complete scroll pair remained pending after NMI.", 3)
            return
        end
        if emu.read(0x3F01, emu.memType.nesPpuDebug) ~= 0x11 then
            fail("The palette update did not coexist with scroll restoration.", 4)
            return
        end
        emu.log("Fixed scroll staging and final PPU state restoration passed.")
        emu.stop(0)
        return
    end
    if frames > 20 then
        fail("Timed out before observing both complete scroll pairs.", 5)
    end
end

emu.addEventCallback(validateScrollingPpuState, emu.eventType.endFrame)
