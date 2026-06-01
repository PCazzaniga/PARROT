#!/bin/bash
cd "$(dirname "$0")"

echo "-- Starting Setup --"
echo

echo "Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Failed to install dependencies. Make sure Python and pip are installed."
    exit 1
fi

echo
echo "Downloading spaCy language model..."
python -m spacy download en_core_web_sm
if [ $? -ne 0 ]; then
    echo "Failed to download spaCy language model."
    exit 1
fi

echo
if [ ! -f "parrot_bot/bot_settings.json" ]; then
    echo "Creating default bot_settings.json..."
    cat > "parrot_bot/bot_settings.json" << 'EOF'
{
    "REPLACEMENT_WORD" : "word",
    "INTENSITY" : 50,
    "WAIT_SECONDS" : 30,
    "WAIT_MESSAGES" : 10,
    "NOTARGET_MODE" : true,
    "VIP_IDS" : [],
    "IGNORED_IDS" : [],
    "SPECIAL_CASES" : {
        "RECURSIVE" : "<WORD>²",
        "PATTERNS" : [
        {
            "MATCH" : "chat",
            "SAY" : "<WORD> nation"
        },
        {
            "MATCH" : "mods",
            "SAY" : "fun police"
        }
    ]},
    "ADVANCED_MODE": false,
    "MAX_TARGET_LENGTH": 120
}
EOF
else
    echo "Found existing settings file, continuing."
fi

if [ ! -f "parrot_bot/PRIVATE_config.json" ]; then
    echo "Creating empty configuration file..."
    cat > "parrot_bot/PRIVATE_config.json" << 'EOF'
{
    "BOT_ACCOUNT_ID": 0,
    "APP_CLIENT_ID": "",
    "APP_CLIENT_SECRET": "",
    "CHANNEL_ACCOUNT_ID": 0,
    "APP_OAUTH_TOKEN": {
        "TOKEN": null,
        "REFRESH_TOKEN": null,
        "EXPIRES_AT": null,
        "FETCHED": null
    }
}
EOF
else
    echo "Found existing configuration file, continuing."
fi

echo
echo "-- Setup complete --"
echo
echo "Before launching the application, open parrot_bot\PRIVATE_config.json and fill in:"
echo "  - BOT_ACCOUNT_ID    : the numeric Twitch user ID of the chatbot account"
echo "  - APP_CLIENT_ID     : the Client ID of your registered Twitch application"
echo "  - APP_CLIENT_SECRET : the Client Secret of your registered Twitch application"
echo "  - CHANNEL_ACCOUNT_ID: the numeric Twitch user ID of the channel to operate in"
echo
echo "Once configured, run launch.sh to start the chatbot."
echo