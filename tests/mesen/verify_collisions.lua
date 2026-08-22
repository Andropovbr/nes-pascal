local frameCount = 0

local function fail(message, code)
    emu.log("Collision validation failed: " .. message)
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

local function expectRect(address, x, y, width, height, name, failureCode)
    expectByte(address, x, name .. ".X", failureCode)
    expectByte(address + 1, y, name .. ".Y", failureCode + 1)
    expectByte(address + 2, width, name .. ".Width", failureCode + 2)
    expectByte(address + 3, height, name .. ".Height", failureCode + 3)
end

local function validateCollisions()
    frameCount = frameCount + 1
    if frameCount < 3 then
        return
    end

    expectByte(0x0372, 0x01, "point at top-left", 11)
    expectByte(0x0373, 0x00, "point at right edge", 12)
    expectByte(0x0374, 0x00, "point at bottom edge", 13)
    expectByte(0x0375, 0x01, "point at inside corner", 14)
    expectByte(0x0376, 0x01, "partial rectangle overlap", 15)
    expectByte(0x0377, 0x00, "touching rectangles", 16)
    expectByte(0x0378, 0x00, "zero-width rectangle", 17)
    expectByte(0x0379, 0x00, "wrapped point rectangle", 18)
    expectByte(0x037A, 0x00, "wrapped rectangle overlap", 19)
    expectByte(0x037B, 0x01, "rectangle ending exactly at 256", 20)
    expectByte(0x0383, 0x01, "collision in a function boolean expression", 21)
    expectByte(0x0082, 0x01, "short-circuit function call count", 22)

    expectRect(0x0366, 0xF1, 0xE2, 0x06, 0x05, "sprite bounds", 30)
    expectRect(0x036A, 0x41, 0x52, 0x06, 0x05, "metasprite normal bounds", 40)
    expectRect(0x036E, 0x39, 0x49, 0x06, 0x05, "metasprite flipped bounds", 50)

    expectByte(0x037C, 0x01, "background top-left", 60)
    expectByte(0x037D, 0x00, "background passable center", 61)
    expectByte(0x037E, 0x01, "background top-right", 62)
    expectByte(0x037F, 0x01, "background bottom-left", 63)
    expectByte(0x0380, 0x00, "background row before boundary", 64)
    expectByte(0x0381, 0x01, "background logical index above 255", 65)
    expectByte(0x0382, 0x00, "background pixel outside 30 rows", 66)

    emu.log("Collision validation passed.")
    emu.stop(0)
end

emu.addEventCallback(validateCollisions, emu.eventType.endFrame)
