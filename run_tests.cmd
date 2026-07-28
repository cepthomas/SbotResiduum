
:: General test runner for all sbot stuff.

cls
echo off

pushd ..\SbotDev\tests
python -m unittest test_common
popd

rem pushd ..\SbotResiduum\tests
rem python -m unittest test_residuum
rem popd

pushd ..\Notr\tests
python -m unittest test_notr test_table
popd

