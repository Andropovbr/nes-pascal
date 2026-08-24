local phase = 0
local phaseFrames = 0
local totalFrames = 0
local latchedController1 = 0
local controllerReadIndex = 0
local baselineX = 0
local baselineY = 0
local baselineEnemyX = 0
local baselineEnemyY = 0
local enemyCountBeforeKills = 0
local experienceBeforeCollection = 0
local damageFrame = nil
local damageFlashStart = 0
local damageFlashLast = 0
local damageFlashChanges = 0
local stressFrames = 0
local stressUpdates = 0
local previousProcessed = nil
local refillGemStarted = false

local STATE = 0x0080
local PLAYER_X = 0x0085
local PLAYER_Y = 0x0086
local PLAYER_HEALTH = 0x0087
local PLAYER_INVULNERABILITY = 0x0088
local PLAYER_MOVING = 0x008A
local SWORD_X = 0x008B
local SWORD_Y = 0x008C
local SWORD_ACTIVE = 0x008D
local SWORD_COOLDOWN = 0x008E
local SPAWN_TIMER = 0x008F
local DAMAGE_FLASH_TIMER = 0x0091
local CONTACT_SCAN_INDEX = 0x0092
local SESSION_COUNT = 0x0095
local ACTIVE_ENEMY_COUNT = 0x0096
local ACTIVE_GEM_COUNT = 0x0097
local ENEMIES = 0x03F6
local GEMS = 0x0426
local EXPERIENCE = 0x0452
local METASPRITE_ANIMATION = 0x0358
local LAST_PROCESSED_FRAME = 0x0002

local function read(address)
    return emu.read(address, emu.memType.nesDebug)
end

local function write(address, value)
    emu.write(address, value, emu.memType.nesDebug)
end

local function fail(message, code)
    emu.log("NES Survivor vertical-slice validation failed: " .. message)
    emu.stop(code)
end

local function serialBit(value, index)
    return math.floor(value / (2 ^ index)) % 2
end

local function phaseInput()
    if phase == 1 or phase == 14 then
        return 0x08
    elseif phase == 3 then
        return 0x90
    end
    return 0x00
end

local function advance(nextPhase)
    phase = nextPhase
    phaseFrames = 0
end

local function enemyAddress(index, field)
    return ENEMIES + index * 4 + field
end

local function gemAddress(index, field)
    return GEMS + index * 3 + field
end

local function setEnemy(index, x, y, active)
    write(enemyAddress(index, 0), x)
    write(enemyAddress(index, 1), y)
    write(enemyAddress(index, 2), active and 1 or 0)
    write(enemyAddress(index, 3), 0)
end

local function activeHardwareSprites()
    local count = 0
    for slot = 0, 63 do
        if emu.read(slot * 4, emu.memType.nesSpriteRam) ~= 0xFF then
            count = count + 1
        end
    end
    return count
end

local function onStrobeWrite(address, value)
    if value == 1 then
        latchedController1 = phaseInput()
        controllerReadIndex = 0
    end
end

local function onController1Read(address, value)
    local bit = serialBit(latchedController1, controllerReadIndex)
    controllerReadIndex = controllerReadIndex + 1
    return bit
end

local function onController2Read(address, value)
    return 0
end

local function validateVerticalSlice()
    totalFrames = totalFrames + 1
    phaseFrames = phaseFrames + 1

    if phase == 0 then
        if read(LAST_PROCESSED_FRAME) > 2 then
            if read(STATE) ~= 0 or read(SESSION_COUNT) ~= 0 then
                fail("boot did not remain in the visible Title state", 10)
                return
            end
            if activeHardwareSprites() ~= 7 then
                fail("Title did not render the seven-sprite Soldier emblem", 11)
                return
            end
            advance(1)
        end
    elseif phase == 1 then
        if read(STATE) == 1 then
            if read(SESSION_COUNT) ~= 1 or read(PLAYER_X) ~= 0x80
                or read(PLAYER_Y) ~= 0x78 or read(PLAYER_HEALTH) ~= 5 then
                fail("Start did not initialize the first gameplay session", 12)
                return
            end
            advance(2)
        end
    elseif phase == 2 then
        if phaseFrames >= 2 then
            baselineX = read(PLAYER_X)
            baselineY = read(PLAYER_Y)
            advance(3)
        end
    elseif phase == 3 then
        if read(0x0003) == 0x90 and read(PLAYER_X) >= baselineX + 4
            and read(PLAYER_Y) <= baselineY - 4 then
            if read(PLAYER_MOVING) ~= 1 then
                fail("diagonal D-pad movement did not update both axes", 13)
                return
            end
            if read(METASPRITE_ANIMATION) ~= 1 then
                fail("movement did not select the Soldier walking animation", 14)
                return
            end
            advance(4)
        end
    elseif phase == 4 then
        if phaseFrames >= 2 then
            if read(PLAYER_MOVING) ~= 0 or read(METASPRITE_ANIMATION) ~= 0 then
                fail("released movement did not return to idle animation", 15)
                return
            end
            write(SPAWN_TIMER, 1)
            advance(5)
        end
    elseif phase == 5 then
        if read(ACTIVE_ENEMY_COUNT) >= 1 then
            local x = read(enemyAddress(0, 0))
            local y = read(enemyAddress(0, 1))
            if read(enemyAddress(0, 2)) ~= 1 then
                fail("RNG spawn did not activate the first Bat record", 16)
                return
            end
            if x > 9 and x < 0xF6 and y > 9 and y < 0xE7 then
                fail("RNG spawn did not choose one arena edge", 17)
                return
            end
            baselineEnemyX = x
            baselineEnemyY = y
            advance(6)
        end
    elseif phase == 6 then
        if phaseFrames >= 5 then
            if read(enemyAddress(0, 0)) == baselineEnemyX
                and read(enemyAddress(0, 1)) == baselineEnemyY then
                fail("the spawned Bat did not pursue the player", 18)
                return
            end
            advance(7)
        end
    elseif phase == 7 then
        if read(ACTIVE_ENEMY_COUNT) < 12 then
            write(SPAWN_TIMER, 1)
        else
            enemyCountBeforeKills = read(ACTIVE_ENEMY_COUNT)
            write(SWORD_ACTIVE, 0)
            write(SWORD_COOLDOWN, 0)
            advance(8)
        end
    elseif phase == 8 then
        if read(SWORD_ACTIVE) > 0 then
            local swordX = read(SWORD_X)
            local swordY = read(SWORD_Y)
            for index = 0, 7 do
                setEnemy(index, swordX, swordY, true)
            end
            advance(9)
        end
    elseif phase == 9 then
        if read(ACTIVE_GEM_COUNT) >= 8 then
            if read(ACTIVE_ENEMY_COUNT) ~= enemyCountBeforeKills - 8 then
                fail("sword collision did not remove exactly eight arranged Bats", 19)
                return
            end
            if activeHardwareSprites() < 7 + 2 + 4 * 2 + 8 then
                fail("Bat deaths did not replace enemy sprites with XP gems", 20)
                return
            end
            write(SWORD_ACTIVE, 0)
            write(SWORD_COOLDOWN, 0xFF)
            write(PLAYER_X, 0x20)
            write(PLAYER_Y, 0x20)
            advance(10)
        end
    elseif phase == 10 then
        if read(ACTIVE_GEM_COUNT) < 8 and not refillGemStarted
            and read(ACTIVE_ENEMY_COUNT) == 12 then
            write(PLAYER_X, 0xD0)
            write(PLAYER_Y, 0x20)
            setEnemy(0, 0xE1, 0x20, true)
            write(SWORD_ACTIVE, 0)
            write(SWORD_COOLDOWN, 0)
            refillGemStarted = true
        elseif read(ACTIVE_GEM_COUNT) >= 8 and refillGemStarted then
            write(SWORD_ACTIVE, 0)
            write(SWORD_COOLDOWN, 0xFF)
            write(PLAYER_X, 0x20)
            write(PLAYER_Y, 0x20)
            if read(ACTIVE_ENEMY_COUNT) < 12 then
                write(SPAWN_TIMER, 1)
            end
            refillGemStarted = false
        elseif read(ACTIVE_GEM_COUNT) < 8 and refillGemStarted then
            -- Wait for the arranged automatic-sword collision.
        elseif read(ACTIVE_ENEMY_COUNT) < 12 then
            write(SPAWN_TIMER, 1)
        else
            if read(ACTIVE_GEM_COUNT) ~= 8 then
                fail("the XP pool did not stay saturated during Bat refills", 21)
                return
            end
            if activeHardwareSprites() == 41 then
                previousProcessed = read(LAST_PROCESSED_FRAME)
                stressFrames = 0
                stressUpdates = 0
                advance(11)
            end
        end
    elseif phase == 11 then
        write(PLAYER_HEALTH, 0xFF)
        write(PLAYER_INVULNERABILITY, 0xFF)
        write(SWORD_ACTIVE, 0)
        write(SWORD_COOLDOWN, 0xFF)
        stressFrames = stressFrames + 1
        local processed = read(LAST_PROCESSED_FRAME)
        if processed ~= previousProcessed then
            stressUpdates = stressUpdates + 1
            previousProcessed = processed
        end
        if stressFrames >= 120 then
            if stressUpdates < 100 then
                fail("41-sprite stress load fell below 100 updates per 120 video frames", 23)
                return
            end
            experienceBeforeCollection = read(EXPERIENCE)
            write(gemAddress(0, 0), read(PLAYER_X))
            write(gemAddress(0, 1), read(PLAYER_Y))
            write(gemAddress(0, 2), 1)
            write(0x0094, 0)
            advance(12)
        end
    elseif phase == 12 then
        if read(EXPERIENCE) > experienceBeforeCollection then
            if read(ACTIVE_GEM_COUNT) ~= 7 then
                fail("collecting one XP gem did not shrink the active pool", 24)
                return
            end
            write(PLAYER_HEALTH, 5)
            write(PLAYER_INVULNERABILITY, 0)
            write(SWORD_ACTIVE, 0)
            write(SWORD_COOLDOWN, 0xFF)
            write(CONTACT_SCAN_INDEX, 0)
            setEnemy(0, read(PLAYER_X), read(PLAYER_Y), true)
            advance(13)
        end
    elseif phase == 13 then
        if damageFrame == nil and read(PLAYER_HEALTH) == 4 then
            damageFlashStart = read(DAMAGE_FLASH_TIMER)
            if damageFlashStart < 9 or damageFlashStart > 10 then
                fail("player damage did not start the ten-frame flash", 25)
                return
            end
            damageFrame = totalFrames
            damageFlashLast = damageFlashStart
            damageFlashChanges = 0
            setEnemy(0, 8, 8, true)
        elseif damageFrame ~= nil then
            local currentFlash = read(DAMAGE_FLASH_TIMER)
            if currentFlash ~= damageFlashLast then
                damageFlashLast = currentFlash
            end
            if currentFlash == 0 and damageFlashChanges == 0 then
                write(PLAYER_HEALTH, 1)
                write(PLAYER_INVULNERABILITY, 0)
                write(CONTACT_SCAN_INDEX, 0)
                write(SWORD_ACTIVE, 0)
                write(SWORD_COOLDOWN, 0xFF)
                setEnemy(0, read(PLAYER_X), read(PLAYER_Y), true)
                damageFlashChanges = 1
            elseif damageFlashChanges == 1 and read(STATE) == 2
                and activeHardwareSprites() == 0 then
                -- Observe the post-DMA hardware state, not only the CPU shadow.
                advance(14)
            end
        end
    elseif phase == 14 then
        if read(STATE) == 1 then
            if read(SESSION_COUNT) ~= 2 or read(PLAYER_HEALTH) ~= 5
                or read(ACTIVE_ENEMY_COUNT) ~= 0 or read(ACTIVE_GEM_COUNT) ~= 0
                or read(PLAYER_X) ~= 0x80 or read(PLAYER_Y) ~= 0x78 then
                fail("Start did not restart gameplay without resetting the ROM", 29)
                return
            end
            emu.log(string.format(
                "NES Survivor vertical slice passed: 41 OAM sprites, %d/120 stress updates",
                stressUpdates
            ))
            emu.stop(0)
            return
        end
    end

    if phaseFrames > 240 then
        fail("timed out in phase " .. phase, 80 + phase)
    elseif totalFrames > 900 then
        fail("timed out before scenario completion", 99)
    end
end

emu.addMemoryCallback(onStrobeWrite, emu.callbackType.write, 0x4016)
emu.addMemoryCallback(onController1Read, emu.callbackType.read, 0x4016)
emu.addMemoryCallback(onController2Read, emu.callbackType.read, 0x4017)
emu.addEventCallback(validateVerticalSlice, emu.eventType.endFrame)
