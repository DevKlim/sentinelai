@echo off

REM Test script for merged containers

echo Testing EIDO-IDX merged container...

REM Build the EIDO-IDX merged container
echo Building EIDO-IDX merged container...
docker build -t eido-idx-merged-test ./eido-idx-merged

REM Test each service
echo Testing EIDO API service...
docker run --rm -d --name eido-api-test -e SERVICE=eido-api eido-idx-merged-test
timeout /t 10 /nobreak >nul
docker logs eido-api-test | more
docker stop eido-api-test

echo Testing IDX UI service...
docker run --rm -d --name idx-ui-test -e SERVICE=idx-ui eido-idx-merged-test
timeout /t 10 /nobreak >nul
docker logs idx-ui-test | more
docker stop idx-ui-test

echo Testing SentinelAI merged container...

REM Build the SentinelAI merged container
echo Building SentinelAI merged container...
docker build -t sentinelai-merged-test ./sentinelai-merged

REM Test each service
echo Testing SentinelAI API service...
docker run --rm -d --name sentinelai-api-test -e SERVICE=api sentinelai-merged-test
timeout /t 10 /nobreak >nul
docker logs sentinelai-api-test | more
docker stop sentinelai-api-test

echo Testing SentinelAI Dashboard service...
docker run --rm -d --name sentinelai-dashboard-test -e SERVICE=dashboard sentinelai-merged-test
timeout /t 10 /nobreak >nul
docker logs sentinelai-dashboard-test | more
docker stop sentinelai-dashboard-test

echo All tests completed!