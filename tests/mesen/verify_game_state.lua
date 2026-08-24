local phase = 0
local phaseFrames = 0
local totalFrames = 0
local latchedController1 = 0
local controller1ReadIndex = 0
local controller2ReadIndex = 0
local pausedFrame = nil
local pausedScore = nil
local pausedTicks = nil
local pausedX = nil
local pausedY = nil

local STATE = 0x0080
local PLAYER_X = 0x0081
local PLAYER_Y = 0x0082
local HEALTH = 0x0083
local SCORE = 0x0372
local GAMEPLAY_TICKS = 0x0373
local INITIAL_RANDOM = 0x0374
local SESSION_STARTS = 0x0375
local FRAME_COUNTER = 0x0000

local function read(address)
    return emu.read(address, emu.memType.nesDebug)
end

local function fail(message, code)
    emu.log("Game-state validation failed: " .. message)
    emu.stop(code)
end

local function expect(address, expected, label, code)
    local actual = read(address)
    if actual ~= expected then
        fail(label .. " expected $" .. string.format("%02X", expected)
            .. " but found $" .. string.format("%02X", actual), code)
        return false
    end
    return true
end

local function phaseInput()
    if phase == 1 or phase == 5 or phase == 6 or phase == 8
        or phase == 12 or phase == 13 then
        return 0x08
    elseif phase == 3 then
        return 0x80
    elseif phase == 10 then
        return 0x02
    end
    return 0x00
end

local function serialBit(value, index)
    return math.floor(value / (2 ^ index)) % 2
end

local function advance(nextPhase)
    phase = nextPhase
    phaseFrames = 0
end

local function onStrobeWrite(address, value)
    if value == 1 then
        latchedController1 = phaseInput()
        controller1ReadIndex = 0
        controller2ReadIndex = 0
    end
end

local function onController1Read(address, value)
    local bit = serialBit(latchedController1, controller1ReadIndex)
    controller1ReadIndex = controller1ReadIndex + 1
    return bit
end

local function onController2Read(address, value)
    controller2ReadIndex = controller2ReadIndex + 1
    return 0
end

local function validateGameState()
    totalFrames = totalFrames + 1
    phaseFrames = phaseFrames + 1

    local state = read(STATE)
    local playerX = read(PLAYER_X)
    local playerY = read(PLAYER_Y)
    local health = read(HEALTH)
    local score = read(SCORE)
    local ticks = read(GAMEPLAY_TICKS)
    local sessions = read(SESSION_STARTS)

    if phase == 0 then
        if read(FRAME_COUNTER) > 2 then
            if state ~= 0 or sessions ~= 0 then
                fail("boot did not remain in Title with no started sessions", 10)
                return
            end
            advance(1)
        end
    elseif phase == 1 and read(0x0003) == 0x08 then
        if state ~= 1 or playerX ~= 0x78 or playerY ~= 0x70
            or health ~= 0x03 or score ~= 0 or ticks ~= 0
            or read(INITIAL_RANDOM) ~= 0x15 or sessions ~= 1 then
            fail("Title Start did not create the exact initial Playing state", 11)
            return
        end
        advance(2)
    elseif phase == 2 and read(0x0003) == 0 and read(0x0004) == 0x08 then
        if state ~= 1 or score ~= 1 or ticks ~= 1 then
            fail("Playing did not advance after Start release", 12)
            return
        end
        advance(3)
    elseif phase == 3 and read(0x0003) == 0x80 then
        if state ~= 1 or playerX ~= 0x79 or score ~= 2 or ticks ~= 2 then
            fail("Playing did not update movement and counters", 13)
            return
        end
        advance(4)
    elseif phase == 4 and read(0x0003) == 0 then
        pausedX = playerX
        pausedY = playerY
        pausedScore = score
        pausedTicks = ticks
        advance(5)
    elseif phase == 5 and read(0x0003) == 0x08 and read(0x0004) == 0 then
        if state ~= 2 or playerX ~= pausedX or playerY ~= pausedY
            or score ~= pausedScore or ticks ~= pausedTicks then
            fail("Start did not pause without advancing gameplay", 14)
            return
        end
        pausedFrame = read(FRAME_COUNTER)
        advance(6)
    elseif phase == 6 and read(0x0003) == 0x08 and read(0x0004) == 0x08 then
        if state ~= 2 or score ~= pausedScore or ticks ~= pausedTicks then
            fail("held Start retriggered or advanced paused gameplay", 15)
            return
        end
        advance(7)
    elseif phase == 7 and read(0x0003) == 0 and read(0x0004) == 0x08 then
        if state ~= 2 or playerX ~= pausedX or playerY ~= pausedY
            or score ~= pausedScore or ticks ~= pausedTicks then
            fail("pause did not freeze game-owned state", 16)
            return
        elseif read(FRAME_COUNTER) == pausedFrame then
            fail("frame processing stopped while paused", 17)
            return
        end
        advance(8)
    elseif phase == 8 and read(0x0003) == 0x08 and read(0x0004) == 0 then
        if state ~= 1 or score ~= pausedScore or ticks ~= pausedTicks then
            fail("second Start press did not resume exactly once", 18)
            return
        end
        advance(9)
    elseif phase == 9 and read(0x0003) == 0 and read(0x0004) == 0x08 then
        if state ~= 1 or score ~= pausedScore + 1 or ticks ~= pausedTicks + 1 then
            fail("gameplay did not continue after resume", 19)
            return
        end
        advance(10)
    elseif phase == 10 and read(0x0003) == 0x02 then
        if state ~= 3 or health ~= 0 then
            fail("B did not enter GameOver through ShouldEndGame", 20)
            return
        end
        pausedX = playerX
        pausedY = playerY
        pausedScore = score
        pausedTicks = ticks
        advance(11)
    elseif phase == 11 and read(0x0003) == 0 and read(0x0004) == 0x02 then
        if state ~= 3 or playerX ~= pausedX or playerY ~= pausedY
            or score ~= pausedScore or ticks ~= pausedTicks then
            fail("GameOver did not stop normal gameplay", 21)
            return
        end
        advance(12)
    elseif phase == 12 and read(0x0003) == 0x08 and read(0x0004) == 0 then
        if state ~= 1 or playerX ~= 0x78 or playerY ~= 0x70
            or health ~= 0x03 or score ~= 0 or ticks ~= 0
            or read(INITIAL_RANDOM) ~= 0x15 or sessions ~= 2 then
            fail("GameOver Start did not explicitly reset gameplay", 22)
            return
        end
        advance(13)
    elseif phase == 13 and read(0x0003) == 0x08 and read(0x0004) == 0x08 then
        if state ~= 1 or sessions ~= 2 then
            fail("restart Start press also paused or reset the ROM", 23)
            return
        end
        advance(14)
    elseif phase == 14 and read(0x0003) == 0 and read(0x0004) == 0x08 then
        if state ~= 1 or sessions ~= 2 then
            fail("persistent session state changed after gameplay restart", 24)
            return
        end
        emu.log("Game-state lifecycle validation passed.")
        emu.stop(0)
        return
    end

    if phaseFrames > 30 then
        fail("timed out in phase " .. phase, 80 + phase)
    elseif totalFrames > 300 then
        fail("timed out before lifecycle completion", 99)
    end
end

emu.addMemoryCallback(onStrobeWrite, emu.callbackType.write, 0x4016)
emu.addMemoryCallback(onController1Read, emu.callbackType.read, 0x4016)
emu.addMemoryCallback(onController2Read, emu.callbackType.read, 0x4017)
emu.addEventCallback(validateGameState, emu.eventType.endFrame)
