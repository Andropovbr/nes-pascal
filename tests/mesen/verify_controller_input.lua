local phase = 0
local phaseFrames = 0
local totalFrames = 0
local phaseStartX = nil
local phaseStartY = nil
local sawWrap = false
local previousFrameCounter = nil
local polledFrameWrites = 0
local strobeHighWrites = 0
local strobeLowWrites = 0
local latchedController1 = 0
local latchedController2 = 0
local controller1ReadIndex = 0
local controller2ReadIndex = 0

local function fail(message)
    emu.log("Controller input validation failed: " .. message)
    local code = phase + 10
    if string.find(message, "newest processed frame") then
        code = 90
    elseif string.find(message, "Right did not") then
        code = 91
    elseif string.find(message, "Timed out") then
        code = 92
    end
    emu.stop(code)
end

local function phaseInputMasks()
    local player1 = 0
    local player2 = 0
    if phase == 1 then
        player1 = 0x80
    elseif phase == 2 then
        player1 = 0x81
    elseif phase == 3 then
        player1 = 0x40
    elseif phase == 4 then
        player1 = 0x10
    elseif phase == 5 then
        player1 = 0x20
    elseif phase == 6 or phase == 7 then
        player1 = 0x02
    elseif phase == 10 then
        player1 = 0x80
    elseif phase == 11 then
        player1 = 0x08
    elseif phase == 12 or phase == 13 then
        player1 = 0x04
    elseif phase == 15 then
        player1 = 0x04
    elseif phase == 16 then
        player1 = 0xF0
        player2 = 0x41
    end
    return player1, player2
end

local function serialBit(value, index)
    return math.floor(value / (2 ^ index)) % 2
end

local function advance(nextPhase, x, y)
    phase = nextPhase
    phaseFrames = 0
    phaseStartX = x
    phaseStartY = y
end

local function onPolledFrameWrite(address, value)
    polledFrameWrites = polledFrameWrites + 1
end

local function onStrobeWrite(address, value)
    if value == 1 then
        strobeHighWrites = strobeHighWrites + 1
        latchedController1, latchedController2 = phaseInputMasks()
        controller1ReadIndex = 0
        controller2ReadIndex = 0
    elseif value == 0 then
        strobeLowWrites = strobeLowWrites + 1
    else
        fail("Controller strobe received a value other than 0 or 1.")
    end
end

local function onController1Read(address, value)
    local bit = serialBit(latchedController1, controller1ReadIndex)
    controller1ReadIndex = controller1ReadIndex + 1
    return bit
end

local function onController2Read(address, value)
    local bit = serialBit(latchedController2, controller2ReadIndex)
    controller2ReadIndex = controller2ReadIndex + 1
    return bit
end

local function validateControllerInput()
    totalFrames = totalFrames + 1
    phaseFrames = phaseFrames + 1

    local frameCounter = emu.read(0x0000, emu.memType.nesDebug)
    local controller1 = emu.read(0x0003, emu.memType.nesDebug)
    local previous1 = emu.read(0x0004, emu.memType.nesDebug)
    local controller2 = emu.read(0x0005, emu.memType.nesDebug)
    local previous2 = emu.read(0x0006, emu.memType.nesDebug)
    local polledFrame = emu.read(0x0007, emu.memType.nesDebug)
    local playerX = emu.read(0x0080, emu.memType.nesDebug)
    local playerY = emu.read(0x0081, emu.memType.nesDebug)
    local playerTile = emu.read(0x0082, emu.memType.nesDebug)
    local wrapAtEdges = emu.read(0x0084, emu.memType.nesDebug)

    if previousFrameCounter ~= nil and frameCounter < previousFrameCounter then
        sawWrap = true
    end
    previousFrameCounter = frameCounter

    if frameCounter ~= 0 and polledFrame ~= frameCounter then
        fail("Controller state was not updated for the newest processed frame.")
        return
    end

    if phase == 0 then
        if frameCounter > 2 and controller1 == 0 and controller2 == 0
            and playerX == 0x78 and playerY == 0x70 and playerTile == 1 then
            advance(1, playerX, playerY)
        end
    elseif phase == 1 and controller1 == 0x80 then
        if playerX ~= (phaseStartX + 1) % 256 then
            fail("Right did not move the player by one pixel while held.")
            return
        end
        advance(2, playerX, playerY)
    elseif phase == 2 and controller1 == 0x81 and previous1 == 0x80 then
        if playerX ~= (phaseStartX + 2) % 256 then
            fail("A did not increase held movement speed to two pixels.")
            return
        end
        advance(3, playerX, playerY)
    elseif phase == 3 and controller1 == 0x40 then
        if playerX ~= (phaseStartX - 1) % 256 then
            fail("Left did not move the player continuously.")
            return
        end
        advance(4, playerX, playerY)
    elseif phase == 4 and controller1 == 0x10 then
        if playerY ~= (phaseStartY - 1) % 256 then
            fail("Up did not move the player continuously.")
            return
        end
        advance(5, playerX, playerY)
    elseif phase == 5 and controller1 == 0x20 then
        if playerY ~= (phaseStartY + 1) % 256 then
            fail("Down did not move the player continuously.")
            return
        end
        advance(6, playerX, playerY)
    elseif phase == 6 and controller1 == 0x02 and previous1 ~= 0x02 then
        if playerTile ~= 2 then
            fail("B press did not select the alternate visible tile.")
            return
        end
        advance(7, playerX, playerY)
    elseif phase == 7 and controller1 == 0x02 and previous1 == 0x02 then
        if playerTile ~= 2 then
            fail("Held B did not keep a consistent controller_down state.")
            return
        end
        advance(8, playerX, playerY)
    elseif phase == 8 and controller1 == 0 and previous1 == 0x02 then
        if playerTile ~= 1 then
            fail("B release did not restore the normal tile.")
            return
        end
        advance(9, playerX, playerY)
    elseif phase == 9 and controller1 == 0 and previous1 == 0 then
        if playerTile ~= 1 then
            fail("B released transition persisted for more than one frame.")
            return
        end
        advance(10, playerX, playerY)
    elseif phase == 10 and controller1 == 0x80 then
        if playerX ~= 0x78 then
            advance(11, playerX, playerY)
        end
    elseif phase == 11 and controller1 == 0x08 and previous1 == 0x80 then
        if playerX ~= 0x78 or playerY ~= 0x70 then
            fail("Start press did not reset the player exactly once.")
            return
        end
        advance(12, playerX, playerY)
    elseif phase == 12 and controller1 == 0x04 and previous1 ~= 0x04 then
        if wrapAtEdges ~= 1 then
            fail("Select press did not enable edge wrapping.")
            return
        end
        advance(13, playerX, playerY)
    elseif phase == 13 and controller1 == 0x04 and previous1 == 0x04 then
        if wrapAtEdges ~= 1 then
            fail("Held Select retriggered controller_pressed.")
            return
        end
        advance(14, playerX, playerY)
    elseif phase == 14 and controller1 == 0 and previous1 == 0x04 then
        advance(15, playerX, playerY)
    elseif phase == 15 and controller1 == 0x04 and previous1 == 0 then
        if wrapAtEdges ~= 0 then
            fail("A second Select press did not toggle edge wrapping off.")
            return
        end
        advance(16, playerX, playerY)
    elseif phase == 16 and controller1 == 0xF0 and controller2 == 0x41 then
        if previous2 ~= 0 then
            fail("Controller 2 previous state was not independent.")
            return
        end
        advance(17, playerX, playerY)
    elseif phase == 17 and controller1 == 0 and controller2 == 0 and sawWrap then
        local oamY = emu.read(0x0200, emu.memType.nesDebug)
        local oamTile = emu.read(0x0201, emu.memType.nesDebug)
        local oamX = emu.read(0x0203, emu.memType.nesDebug)
        if oamY ~= playerY or oamX ~= playerX or oamTile ~= playerTile then
            fail("OAM shadow did not contain one complete committed sprite.")
            return
        elseif strobeHighWrites ~= strobeLowWrites then
            fail("Controller strobe high/low writes were unbalanced.")
            return
        elseif polledFrameWrites - 1 ~= strobeHighWrites then
            fail("Controller ports were not polled exactly once per processed frame.")
            return
        end

        emu.log("Controller input validation passed across frame wraparound.")
        emu.stop(0)
        return
    end

    if phaseFrames > 20 and phase < 17 then
        fail("Timed out in validation phase " .. phase .. ".")
    elseif totalFrames > 400 then
        fail("Timed out before frame-counter wraparound validation completed.")
    end
end

emu.addMemoryCallback(
    onPolledFrameWrite,
    emu.callbackType.write,
    0x0007
)
emu.addMemoryCallback(
    onStrobeWrite,
    emu.callbackType.write,
    0x4016
)
emu.addEventCallback(
    validateControllerInput,
    emu.eventType.endFrame
)
emu.addMemoryCallback(
    onController1Read,
    emu.callbackType.read,
    0x4016
)
emu.addMemoryCallback(
    onController2Read,
    emu.callbackType.read,
    0x4017
)
