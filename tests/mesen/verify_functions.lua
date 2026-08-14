local frameCount = 0

local function fail(message, code)
    emu.log("Function validation failed: " .. message)
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

local function validateFunctions()
    frameCount = frameCount + 1
    if frameCount < 3 then
        return
    end

    expectByte(0x020A, 0x66, "nested function result", 11)
    expectByte(0x020B, 0x01, "right-first expression order", 12)
    expectByte(0x020C, 0x00, "short-circuit and", 13)
    expectByte(0x020D, 0x01, "short-circuit or", 14)
    expectByte(0x0212, 0x00, "short-circuited call count", 15)
    expectByte(0x0081, 0x01, "direct boolean call count", 16)
    expectByte(0x0213, 0x01, "canonical boolean return", 17)
    expectByte(0x020E, 0x01, "function comparison", 18)
    expectByte(0x020F, 0x03, "procedure/function interaction", 19)
    expectByte(0x0210, 0x00, "byte wraparound", 20)
    expectByte(0x0211, 0xFF, "left-to-right argument order", 21)

    emu.log("Function validation passed.")
    emu.stop(0)
end

emu.addEventCallback(validateFunctions, emu.eventType.endFrame)
