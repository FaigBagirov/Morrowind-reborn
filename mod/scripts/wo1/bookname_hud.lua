-- Work Order 1 -- book probe, Layer 3 (PLAYER context, on screen).
--
-- The first run of this probe left the important question open. Layer 1 said
-- both writes succeeded; the player reported the name changed but the page
-- text did not; and Layer 2 never ran, so there was no independent readback to
-- separate the two possibilities:
--
--   a) the running game's data really does hold the substitution, and only the
--      book WINDOW shows something else, or
--   b) the load-context write to `text` never reached the running game at all.
--
-- This script answers that on screen, without a log and without the player
-- hunting for anything: it reads the book record from the PLAYER context of a
-- live session and prints what it finds at the bottom of the screen.
--
-- API surfaces, verified in the shipped 0.51 stubs before use:
--   resources/lua_api/openmw/ui.lua     showMessage(#string msg, #table opts)
--   resources/lua_api/openmw/types.lua  BookRecord: @field name, @field text
--   resources/vfs/builtin.omwscripts    PLAYER: is a valid script section
--
-- Stores nothing, implements no onSave handler, adds nothing to save games.

local types = require('openmw.types')
local ui = require('openmw.ui')

local TAG = '[WO1]'
local BOOK_ID = 'bk_BriefHistoryEmpire1'

local function log(...)
    local parts = {}
    for i = 1, select('#', ...) do
        parts[i] = tostring((select(i, ...)))
    end
    print(TAG .. ' ' .. table.concat(parts, ' '))
end

local function try(fn)
    local ok, res = pcall(fn)
    if ok then return true, res end
    return false, res
end

-- Strip the pseudo-HTML so the message shows the words the page would show,
-- not the markup around them.
local function visible(text, n)
    local s = string.gsub(tostring(text), '<[^>]*>', '')
    s = string.gsub(s, '[\r\n]', ' ')
    s = string.gsub(s, '%s+', ' ')
    s = string.gsub(s, '^%s+', '')
    n = n or 60
    if #s > n then s = string.sub(s, 1, n) end
    return s
end

local function readField(field)
    for _, variant in ipairs({ BOOK_ID, string.lower(BOOK_ID) }) do
        local ok, val = try(function()
            local rec = types.Book.records[variant]
            if rec == nil then return nil end
            return rec[field]
        end)
        if ok and val ~= nil then return val end
    end
    return nil
end

local done = false

local function runOnce()
    if done then return end
    done = true

    local name = readField('name')
    local text = readField('text')

    local nameLine = 'WO1 name: ' .. tostring(name)
    local textLine = 'WO1 text: ' .. (text and visible(text, 60) or '<nil>')

    log('')
    log('=== LAYER 3: read from the PLAYER context of the live session ===')
    log('  ' .. nameLine)
    log('  ' .. textLine)
    log('  text length:', text and #text or 'n/a')

    -- Two messages rather than one, so neither is truncated off screen.
    pcall(function() ui.showMessage(nameLine) end)
    pcall(function() ui.showMessage(textLine) end)
end

return {
    engineHandlers = {
        -- onUpdate rather than onInit: the UI is up by the first frame of a
        -- live session either way, and this fires whether the player started
        -- a new game or loaded a save.
        onUpdate = function() pcall(runOnce) end,
    },
}
