local utils_he = {}

-- Returns all non-service instances in the game as an array (snapshot)
function utils_he.getAllReasonableItems()
    local items = {}
    for _, obj in ipairs(game:GetDescendants()) do
        local ok, isService = pcall(function()
            return game:GetService(obj.ClassName) ~= nil
        end)
        if not (ok and isService) then
            table.insert(items, obj)
        end
    end
    return items
end

-- Returns items in 'new' that are not in 'old' (set difference by instance identity)
function utils_he.table_difference(old, new)
    local oldSet = {}
    for _, obj in ipairs(old) do
        oldSet[obj] = true
    end
    local diff = {}
    for _, obj in ipairs(new) do
        if not oldSet[obj] then
            table.insert(diff, obj)
        end
    end
    return diff
end

-- Returns selected instances from a selection context table
function utils_he.GetSelected(selectionContext)
    local selected = {}
    for _, selection in ipairs(selectionContext) do
        for _, instance in ipairs(game:GetDescendants()) do
            if instance.Name == selection.instanceName and instance:IsA(selection.className) then
                table.insert(selected, instance)
                break
            end
        end
    end
    return selected
end

-- Returns bounding box size info for a model
function utils_he.getSizeInfoOfModel(model)
    local cf, size = model:GetBoundingBox()
    local sx, sy, sz = size.X, size.Y, size.Z
    local shortest = math.min(sx, sy, sz)
    local longest = math.max(sx, sy, sz)
    return {
        shortestSide = shortest,
        longestSide = longest,
        size = size,
        cframe = cf,
    }
end

return utils_he
