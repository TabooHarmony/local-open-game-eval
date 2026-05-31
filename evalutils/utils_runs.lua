local utils_runs = {}

-- Simulates a key press/release in play mode
function utils_runs.sendKeyEvent(pressed, keyCode)
    local VirtualInputManager = game:GetService("VirtualInputManager")
    if pressed then
        VirtualInputManager:SendKeyEvent(true, keyCode, false, game)
    else
        VirtualInputManager:SendKeyEvent(false, keyCode, false, game)
    end
end

-- Creates PlayerScripts in StarterPlayer if missing
function utils_runs.createPlayerScripts()
    local StarterPlayer = game:GetService("StarterPlayer")
    if not StarterPlayer:FindFirstChild("StarterPlayerScripts") then
        local sps = Instance.new("Folder")
        sps.Name = "StarterPlayerScripts"
        sps.Parent = StarterPlayer
    end
end

-- Loads/reloads player scripts (no-op in edit mode)
function utils_runs.loadPlayerScripts()
    -- no-op in edit mode; only relevant during playtest
end

return utils_runs
