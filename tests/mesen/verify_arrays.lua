local frameCount = 0

local function fail(message, code)
    emu.log("Array validation failed: " .. message)
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

local function validateArrays()
    frameCount = frameCount + 1
    if frameCount < 3 then
        return
    end

    for index = 0, 7 do
        expectByte(0x0204 + index, 0x10 + index, "Values element", 11)
        local expectedFlag = index < 4 and 1 or 0
        expectByte(0x020C + index, expectedFlag, "Active element", 12)
    end

    expectByte(0x0204, 0x10, "lower-bound element", 13)
    expectByte(0x020B, 0x17, "upper-bound element", 14)
    expectByte(0x0080, 0x07, "Index", 15)
    expectByte(0x0081, 0x9C, "Sum", 16)
    expectByte(0x0082, 0x04, "ActiveCount", 17)

    emu.log("Array validation passed.")
    emu.stop(0)
end

emu.addEventCallback(validateArrays, emu.eventType.endFrame)
