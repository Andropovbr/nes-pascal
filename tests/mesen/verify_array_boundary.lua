local frameCount = 0

local function fail(message, code)
    emu.log("Array boundary validation failed: " .. message)
    emu.stop(code)
end

local function expectByte(address, expected, name, failureCode)
    local actual = emu.read(address, emu.memType.nesDebug)
    if actual ~= expected then
        fail(
            string.format("%s was $%02X instead of $%02X.", name, actual, expected),
            failureCode
        )
    end
end

local function validateArrayBoundary()
    frameCount = frameCount + 1
    if frameCount < 3 then
        return
    end

    expectByte(0x0204, 0xC3, "Values[0] final", 11)
    expectByte(0x0303, 0xD4, "Values[255] final", 12)
    expectByte(0x0304, 0xA1, "DirectFirst", 13)
    expectByte(0x0305, 0xB2, "DirectLast", 14)
    expectByte(0x0306, 0xC3, "VariableFirst", 15)
    expectByte(0x0307, 0xD4, "VariableLast", 16)
    expectByte(0x0080, 0xFF, "Index", 17)

    emu.log("Array boundary validation passed.")
    emu.stop(0)
end

emu.addEventCallback(validateArrayBoundary, emu.eventType.endFrame)
