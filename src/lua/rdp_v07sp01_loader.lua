-- V07 single-pack trial: deploy only the embedded, byte-identical native DLL.
-- No network, shell commands, game observers, diagnostic callbacks or logs.
local M = {}
local filename = "rdp_v07sp01_93470fef577ebff5.dll"
local target = ".\\" .. filename
local staging = target .. ".rdp-tmp"
local expected_size = 10092
local expected
local ready = false
local allowed = {rdp_install = true, rdp_install_settlement = true, rdp_disable = true}

-- Read at most the expected length plus one to reject oversized files.
-- Missing files and all other I/O failures are distinguished by errno 2.
local function read_file(path, limit)
    local ok, file, _, errno = pcall(io.open, path, "rb")
    if not ok then return nil, "error" end
    if not file then return nil, errno == 2 and "missing" or "error" end
    local read_ok, data = pcall(file.read, file, limit)
    local close_ok, closed = pcall(file.close, file)
    if not read_ok or type(data) ~= "string" or not close_ok or not closed then
        return nil, "error"
    end
    return data, "present"
end

local function remove_staging()
    pcall(function() os.remove(staging) end)
end

local function prepare_inner()
    if ready then return true end
    if not expected then
        local ok, bytes = pcall(require, "lua_scripts.rdp_v07sp01_payload")
        if not ok or type(bytes) ~= "string" or #bytes ~= expected_size or bytes:sub(1, 2) ~= "MZ" then
            return false
        end
        expected = bytes
    end
    -- This first trial supports the normal Rome2.exe working directory only.
    -- It never guesses an installation path or changes process search paths.
    local marker = read_file(".\\Rome2.exe", 2)
    if marker ~= "MZ" then return false end

    local current, state = read_file(target, expected_size + 1)
    if current == expected then ready = true; return true end
    -- A different or unreadable existing file is left untouched.
    if state ~= "missing" then return false end
    if type(os.rename) ~= "function" or type(os.remove) ~= "function" then return false end

    local opened, file = pcall(io.open, staging, "wb")
    if not opened or not file then return false end
    local write_ok, written = pcall(file.write, file, expected)
    local close_ok, closed = pcall(file.close, file)
    if not write_ok or not written or not close_ok or not closed then
        remove_staging(); return false
    end
    local staged = read_file(staging, expected_size + 1)
    if staged ~= expected then remove_staging(); return false end

    -- Recheck before committing. Windows rename does not replace an existing
    -- destination; concurrent instances are not supported by this trial.
    current, state = read_file(target, expected_size + 1)
    if current == expected then remove_staging(); ready = true; return true end
    if state ~= "missing" then remove_staging(); return false end
    local rename_ok, renamed = pcall(os.rename, staging, target)
    if not rename_ok or not renamed then
        remove_staging()
        current = read_file(target, expected_size + 1)
        if current == expected then ready = true; return true end
        return false
    end
    current = read_file(target, expected_size + 1)
    if current ~= expected then return false end
    ready = true
    return true
end

function M.prepare()
    local ok, result = pcall(prepare_inner)
    return ok and result == true
end

function M.load(symbol)
    if not allowed[symbol] or not M.prepare() then return nil end
    local current = read_file(target, expected_size + 1)
    if current ~= expected then ready = false; return nil end
    local ok, fn = pcall(package.loadlib, target, symbol)
    if not ok or type(fn) ~= "function" then return nil end
    return fn
end

return M
