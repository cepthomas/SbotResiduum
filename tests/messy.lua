--[[
    Unit tests for the utils.
    Run like: lua pnut_runner.lua test_utils
--]]


ut = require("utils")

-- Create the namespace/module.
local M={}

-----------------------------------------------------------------------------
function M.setup(pn)         pn.UT_INFO("setup()!!!")       end

-----------------------------------------------------------------------------
       function M.teardown(pn)
-- pn.UT_INFO("teardown()!!!")
end

-----------------------------------------------------------------------------
function M.suite_utils(pn)
pn.UT_INFO("Test all functions in utils.lua")

-- Test strtrim().
local s = "  I have whitespace    "
pn.UT_EQUAL(ut.strtrim(s), "I have whitespace")

-- Test strjoin().
local l = {123, "orange monkey", 765.12, "BlueBlueBlue", "ano", "ther", 222}
pn.UT_EQUAL(ut.strjoin("XXX", l), 
"123XXXorange monkeyXXX765.12XXXBlueBlueBlueXXXanoXXXtherXXX222")

line_indent = 5

function deal_indent(line, delta)
        line.set_indent(indent + delta)
end

function inc_indent(delta)
 if line_indent + delta > 1 then
return
    end

    if line_indent + delta < -1 then
        return
    end
end


-- Test dump_table().
tt = { aa="pt1", bb=90901, arr={"qwerty", 777, temb1={ jj="pt8", b=true, temb2={ num=1.517, dd="strdd" } }, intx=5432}}
local sts = ut.dump_table(tt, 0)
s = ut.strjoin('\n', sts)
pn.UT_EQUAL(#s, 250)

end

-----------------------------------------------------------------------------
-- Return the module.
return M
