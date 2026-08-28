-- Work Order 1 -- book probe, Layer 2 (GLOBAL context).
--
-- Reads the two written values back from a context that has no relationship
-- to the load context that wrote them. This is the check that matters: WO0
-- established that a write can be accepted locally and still not reach the
-- game data, and that the log can agree with itself while the screen
-- disagrees with both.
--
-- Read surface, verified in resources/lua_api/openmw/types.lua:
--   types.Book.records[id].name   (BookRecord: @field #string name)
--   types.Book.records[id].text   (BookRecord: @field #string text)
-- WO0's readback used the same store for BOOK text.
--
-- This script stores nothing and implements no onSave handler, so it adds no
-- data to save games.

local types = require('openmw.types')

local TAG = '[WO1]'

local BOOK_ID = 'bk_BriefHistoryEmpire1'
local NAME_SENTINEL = 'PROBE_BOOKNAME_OK'
local FROM = 'Empire'
local TO = 'Domain'
local MARKER = 'PROBE TEXT OK -- Domain Hist.'
local MARKUP_HEAD = '<DIV ALIGN="CENTER">'

local function log(...)
    local parts = {}
    for i = 1, select('#', ...) do
        parts[i] = tostring((select(i, ...)))
    end
    print(TAG .. ' ' .. table.concat(parts, ' '))
end

local function brief(v, n)
    if v == nil then return '<nil>' end
    local s = string.gsub(tostring(v), '[\r\n]', ' ')
    n = n or 70
    if #s > n then s = string.sub(s, 1, n) .. ' ...(' .. #s .. ' chars)' end
    return s
end

local function try(fn)
    local ok, res = pcall(fn)
    if ok then return true, res end
    return false, res
end

-- Plain-text search and replace. NOT string.gsub: gsub treats its pattern as
-- a Lua pattern, where - . % ( ) [ ] + * ? ^ $ are all special, and it has no
-- plain-match flag. Only string.find takes one, as its fourth argument. The
-- mock run of this probe caught it: the marker "PROBE TEXT OK -- Domain Hist."
-- counted as zero occurrences of itself, because "--" and "." were read as
-- pattern syntax.
--
-- The WO2 transform inherits this hazard directly. Its rules table will hold
-- ordinary prose - apostrophes, hyphens, full stops - and every one of those
-- is a pattern character.
local function countPlain(haystack, needle)
    local n, pos = 0, 1
    while true do
        local s, e = string.find(haystack, needle, pos, true)
        if s == nil then return n end
        n = n + 1
        pos = e + 1
    end
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

local function run()
    log('')
    log('=== LAYER 2: independent readback from a GLOBAL script ===')
    log('  store     : types.Book.records')
    log('  record id :', BOOK_ID)

    local name = readField('name')
    log('')
    log('  P1 name   :', brief(name))
    if name == nil then
        log('  RESULT P1 : NO_READ_SURFACE')
    elseif name == NAME_SENTINEL then
        log('  RESULT P1 : SENTINEL_PRESENT  readback_global=true')
    else
        log('  RESULT P1 : ORIGINAL_VALUE  readback_global=false')
    end

    local text = readField('text')
    log('')
    if text == nil then
        log('  RESULT P2 : NO_READ_SURFACE')
    else
        local nFrom = countPlain(text, FROM)
        local nTo = countPlain(text, TO)
        local headOk = string.sub(text, 1, #MARKUP_HEAD) == MARKUP_HEAD
        log('  P2 length :', #text)
        log('  P2 head   :', brief(text, 60))
        local nMarker = countPlain(text, MARKER)
        log('  "' .. FROM .. '":', nFrom, ' "' .. TO .. '":', nTo,
            ' marker:', nMarker, ' markup head intact:', tostring(headOk))
        if nFrom == 0 and nTo > 0 and nMarker > 0 and headOk then
            log('  RESULT P2 : SUBSTITUTION_PRESENT_MARKUP_INTACT  readback_global=true')
        elseif nFrom > 0 and nTo == 0 then
            log('  RESULT P2 : ORIGINAL_VALUE  readback_global=false')
        else
            log('  RESULT P2 : MIXED - read the counts above')
        end
    end

    log('')
    log('  Neither layer can see the screen. The page render and the item')
    log('  name in the inventory are the on-screen checks, and they are the')
    log('  ones that decide.')
    log('=== Layer 2 complete ===')
end

local done = false

local function runOnce()
    if done then return end
    done = true
    local ok, err = pcall(run)
    if not ok then log('FATAL: readback aborted:', tostring(err)) end
end

return {
    engineHandlers = {
        -- Same shape WO0's readback used: onInit fires on a new game, onLoad
        -- on a loaded save, onUpdate is the backstop so this runs exactly
        -- once either way.
        onInit = function() pcall(runOnce) end,
        onLoad = function() pcall(runOnce) end,
        onUpdate = function() pcall(runOnce) end,
    },
}
