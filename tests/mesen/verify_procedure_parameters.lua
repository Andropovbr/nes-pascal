local frameCount = 0

local function fail(message)
    emu.log("Procedure-parameter validation failed: " .. message)
    emu.stop(1)
end

local function expectByte(address, expected, name)
    local actual = emu.read(address, emu.memType.nesDebug)
    if actual ~= expected then
        fail(
            string.format(
                "%s was $%02X instead of $%02X.",
                name,
                actual,
                expected
            )
        )
        return false
    end
    return true
end

local function validateProcedureParameters()
    frameCount = frameCount + 1
    if frameCount < 3 then
        return
    end

    if not expectByte(0x0080, 0x06, "Counter") then
        return
    elseif not expectByte(0x0300, 0x01, "Enabled") then
        return
    elseif not expectByte(0x0081, 0x21, "BackgroundColor") then
        return
    elseif not expectByte(0x0302, 0x04, "Initialize.Step") then
        return
    elseif not expectByte(0x0304, 0x04, "ApplyStep.Amount") then
        return
    elseif not expectByte(0x0306, 0x01, "SelectColor.Matches") then
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
        emu.log("Procedure-parameter validation passed.")
        emu.stop(0)
    end
end

emu.addEventCallback(
    validateProcedureParameters,
    emu.eventType.endFrame
)
