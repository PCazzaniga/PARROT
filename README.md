# PARROT
**P**hrase **A**ltering & **R**epeating **R**obot **O**n **T**witch

## About
PARROT is a Twitch chatbot that can randomly repeat messages while smartly replacing grammatical subjects and objects for humour and entertainment, inspired by the late [buttsbot](http://www.twitch.tv/buttsbot).

## Installation

### Requirements
- Python 3.10 or higher.
- A Twitch account for the chatbot.
- A Twitch application registered at [dev.twitch.tv](https://dev.twitch.tv).
- **Consent from the owner of the channel the chatbot will operate in.**

### 1. Clone the repository
```bash
> git clone https://github.com/<name>/<repo>.git
> cd repo
```
Alternatively, manually download the files from this repository.

### 2. Install dependencies
```bash
> pip install -r requirements.txt
> python -m spacy download en_core_web_sm
```
Alternatively, run `setup.bat` (Windows) or `setup.sh` (Mac/Linux).

### 3. Configure the chatbot
Change the following values in `parrot_bot\PRIVATE_config.json`:  
 - BOT_ACCOUNT_ID: numeric User ID of the chatbot's Twitch account (you can get it using online tools like [this](https://streamcharts.com/tools/convert-username)).  
 - APP_CLIENT_ID: alphanumeric Client ID of the registered Twitch application.  
 - APP_CLIENT_SECRET: alphanumeric Client Secret of the registered Twitch application.
 - CHANNEL_ACCOUNT_ID: numeric User ID of the Twitch channel the chatbot will operate in.

(Please note that `PRIVATE_config.json` will contain sensitive information of your application and should never be disclosed !)

Optionally, you can also manually change the default values in `parrot_bot\bot_settings.json` but that can be done later directly using the application.

### 4. Run the chatbot
```bash
> python -m <package>
```
Alternatively, run `launch.bat` (Windows) or `launch.sh` (Mac/Linux).

### 5. Authorize the chatbot
On the very first run, the application will need to get a token from Twitch and will print a URL in the console.  
Open it in a browser while logged in as the chatbot account and complete the authorization.  
The token will then be saved automatically to the configuration file.

## Usage

Once the chatbot is running it will listen to the stream chat and occasionally select a message to modify and repeat.  
For example, an user may send:
```
I love this videogame !!!
```
and the chatbot might then repeat:
```
I love this stream !!!
```
---
From the chat itself the channel owner, its moderators and selected users can customize the chatbot's behaviour by @ing the chatbot and sending one of the following commands:  
 - **!commands**, to see the list of available commands.  
 - **!help**, to see the meaning and syntax of a specific command.  
 - !advanced, to select the behaviour when the keyword and the original sentence don't match plurality (for example, if the the keyword is "banana**s**" the message "I want an apple" will become "I want a banana" or "I want some bananas" depending on the selected mode).  
 - !ignore and !unignore, to make or not a user untargetable by the chatbot. By default the chatbot ignores only messages from itself and those that begin with a command (even for other chatbots) or contain any @mention.  
 - !intensity, to set how much the chatbot can alter the messages it selects.  
 - !interval, to set the minimum number of messages the chatbot has to wait between activations.  
 - **!keyword**, to set the word used to alter messages.  
 - !length, to set the chatbot to ignore messages above a certain number of characters.  
 - !notarget, to prevent or not the chatbot from modifying consecutive messages from the same user.  
 - !timer, to set the minimum cooldown the chatbot has to wait between activations.  
 - !try, to test the chatbot with a provided message.  
 - !turnoff, to remotely shutdown the chatbot.  
 - !vip and !unvip to allow or not a user to use these commands even if they're not a moderator.  

 All of these settings are automatically saved in `bot_settings.json` to persist when the chatbot goes offline.  

 ---
 Additionally, there are some settings that can only be customized by manually modifying `bot_settings.json`, namely special hardcoded, case-sensitive, replacements that will always be performed if found in a selected message:
 - RECURSIVE to set the replacement text for when the current keyword itself is found in a sentence.
 - PATTERNS to set any "original" - "replacement" pairs of text.  
 
 In the replacement texts the notation `<WORD>` can be used as a placeholder for whatever the keyword will be when that special replacement is used (for example, "my \<WORD>" will be automatically output as "my banana" if the current keyword is "banana" and "my apple" if it's "apple").
