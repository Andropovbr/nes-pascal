local frameCount = 0

local function fail(message, code)
    emu.log("Record validation failed: " .. message)
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

local function validateRecords()
    frameCount = frameCount + 1
    if frameCount < 3 then
        return
    end

    expectByte(0x0204, 0x20, "Enemies[0].X", 11)
    expectByte(0x0205, 0x30, "Enemies[0].Y", 12)
    expectByte(0x0206, 0x01, "Enemies[0].State", 13)
    expectByte(0x0207, 0x01, "Enemies[0].Visible", 14)
    expectByte(0x0208, 0x44, "Enemies[1].X", 15)
    expectByte(0x0209, 0x31, "Enemies[1].Y", 16)
    expectByte(0x020A, 0x01, "Enemies[1].State", 17)
    expectByte(0x020B, 0x01, "Enemies[1].Visible", 18)

    expectByte(0x0214, 0x20, "Player.X", 19)
    expectByte(0x0215, 0x30, "Player.Y", 20)
    expectByte(0x0216, 0x01, "Player.State", 21)
    expectByte(0x0217, 0x01, "Player.Visible", 22)
    expectByte(0x0080, 0x01, "Index", 23)
    expectByte(0x0081, 0x45, "Result", 24)
    expectByte(0x0218, 0x01, "IsVisible", 25)

    emu.log("Record validation passed.")
    emu.stop(0)
end

emu.addEventCallback(validateRecords, emu.eventType.endFrame)
