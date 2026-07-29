local observedFrames = 0
local previousRuntimeCounter = nil
local previousUserFrames = 0

local function fail(message)
    emu.log("Frame synchronization validation failed: " .. message)
    emu.stop(1)
end

local function expectByte(address, expected, name)
    local actual = emu.read(address, emu.memType.nesDebug)
    if actual ~= expected then
        fail(
            string.format(
                "%s at $%04X was $%02X instead of $%02X.",
                name,
                address,
                actual,
                expected
            )
        )
        return false
    end
    return true
end

local function validateFrameSynchronization()
    local runtimeCounter = emu.read(0x0000, emu.memType.nesDebug)
    local userFrames = emu.read(0x0080, emu.memType.nesDebug)
    if userFrames > previousUserFrames + 1 then
        fail("Frames advanced more than once between consecutive frame callbacks.")
        return
    end
    previousUserFrames = userFrames

    if previousRuntimeCounter ~= nil and runtimeCounter ~= previousRuntimeCounter then
        observedFrames = observedFrames + 1
    end
    previousRuntimeCounter = runtimeCounter

    if observedFrames < 6 then
        return
    end

    if not expectByte(0x0080, 0x03, "Frames") then
        return
    elseif not expectByte(0x0081, 0x00, "Running") then
        return
    end

    local paletteColor = emu.read(0x3F00, emu.memType.nesPpuDebug)
    if paletteColor ~= 0x21 then
        fail(
            string.format(
                "PPU palette entry $3F00 was $%02X instead of $21.",
                paletteColor
            )
        )
    else
        emu.log("Frame synchronization validation passed.")
        emu.stop(0)
    end
end

emu.addEventCallback(
    validateFrameSynchronization,
    emu.eventType.endFrame
)
