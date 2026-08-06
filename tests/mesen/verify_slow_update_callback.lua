local lastProcessedWrites = 0
local acceptedFrames = 0
local updateStarts = 0
local updateCompletions = 0
local observedRuntimeFrames = 0
local previousRuntimeCounter = nil
local sawPendingFrameDuringUpdate = false
local waitingForUpdateStart = false

local function fail(message)
    emu.log("Slow update callback validation failed: " .. message)
    emu.stop(1)
end

local function onLastProcessedWrite(address, value)
    lastProcessedWrites = lastProcessedWrites + 1

    -- The first write is RESET RAM clearing; the second establishes the
    -- update-loop baseline. Later writes accept one newest pending frame.
    if lastProcessedWrites <= 2 then
        return
    end
    if waitingForUpdateStart then
        fail("A second pending frame was accepted before Update started.")
        return
    end

    acceptedFrames = acceptedFrames + 1
    waitingForUpdateStart = true
end

local function onUpdateActiveWrite(address, value)
    local current = emu.read(0x0201, emu.memType.nesDebug)
    if value == 1 then
        if current ~= 0 then
            fail("Update was entered while a previous Update was active.")
            return
        elseif not waitingForUpdateStart then
            fail("Update started without accepting a pending frame.")
            return
        end
        waitingForUpdateStart = false
        updateStarts = updateStarts + 1
    elseif value == 0 and current == 1 then
        updateCompletions = updateCompletions + 1
    end
end

local function validateSlowUpdate()
    local runtimeCounter = emu.read(0x0000, emu.memType.nesDebug)
    local lastProcessed = emu.read(0x0002, emu.memType.nesDebug)
    local updateActive = emu.read(0x0201, emu.memType.nesDebug)

    if previousRuntimeCounter ~= nil and runtimeCounter ~= previousRuntimeCounter then
        observedRuntimeFrames = observedRuntimeFrames + 1
    end
    previousRuntimeCounter = runtimeCounter

    if updateActive == 1 and runtimeCounter ~= lastProcessed then
        sawPendingFrameDuringUpdate = true
    end

    if updateStarts >= 6 and updateCompletions >= 5 then
        if not sawPendingFrameDuringUpdate then
            fail("The slow Update never crossed an NMI with a frame pending.")
            return
        elseif acceptedFrames ~= updateStarts then
            fail("Accepted frames and sequential Update calls diverged.")
            return
        end

        emu.log("Slow update callback pending-frame validation passed.")
        emu.stop(0)
        return
    end

    if observedRuntimeFrames > 120 then
        fail("Timed out before enough slow Update callbacks completed.")
    end
end

emu.addMemoryCallback(
    onLastProcessedWrite,
    emu.callbackType.write,
    0x0002
)
emu.addMemoryCallback(
    onUpdateActiveWrite,
    emu.callbackType.write,
    0x0201
)
emu.addEventCallback(
    validateSlowUpdate,
    emu.eventType.endFrame
)
