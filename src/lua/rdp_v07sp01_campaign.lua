local loader = require "lua_scripts.rdp_v07sp01_loader"
local scripting = require "lua_scripts.EpisodicScripting"
local loaded = {}

local function native(symbol)
    local ok, result = pcall(function()
        local fn = loaded[symbol]
        if not fn then
            fn = loader.load(symbol)
            if type(fn) ~= "function" then return false end
            loaded[symbol] = fn
        end
        fn()
        return true
    end)
    return ok and result
end

-- Remove only this project's old observer registrations from existing saves.
-- This version never registers or supplies a custom battlefield script.
local function cleanup_legacy()
    for _, key in ipairs({"rdp_v03_native_observe", "rdp_v04_native_merge", "rdp_v05_native_merge"}) do
        pcall(function() scripting.game_interface:remove_custom_battlefield(key) end)
    end
end

local function pending(context)
    pcall(function()
        cleanup_legacy()
        native("rdp_disable")
        local model = scripting.game_interface:model()
        if model:is_multiplayer() then return end
        local pb = context:pending_battle()
        local battle_type = pb:battle_type()
        local settlement_assault = battle_type == "settlement_standard" or
            battle_type == "settlement_unfortified" or battle_type == "town_normal" or
            battle_type == "fort_standard"
        local general_battle = battle_type == "land_normal" or battle_type == "naval_normal" or
            battle_type == "settlement_sally" or battle_type == "coastal_battle" or
            battle_type == "naval_breakout"
        if not general_battle and not settlement_assault then return end
        if not pb:has_attacker() or not pb:has_defender() then return end
        if battle_type == "land_normal" and pb:has_contested_garrison() then settlement_assault = true end
        local a, d = pb:attacker():faction(), pb:defender():faction()
        if not a:is_human() and not d:is_human() then return end
        native(settlement_assault and "rdp_install_settlement" or "rdp_install")
    end)
end

scripting.AddEventCallBack("PendingBattle", pending)
scripting.AddEventCallBack("UICreated", function()
    pcall(function()
        cleanup_legacy()
        native("rdp_disable")
        local pb = scripting.game_interface:model():pending_battle()
        if pb:is_active() then pending({pending_battle = function() return pb end}) end
    end)
end)
scripting.AddEventCallBack("BattleCompleted", function()
    cleanup_legacy()
    native("rdp_disable")
end)
-- Prepare on campaign script load; retry from native calls if preparation fails.
loader.prepare()
return true
