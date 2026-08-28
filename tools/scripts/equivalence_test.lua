-- Equivalence test: does the shipped Lua engine produce exactly what the
-- Python engine produced?
--
-- Two implementations of the same rules, in two languages, are two chances to
-- get boundaries, case shapes and markup spans subtly different. The Python one
-- is what every report and every review in this project is based on; the Lua
-- one is what the player actually gets. If they disagree, the reports describe
-- a mod that does not exist.
--
-- Run through tools/scripts/equivalence_test.py, which supplies the fixture
-- path and loads this under OpenMW's own lua51.dll.

local fixturePath = FIXTURE_PATH
local rulesPath = RULES_PATH

-- The applier is written for the game, where it requires openmw.content. Here
-- only its matching half is under test, so the file is read and the functions
-- are lifted out by loading it with a stubbed require.
local realRequire = require
local rulesModule = dofile(rulesPath)
_G.require = function(name)
    if name == 'openmw.content' then return { } end
    if name == 'scripts.rewrite.rules' then return rulesModule end
    return realRequire(name)
end

-- apply.lua returns a handler table, so the internals are not reachable from
-- outside. The test loads the source and appends an export instead of
-- duplicating the logic, which would defeat the purpose.
local f = assert(io.open(APPLY_PATH, 'r'))
local src = f:read('*a')
f:close()
src = src:gsub('return {%s*\n%s*engineHandlers.*$', '')
src = src .. '\nreturn { applyAll = applyAll, shape = shape }\n'
local chunk = assert(loadstring(src, 'apply.lua'))
local engine = chunk()

-- Minimal JSON reader for the fixture: it is machine-written, ASCII-escaped
-- and flat, so a full parser is not needed.
local function readFixture(path)
    local fh = assert(io.open(path, 'rb'))
    local text = fh:read('*a')
    fh:close()
    local cases, pos = {}, 1
    while true do
        local s = string.find(text, '{"code":', pos, true)
        if s == nil then break end
        local e = string.find(text, '{"code":', s + 1, true) or (#text + 1)
        local blob = string.sub(text, s, e - 1)
        local function grab(field)
            local a = string.find(blob, '"' .. field .. '":"', 1, true)
            if a == nil then return nil end
            a = a + #field + 4
            local out, i = {}, a
            while i <= #blob do
                local c = string.sub(blob, i, i)
                if c == '\\' then
                    local n = string.sub(blob, i + 1, i + 1)
                    if n == 'n' then out[#out + 1] = '\n'
                    elseif n == 'r' then out[#out + 1] = '\r'
                    elseif n == 't' then out[#out + 1] = '\t'
                    elseif n == 'u' then
                        local hex = string.sub(blob, i + 2, i + 5)
                        out[#out + 1] = '\\u' .. hex
                        i = i + 4
                    else out[#out + 1] = n end
                    i = i + 2
                elseif c == '"' then
                    break
                else
                    out[#out + 1] = c
                    i = i + 1
                end
            end
            return table.concat(out)
        end
        cases[#cases + 1] = {
            code = grab('code'), id = grab('id'), field = grab('field'),
            before = grab('before'), after = grab('after'),
        }
        pos = e
    end
    return cases
end

local cases = readFixture(fixturePath)
local pass, fail = 0, 0
for _, c in ipairs(cases) do
    local got = engine.applyAll(c.before, c.id)
    if got == c.after then
        pass = pass + 1
    else
        fail = fail + 1
        if fail <= 5 then
            print('MISMATCH ' .. c.code .. ' ' .. c.id .. ' ' .. c.field)
            -- Print the neighbourhood of the first differing byte only.
            local i = 1
            while i <= math.min(#got, #c.after) and
                  string.sub(got, i, i) == string.sub(c.after, i, i) do
                i = i + 1
            end
            local a = math.max(1, i - 60)
            print('  python: ' .. string.sub(c.after, a, i + 60))
            print('  lua   : ' .. string.sub(got, a, i + 60))
        end
    end
end
print('cases ' .. #cases .. '  pass ' .. pass .. '  fail ' .. fail)
if fail > 0 then os.exit(1) end
