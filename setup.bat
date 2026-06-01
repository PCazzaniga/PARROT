@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo -- Starting Setup --
echo.

echo Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install dependencies. Make sure Python and pip are installed.
    pause
    exit /b 1
)

echo.
echo Downloading spaCy language model...
python -m spacy download en_core_web_sm
if %errorlevel% neq 0 (
    echo Failed to download spaCy language model.
    pause
    exit /b 1
)

echo.
if not exist "parrot_bot\bot_settings.json" (
    echo Creating default settings file...
    (
        echo {
        echo     "REPLACEMENT_WORD" : "word",
        echo     "INTENSITY" : 50,
        echo     "WAIT_SECONDS" : 30,
        echo     "WAIT_MESSAGES" : 10,
        echo     "NOTARGET_MODE" : true,
        echo     "VIP_IDS" : [],
        echo     "IGNORED_IDS" : [],
        echo     "SPECIAL_CASES" : {
        echo         "RECURSIVE" : "^<WORD^>²",
        echo         "PATTERNS" : [
        echo         {
        echo             "MATCH" : "chat",
        echo             "SAY" : "^<WORD^> nation"
        echo         },
        echo         {
        echo             "MATCH" : "mods",
        echo             "SAY" : "fun police"
        echo         }
        echo     ]},
        echo     "ADVANCED_MODE": false,
        echo     "MAX_TARGET_LENGTH": 120
        echo }
    ) > "parrot_bot\bot_settings.json"
) else (
    echo Found existing settings file, continuing.
)

if not exist "parrot_bot\PRIVATE_config.json" (
    echo Creating empty configuration file...
    (
        echo {
        echo     "BOT_ACCOUNT_ID": 0,
        echo     "APP_CLIENT_ID": "",
        echo     "APP_CLIENT_SECRET": "",
        echo     "CHANNEL_ACCOUNT_ID": 0,
        echo     "APP_OAUTH_TOKEN": {
        echo         "TOKEN": null,
        echo         "REFRESH_TOKEN": null,
        echo         "EXPIRES_AT": null,
        echo         "FETCHED": null
        echo     }
        echo }
    ) > "parrot_bot\PRIVATE_config.json"
) else (
    echo Found existing configuration file, continuing.
)

echo.
echo -- Setup complete --
echo.
echo Before launching the application, open parrot_bot\PRIVATE_config.json and fill in:
echo   - BOT_ACCOUNT_ID    : the numeric Twitch user ID of the chatbot account
echo   - APP_CLIENT_ID     : the Client ID of your registered Twitch application
echo   - APP_CLIENT_SECRET : the Client Secret of your registered Twitch application
echo   - CHANNEL_ACCOUNT_ID: the numeric Twitch user ID of the channel to operate in
echo.
echo Once configured, run launch.bat to start the chatbot.
echo.
pause