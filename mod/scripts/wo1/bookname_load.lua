-- Work Order 1 -- book probe, Layer 1 (LOAD context).
--
-- Two questions, one game run:
--
--   P1. Is BOOK `name` writable? WO0 wrote BOOK `text` only and assumed the
--       name because it shares a content sub-package. 4 keyword records and
--       the routing table's only unmeasured assumption ride on that guess.
--
--   P2. Does a book still RENDER after an in-place substring substitution?
--       WO0 replaced a whole `text` field with a bare sentinel and the page
--       came up blank, because the vanilla pseudo-HTML markup went with it.
--       The rule that followed - substitute inside the field, never replace
--       it - is what the WO2 transform is built on. This rehearses it on one
--       book so the rule is measured rather than assumed.
--
-- API surfaces, checked against the shipped 0.51 stubs before use:
--   resources/lua_api/openmw/content.lua
--     "A mutable list of all BookRecords" -> content.books.records
--   resources/lua_api/openmw/types.lua
--     BookRecord: @field #string name, @field #string text
-- In-place mutation (rec.field = x) is the pattern the engine's own LOAD
-- script esmfallbacks.lua uses, and the one WO0 confirmed on BOOK text.
--
-- Nothing here is invented, every access is wrapped in pcall, and the script
-- stores nothing in save games.

local content = require('openmw.content')

local TAG = '[WO1]'

-- Target: sits in Seyda Neen, Census and Excise Office - the room a new game
-- starts in, so the on-screen check costs a minute.
local BOOK_ID = 'bk_BriefHistoryEmpire1'
local NAME_SENTINEL = 'PROBE_BOOKNAME_OK'

-- P2 substitution. Equal length, so it also honours the project rule that a
-- replacement is never longer than what it replaces. "Empire" is in the title
-- line on page one, so the result is legible at a glance.
local FROM = 'Empire'
local TO = 'Domain'

-- The opening of the vanilla markup. If the page renders and this is intact,
-- the substitution left the formatting alone.
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

-- Count non-overlapping plain-text occurrences. gsub returns the count and is
-- given `true` for plain matching, so no character here is treated as a
-- pattern.
local function countPlain(haystack, needle)
    local _, n = string.gsub(haystack, needle, needle)
    return n
end

local function findRecord(recs, id)
    for _, variant in ipairs({ id, string.lower(id) }) do
        local ok, rec = try(function() return recs[variant] end)
        if ok and rec ~= nil then return rec, variant end
    end
    return nil, nil
end

----------------------------------------------------------------------------

local function run()
    log('')
    log('###############################################')
    log('# WORK ORDER 1 -- book name and render probe  #')
    log('# Layer 1: writes from the LOAD context       #')
    log('###############################################')

    local ok, books = try(function() return content.books end)
    if not ok or books == nil then
        log('RESULT P1 : NO_API_SURFACE (content.books absent)')
        log('RESULT P2 : NO_API_SURFACE')
        return
    end

    local okr, recs = try(function() return books.records end)
    if not okr or recs == nil then
        log('RESULT P1 : NO_API_SURFACE (content.books.records absent)')
        log('RESULT P2 : NO_API_SURFACE')
        return
    end

    local rec, usedId = findRecord(recs, BOOK_ID)
    if rec == nil then
        log('RESULT P1 : RECORD_NOT_FOUND', BOOK_ID)
        log('RESULT P2 : RECORD_NOT_FOUND')
        return
    end
    log('')
    log('target book:', usedId)

    ------------------------------------------------------------------
    -- P1: BOOK name
    ------------------------------------------------------------------

    log('')
    log('=== P1  BOOK name ===')

    local okOld, oldName = try(function() return rec.name end)
    log('  old name  :', okOld and brief(oldName) or '<read failed>')
    log('  sentinel  :', NAME_SENTINEL)

    if okOld and oldName ~= nil and #NAME_SENTINEL > #oldName then
        -- Project rule: a replacement is never longer than what it replaces.
        log('  RESULT P1 : ABORTED (sentinel longer than the vanilla name)')
    else
        local okWrite, werr = try(function() rec.name = NAME_SENTINEL end)
        if not okWrite then
            log('  RESULT P1 : WRITE_THREW')
            log('  detail    :', tostring(werr))
        else
            -- Re-fetch rather than reuse the handle, so a write that only
            -- touched a local copy shows up here as a mismatch.
            local okBack, nowName = try(function()
                local r2 = findRecord(recs, BOOK_ID)
                if r2 == nil then return nil end
                return r2.name
            end)
            if not okBack then
                log('  RESULT P1 : WRITE_OK_READBACK_THREW')
                log('  detail    :', tostring(nowName))
            elseif nowName == NAME_SENTINEL then
                log('  RESULT P1 : WRITE_OK  write_ok=true readback_load=true')
            else
                log('  RESULT P1 : WRITE_SILENTLY_REVERTED')
                log('  now reads :', brief(nowName))
            end
        end
    end

    ------------------------------------------------------------------
    -- P2: BOOK text, substring substitution with the markup preserved
    ------------------------------------------------------------------

    log('')
    log('=== P2  BOOK text, substring substitution ===')
    log('  rule      : substitute inside the field, never replace the field')

    local okText, oldText = try(function() return rec.text end)
    if not okText or oldText == nil then
        log('  RESULT P2 : READ_FAILED')
        return
    end

    local beforeFrom = countPlain(oldText, FROM)
    local beforeTo = countPlain(oldText, TO)
    log('  old length:', #oldText)
    log('  old head  :', brief(oldText, 60))
    log('  "' .. FROM .. '" before:', beforeFrom, ' "' .. TO .. '" before:', beforeTo)

    if beforeFrom == 0 then
        log('  RESULT P2 : ABORTED (nothing to substitute - wrong book?)')
        return
    end

    local newText = string.gsub(oldText, FROM, TO)

    -- Two guards before the write, both project rules.
    if #newText > #oldText then
        log('  RESULT P2 : ABORTED (replacement is longer than the original)')
        return
    end
    if string.sub(newText, 1, #MARKUP_HEAD) ~= MARKUP_HEAD then
        log('  RESULT P2 : ABORTED (substitution damaged the markup head)')
        return
    end
    log('  new length:', #newText, '(delta ' .. (#newText - #oldText) .. ')')

    local okWrite, werr = try(function() rec.text = newText end)
    if not okWrite then
        log('  RESULT P2 : WRITE_THREW')
        log('  detail    :', tostring(werr))
        return
    end

    local okBack, nowText = try(function()
        local r2 = findRecord(recs, BOOK_ID)
        if r2 == nil then return nil end
        return r2.text
    end)
    if not okBack or nowText == nil then
        log('  RESULT P2 : WRITE_OK_READBACK_THREW')
        return
    end

    local afterFrom = countPlain(nowText, FROM)
    local afterTo = countPlain(nowText, TO)
    log('  "' .. FROM .. '" after :', afterFrom, ' "' .. TO .. '" after :', afterTo)
    log('  head now  :', brief(nowText, 60))

    if nowText == newText then
        log('  RESULT P2 : WRITE_OK  write_ok=true readback_load=true')
        log('  NOTE      : the log cannot say whether the PAGE renders.')
        log('              Open the book in game. A blank page here means')
        log('              substring substitution is not enough either.')
    else
        log('  RESULT P2 : WRITE_SILENTLY_REVERTED')
    end

    log('')
    log('=== Layer 1 complete. Layer 2 readback runs when a game starts. ===')
end

return {
    engineHandlers = {
        onContentFilesLoaded = function()
            local ok, err = pcall(run)
            if not ok then
                log('FATAL: probe aborted:', tostring(err))
            end
        end,
    },
}
