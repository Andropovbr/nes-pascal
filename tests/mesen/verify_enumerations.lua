local frameCount = 0

local function fail(message, code)
    emu.log("Enumeration validation failed: " .. message)
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

local function validateEnumerations()
    frameCount = frameCount + 1
    if frameCount < 3 then
        return
    end

    expectByte(0x0080, 0x03, "State", 11)
    expectByte(0x0204, 0x01, "PreviousState", 12)
    expectByte(0x0205, 0x01, "IsGameOver", 13)

    emu.log("Enumeration validation passed.")
    emu.stop(0)
end

emu.addEventCallback(validateEnumerations, emu.eventType.endFrame)
