import discord
from discord.ext import commands, tasks
import datetime
import json
import os
import asyncio
import random
import secrets
import hashlib
import base64
import pytz
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()  # this loads the .env file so your secrets can be read

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Load saved settings (per server)
if os.path.exists("settings.json"):
    with open("settings.json", "r") as f:
        server_settings = json.load(f)
else:
    server_settings = {}

# Load last messages for deletion
if os.path.exists("last_messages.json"):
    with open("last_messages.json", "r") as f:
        last_messages = json.load(f)
else:
    last_messages = {}

# Load sticky messages for vent channels
if os.path.exists("sticky_messages.json"):
    with open("sticky_messages.json", "r") as f:
        sticky_messages = json.load(f)
else:
    sticky_messages = {}

# Load dismissed users
if os.path.exists("dismissed_users.json"):
    with open("dismissed_users.json", "r") as f:
        dismissed_users = json.load(f)
else:
    dismissed_users = {}

# Load anonymous logs (encrypted)
if os.path.exists("anon_logs.json"):
    with open("anon_logs.json", "r") as f:
        anon_logs = json.load(f)
else:
    anon_logs = {}

# Load access codes for log viewing
if os.path.exists("access_codes.json"):
    with open("access_codes.json", "r") as f:
        access_codes = json.load(f)
else:
    access_codes = {}

# Load moderator access tracking
if os.path.exists("moderator_access.json"):
    with open("moderator_access.json", "r") as f:
        moderator_access = json.load(f)
else:
    moderator_access = {}

# Track setup sessions
setup_sessions = {}

checkin_message = (
    "Hey {ping}! Please let us know how you're feeling today 💖\n\n"
    "❤️ - I'm doing amazing today!\n"
    "🧡 - I'm feeling positive and good about life\n"
    "💛 - I'm good\n"
    "💚 - I could be better, could be worse but I'm okay!\n"
    "💙 - I'm having a down day\n"
    "💜 - I feel lost and broken\n"
    "🖤 - I'm in a really dark place today\n"
    "🤍 - I'd like someone to DM me if they could...\n\n"
    "Remember, you're not alone. You can always talk in {support_channel} 🫂\n\n"
    "Need to vent anonymously? Use the button below! 👇"
)

emojis = ["❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍"]

def save_data():
    """Save all data to files"""
    with open("settings.json", "w") as f:
        json.dump(server_settings, f, indent=2)
    with open("last_messages.json", "w") as f:
        json.dump(last_messages, f, indent=2)
    with open("sticky_messages.json", "w") as f:
        json.dump(sticky_messages, f, indent=2)
    with open("dismissed_users.json", "w") as f:
        json.dump(dismissed_users, f, indent=2)
    with open("anon_logs.json", "w") as f:
        json.dump(anon_logs, f, indent=2)
    with open("access_codes.json", "w") as f:
        json.dump(access_codes, f, indent=2)
    with open("moderator_access.json", "w") as f:
        json.dump(moderator_access, f, indent=2)

def log_anonymous_message(guild_id: str, message_content: str, channel_id: str, user_id: str, username: str, display_name: str):
    """Log anonymous message with user information for moderation"""
    timestamp = datetime.datetime.now().isoformat()
    
    # Create a hash of the message for identification
    message_hash = hashlib.sha256(message_content.encode()).hexdigest()[:16]
    
    # Encode the message content
    encoded_message = base64.b64encode(message_content.encode()).decode()
    
    # Encode user information for security
    encoded_username = base64.b64encode(username.encode()).decode()
    encoded_display_name = base64.b64encode(display_name.encode()).decode()
    
    log_entry = {
        "timestamp": timestamp,
        "guild_id": guild_id,
        "channel_id": channel_id,
        "user_id": user_id,
        "encoded_username": encoded_username,
        "encoded_display_name": encoded_display_name,
        "message_hash": message_hash,
        "encoded_content": encoded_message
    }
    
    if guild_id not in anon_logs:
        anon_logs[guild_id] = []
    
    anon_logs[guild_id].append(log_entry)
    save_data()

def generate_access_code(guild_id: str) -> str:
    """Generate a one-time access code for log viewing"""
    code = secrets.token_hex(16)
    
    if guild_id not in access_codes:
        access_codes[guild_id] = {}
    
    access_codes[guild_id][code] = {
        "created": datetime.datetime.now().isoformat(),
        "used": False
    }
    
    save_data()
    return code

def use_access_code(guild_id: str, code: str, user_id: str) -> bool:
    """Use an access code and track who used it"""
    if guild_id not in access_codes or code not in access_codes[guild_id]:
        return False
    
    if access_codes[guild_id][code]["used"]:
        return False
    
    # Mark code as used
    access_codes[guild_id][code]["used"] = True
    access_codes[guild_id][code]["used_by"] = user_id
    access_codes[guild_id][code]["used_at"] = datetime.datetime.now().isoformat()
    
    # Track moderator access
    if guild_id not in moderator_access:
        moderator_access[guild_id] = []
    
    moderator_access[guild_id].append({
        "user_id": user_id,
        "accessed_at": datetime.datetime.now().isoformat(),
        "access_code": code
    })
    
    save_data()
    return True

class CheckinVentView(discord.ui.View):
    """View for daily check-in with anonymous vent button"""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🫣 Vent Anonymously', style=discord.ButtonStyle.secondary, custom_id='checkin_vent')
    async def anonymous_vent(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle anonymous vent button clicks from check-in"""
        guild_id = str(interaction.guild.id)
        
        # Check if server has vent channel configured
        if guild_id not in server_settings or 'vent_channel' not in server_settings[guild_id]:
            await interaction.response.send_message(
                "❌ Anonymous venting is not set up for this server. Please ask an admin to run the setup wizard.",
                ephemeral=True
            )
            return
            
        await interaction.response.send_modal(AnonymousVentModal(from_checkin=True))

class TimezoneSelect(discord.ui.Select):
    """Timezone selection dropdown"""
    def __init__(self):
        # Popular timezone options
        options = [
            discord.SelectOption(label="UTC (Universal Time)", value="UTC", description="UTC+0"),
            discord.SelectOption(label="Eastern Time (US)", value="US/Eastern", description="UTC-5/-4"),
            discord.SelectOption(label="Central Time (US)", value="US/Central", description="UTC-6/-5"),
            discord.SelectOption(label="Mountain Time (US)", value="US/Mountain", description="UTC-7/-6"),
            discord.SelectOption(label="Pacific Time (US)", value="US/Pacific", description="UTC-8/-7"),
            discord.SelectOption(label="Alaska Time", value="US/Alaska", description="UTC-9/-8"),
            discord.SelectOption(label="Hawaii Time", value="US/Hawaii", description="UTC-10"),
            discord.SelectOption(label="London (GMT/BST)", value="Europe/London", description="UTC+0/+1"),
            discord.SelectOption(label="Paris/Berlin/Rome", value="Europe/Paris", description="UTC+1/+2"),
            discord.SelectOption(label="Moscow", value="Europe/Moscow", description="UTC+3"),
            discord.SelectOption(label="Dubai", value="Asia/Dubai", description="UTC+4"),
            discord.SelectOption(label="Mumbai/Delhi", value="Asia/Kolkata", description="UTC+5:30"),
            discord.SelectOption(label="Bangkok", value="Asia/Bangkok", description="UTC+7"),
            discord.SelectOption(label="Shanghai/Beijing", value="Asia/Shanghai", description="UTC+8"),
            discord.SelectOption(label="Tokyo", value="Asia/Tokyo", description="UTC+9"),
            discord.SelectOption(label="Sydney", value="Australia/Sydney", description="UTC+10/+11"),
            discord.SelectOption(label="Auckland", value="Pacific/Auckland", description="UTC+12/+13"),
        ]
        super().__init__(placeholder="Choose your timezone...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)
        
        if guild_id not in setup_sessions or user_id not in setup_sessions[guild_id]:
            await interaction.response.send_message("❌ Setup session not found. Please start over with `!setup`", ephemeral=True)
            return
            
        session = setup_sessions[guild_id][user_id]
        
        # Save timezone selection
        session['data']['timezone'] = self.values[0]
        session['step'] = 7
        
        # Get timezone display name
        selected_tz = next((opt.label for opt in self.options if opt.value == self.values[0]), self.values[0])
        
        # Move to time selection step
        embed = discord.Embed(
            title="Setup Wizard - Step 7/7 ⏰",
            description=f"**Perfect! Timezone set to {selected_tz}** 🌍\n\n**Final step! When should I send the daily check-ins?** 🕐\n\nPick a time that works for your community. Maybe when people are having their morning coffee, or when they're winding down for the day.\n\n**Please enter a time in 24-hour format:**\n• Examples: `09:00`, `14:30`, `20:15`\n• Must be in HH:MM format",
            color=0x7289da
        )
        embed.set_footer(text="Example: 09:00 for 9 AM")
        
        await interaction.response.edit_message(embed=embed, view=None)

class TimezoneView(discord.ui.View):
    """View containing timezone selector"""
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(TimezoneSelect())

class AnonymousVentView(discord.ui.View):
    """Persistent view for anonymous venting button"""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🫣 Vent Anonymously', style=discord.ButtonStyle.secondary, custom_id='anonymous_vent')
    async def anonymous_vent(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle anonymous vent button clicks"""
        guild_id = str(interaction.guild.id)
        
        # Check if server has vent channel configured
        if guild_id not in server_settings or 'vent_channel' not in server_settings[guild_id]:
            await interaction.response.send_message(
                "❌ Anonymous venting is not set up for this server. Please ask an admin to run the setup wizard.",
                ephemeral=True
            )
            return
            
        await interaction.response.send_modal(AnonymousVentModal())

class AnonymousVentModal(discord.ui.Modal, title='Anonymous Vent'):
    """Modal for anonymous message input"""
    
    def __init__(self, from_checkin=False):
        super().__init__()
        self.from_checkin = from_checkin

    message = discord.ui.TextInput(
        label='Your anonymous message',
        placeholder='Share what\'s on your mind... Your identity will remain completely anonymous.',
        style=discord.TextStyle.long,
        max_length=2000,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        
        # Check if server is configured
        if guild_id not in server_settings:
            await interaction.response.send_message(
                "❌ **Server not configured!**\n\n"
                "An administrator needs to run `!setup` first to configure the bot.",
                ephemeral=True
            )
            return
            
        settings = server_settings[guild_id]
        
        # Get the vent channel
        vent_channel = bot.get_channel(int(settings['vent_channel']))
        if not vent_channel:
            await interaction.response.send_message(
                "❌ Vent channel not found. Please contact an administrator.",
                ephemeral=True
            )
            return

        # Log the anonymous message with user info for moderation
        log_anonymous_message(
            guild_id, 
            self.message.value, 
            str(vent_channel.id),
            str(interaction.user.id),
            interaction.user.name,
            interaction.user.display_name
        )

        # Create anonymous embed
        embed = discord.Embed(
            description=self.message.value,
            color=0x2b2d31,
            timestamp=datetime.datetime.now()
        )
        embed.set_author(name="🫣 ANON", icon_url="https://cdn.discordapp.com/emojis/1234567890.png")
        embed.set_footer(text="Stay strong 💙 You're not alone")

        try:
            await vent_channel.send(embed=embed)
            
            # Create response with link to vent channel
            response_text = (
                f"✅ Your anonymous message has been posted in {vent_channel.mention}. "
                f"Thank you for sharing. 💙\n\n"
                f"You can check {vent_channel.mention} to see your message and await responses."
            )
            
            await interaction.response.send_message(response_text, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                "❌ Failed to post your message. Please try again later.",
                ephemeral=True
            )
            print(f"Error posting anonymous vent in guild {guild_id}: {e}")

class SimpleVentView(discord.ui.View):
    """Simple view for vent channels - just the anonymous button"""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🫣 Vent Anonymously', style=discord.ButtonStyle.primary, custom_id='simple_vent')
    async def simple_vent(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle simple vent button clicks"""
        await interaction.response.send_modal(AnonymousVentModal())

@bot.event
async def on_ready():
    """Bot ready event"""
    print(f'{bot.user} has connected to Discord!')
    
    # Add persistent views
    bot.add_view(AnonymousVentView())
    bot.add_view(SimpleVentView())
    bot.add_view(CheckinVentView())
    
    # Start daily check-in task
    if not daily_checkin.is_running():
        daily_checkin.start()

@tasks.loop(minutes=1)
async def daily_checkin():
    """Check if it's time to post daily check-ins for any server"""
    try:
        current_time = datetime.datetime.now(pytz.UTC)
        
        for guild_id, settings in server_settings.items():
            if 'time' not in settings or 'timezone' not in settings:
                continue
                
            try:
                # Parse the configured time
                time_parts = settings['time'].split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                
                # Get timezone
                try:
                    tz = pytz.timezone(settings['timezone'])
                except:
                    tz = pytz.UTC
                
                # Get current time in the server's timezone
                local_time = current_time.astimezone(tz)
                
                # Check if it's the right time (within the minute)
                if local_time.hour == hour and local_time.minute == minute:
                    
                    # Check if we already posted today
                    today_key = local_time.strftime('%Y-%m-%d')
                    if guild_id not in last_messages:
                        last_messages[guild_id] = {}
                    
                    if 'last_checkin_date' not in last_messages[guild_id] or last_messages[guild_id]['last_checkin_date'] != today_key:
                        await post_daily_checkin(guild_id)
                        last_messages[guild_id]['last_checkin_date'] = today_key
                        save_data()
                        
            except Exception as e:
                print(f"Error processing daily checkin for guild {guild_id}: {e}")
                continue
                
    except Exception as e:
        print(f"Error in daily_checkin task: {e}")

async def post_daily_checkin(guild_id: str):
    """Post daily check-in message"""
    try:
        settings = server_settings[guild_id]
        guild = bot.get_guild(int(guild_id))
        
        if not guild:
            print(f"Guild {guild_id} not found")
            return
        
        channel = guild.get_channel(int(settings['post_channel']))
        support_channel = guild.get_channel(int(settings['support_channel']))
        
        if not channel or not support_channel:
            print(f"Channels not found for guild {guild_id}")
            return

        # 🔹 Delete the previous check-in message if it exists
        if guild_id in last_messages and "daily_checkin" in last_messages[guild_id]:
            try:
                old_message = await channel.fetch_message(int(last_messages[guild_id]["daily_checkin"]))
                await old_message.delete()
            except Exception as e:
                print(f"Could not delete old check-in message in guild {guild_id}: {e}")
        
        # Format the message
        formatted_message = checkin_message.format(
            ping=settings['ping'],
            support_channel=support_channel.mention
        )
        
        # Create view with anonymous vent button
        view = CheckinVentView()
        
        # Send the message
        message = await channel.send(formatted_message, view=view)
        
        # Add reactions
        for emoji in emojis:
            try:
                await message.add_reaction(emoji)
            except:
                pass
        
        # Save message ID for tracking
        if guild_id not in last_messages:
            last_messages[guild_id] = {}
        last_messages[guild_id]['daily_checkin'] = str(message.id)
        save_data()
        
        print(f"Posted daily check-in for guild {guild_id}")
        
    except Exception as e:
        print(f"Error posting daily check-in for guild {guild_id}: {e}")


async def handle_sticky_message(message):
    """Handle sticky message logic for vent channels"""
    guild_id = str(message.guild.id)
    channel_id = str(message.channel.id)
    
    # Check if this guild has a sticky message configured
    if guild_id not in sticky_messages:
        return
    
    sticky_info = sticky_messages[guild_id]
    
    # Handle both old format (string) and new format (dict)
    if isinstance(sticky_info, str):
        # Old format - just message ID, need to get channel from settings
        if guild_id not in server_settings or 'vent_channel' not in server_settings[guild_id]:
            return
        expected_channel_id = str(server_settings[guild_id]['vent_channel'])
        message_id = sticky_info
    else:
        # New format - dict with message_id and channel_id
        expected_channel_id = sticky_info["channel_id"]
        message_id = sticky_info["message_id"]
    
    # Check if this message is in the vent channel
    if expected_channel_id != channel_id:
        return
    
    # Check if this message is the sticky message itself (don't restick if bot just posted it)
    if str(message.id) == message_id:
        return
    
    try:
        # Get the channel and find the sticky message
        channel = message.guild.get_channel(int(channel_id))
        if not channel:
            return
        
        # Try to get the current sticky message
        try:
            current_sticky = await channel.fetch_message(int(message_id))
        except discord.NotFound:
            # Sticky message was deleted, create a new one
            await create_new_sticky_message(channel, guild_id)
            return
        
        # Check if the sticky message is still the last message in the channel
        # Get recent messages to see if sticky is still at the bottom
        recent_messages = [msg async for msg in channel.history(limit=10)]
        
        if not recent_messages:
            return
        
        # If sticky message is not the most recent message, repost it
        last_message = recent_messages[0]
        if str(last_message.id) != message_id:
            # Delete the old sticky and create a new one
            try:
                await current_sticky.delete()
            except discord.NotFound:
                pass  # Already deleted
            
            # Create new sticky message
            await create_new_sticky_message(channel, guild_id)
    
    except Exception as e:
        print(f"Error handling sticky message: {e}")

async def create_new_sticky_message(channel, guild_id):
    """Create a new sticky message in the vent channel"""
    view = SimpleVentView()
    message = await channel.send(view=view)
    
    # Update sticky message info
    sticky_messages[str(guild_id)] = {
        "message_id": str(message.id),
        "channel_id": str(channel.id)
    }
    save_data()

@bot.event
async def on_message(message):
    """Handle incoming messages for setup wizard and sticky messages"""
    if message.author.bot:
        return
    
    # Ignore DM messages
    if message.guild is None:
        return
    
    # Handle sticky message logic for vent channels
    await handle_sticky_message(message)
    
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)
    
    # Check if user is in setup session
    if guild_id in setup_sessions and user_id in setup_sessions[guild_id]:
        session = setup_sessions[guild_id][user_id]
        
        # Delete the user's message
        try:
            await message.delete()
        except:
            pass
        
        await handle_setup_response(message, session)
        return
    
    # Process commands
    await bot.process_commands(message)

async def parse_channel(guild, content):
    """Parse channel mention or name"""
    content = content.strip()
    
    # Channel mention format
    if content.startswith('<#') and content.endswith('>'):
        try:
            channel_id = int(content[2:-1])
            channel = guild.get_channel(channel_id)
            if isinstance(channel, discord.TextChannel):
                return channel
        except ValueError:
            pass
    
    # Channel name with # or without
    channel_name = content.lstrip('#')
    channel = discord.utils.get(guild.text_channels, name=channel_name)
    return channel

async def setup_vent_channel(vent_channel, guild_id):
    """Setup sticky vent message in vent channel"""
    view = SimpleVentView()
    message = await vent_channel.send(view=view)
    
    # Store sticky message info for tracking
    sticky_messages[str(guild_id)] = {
        "message_id": str(message.id),
        "channel_id": str(vent_channel.id)
    }
    save_data()

async def handle_setup_response(message, session):
    """Handle setup wizard responses"""
    guild = message.guild
    channel = message.channel
    user = message.author
    content = message.content.strip()
    step = session['step']
    
    try:
        if step == 2:  # Post channel selection
            target_channel = await parse_channel(guild, content)
            if not target_channel:
                embed = discord.Embed(
                    title="❌ Invalid Channel",
                    description="Please mention a valid text channel or type the channel name (e.g., #general or general)",
                    color=0xff0000
                )
                await channel.send(embed=embed, delete_after=5)
                return
            
            session['data']['post_channel'] = target_channel.id
            session['step'] = 3
            
            # Move to support channel selection
            embed = discord.Embed(
                title="Setup Wizard - Step 3/6 📞",
                description="**Noice! Now pick your support channel** 💬\n\nThis is where people can go when they need some extra love and support. You know, for when the going gets tough and they need a hug (but in text form).\n\n*Pro tip: Don't use your meme channel for this one 😅*\n\n**Please mention the support channel or type its name:**",
                color=0x7289da
            )
            embed.set_footer(text="Example: #support or support")
            await session['message'].edit(embed=embed)
            
        elif step == 3:  # Support channel selection
            target_channel = await parse_channel(guild, content)
            if not target_channel:
                embed = discord.Embed(
                    title="❌ Invalid Channel",
                    description="Please mention a valid text channel or type the channel name (e.g., #support or support)",
                    color=0xff0000
                )
                await channel.send(embed=embed, delete_after=5)
                return
            
            session['data']['support_channel'] = target_channel.id
            session['step'] = 4
            
            embed = discord.Embed(
                title="Setup Wizard - Step 4/6 🫣",
                description="**Sweet! Now let's set up the secret diary channel** 📝\n\nThis is where people can anonymously spill their thoughts without anyone knowing who's doing the spilling. It's like a confession booth, but cooler and with more emojis.\n\n*Warning: May contain feelings*\n\n**Please mention the vent channel or type its name:**",
                color=0x7289da
            )
            embed.set_footer(text="Example: #vent or anonymous-vent")
            await session['message'].edit(embed=embed)
            
        elif step == 4:  # Vent channel selection
            target_channel = await parse_channel(guild, content)
            if not target_channel:
                embed = discord.Embed(
                    title="❌ Invalid Channel",
                    description="Please mention a valid text channel or type the channel name (e.g., #vent or anonymous-vent)",
                    color=0xff0000
                )
                await channel.send(embed=embed, delete_after=5)
                return
            
            session['data']['vent_channel'] = target_channel.id
            session['step'] = 5
            
            embed = discord.Embed(
                title="Setup Wizard - Step 5/6 📣",
                description="**Awesome sauce! Who should I annoy... I mean, *notify* for check-ins?** 🔔\n\nPick your poison wisely - some people love a good @everyone, others prefer the gentle nudge of @here. Choose your chaos level!\n\n**Type one of the following:**\n• `@everyone` - Ping everyone (maximum chaos)\n• `@here` - Ping only online members (medium chaos)\n• `none` - No pings (peaceful mode)",
                color=0x7289da
            )
            embed.set_footer(text="Choose wisely...")
            await session['message'].edit(embed=embed)
            
        elif step == 5:  # Ping selection
            ping_options = {
                '@everyone': '@everyone',
                'everyone': '@everyone',
                '@here': '@here',
                'here': '@here',
                'none': 'none',
                'no': 'none'
            }
            
            ping_choice = ping_options.get(content.lower())
            if not ping_choice:
                embed = discord.Embed(
                    title="❌ Invalid Option",
                    description="Please type one of: `@everyone`, `@here`, or `none`",
                    color=0xff0000
                )
                await channel.send(embed=embed, delete_after=5)
                return
            
            session['data']['ping'] = ping_choice
            session['step'] = 6
            
            embed = discord.Embed(
                title="Setup Wizard - Step 6/7 🌍",
                description="**Awesome sauce! What's your timezone?** ⏰\n\nPick your timezone so I know when to post your daily check-ins! No more confusion about whether it's 9 AM your time or mine (spoiler: mine doesn't exist because I'm a bot 🤖).\n\n**Please select your timezone from the dropdown below:**",
                color=0x7289da
            )
            embed.set_footer(text="Choose the timezone closest to your server's location")
            
            view = TimezoneView()
            await session['message'].edit(embed=embed, view=view)
            
        elif step == 7:  # Time selection
            try:
                time_parts = content.split(':')
                if len(time_parts) != 2:
                    raise ValueError
                hour, minute = int(time_parts[0]), int(time_parts[1])
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError
                time_str = f"{hour:02d}:{minute:02d}"
            except ValueError:
                embed = discord.Embed(
                    title="❌ Invalid Time",
                    description="Please enter a valid time in HH:MM format (e.g., 09:00, 14:30, 20:15)",
                    color=0xff0000
                )
                await channel.send(embed=embed, delete_after=5)
                return
            
            session['data']['time'] = time_str
            # Timezone already set in step 6
            
            server_settings[str(guild.id)] = session['data']
            save_data()
            
            post_ch = guild.get_channel(int(session['data']['post_channel']))
            support_ch = guild.get_channel(int(session['data']['support_channel']))
            vent_ch = guild.get_channel(int(session['data']['vent_channel']))
            
            embed = discord.Embed(
                title="🎉 Setup Complete! Welcome to Wholesome-ville!",
                description="**Congrats! Your server is now 1000% more supportive!** 💖\n\nI'm all configured and ready to help your community check in on each other and share their feelings safely.",
                color=0x00ff7f
            )
            # Get timezone display name for completion message
            timezone_display = session['data']['timezone']
            try:
                tz = pytz.timezone(session['data']['timezone'])
                # Try to get a more user-friendly name
                timezone_options = {
                    "UTC": "UTC (Universal Time)",
                    "US/Eastern": "Eastern Time (US)",
                    "US/Central": "Central Time (US)", 
                    "US/Mountain": "Mountain Time (US)",
                    "US/Pacific": "Pacific Time (US)",
                    "US/Alaska": "Alaska Time",
                    "US/Hawaii": "Hawaii Time",
                    "Europe/London": "London (GMT/BST)",
                    "Europe/Paris": "Paris/Berlin/Rome",
                    "Europe/Moscow": "Moscow",
                    "Asia/Dubai": "Dubai",
                    "Asia/Kolkata": "Mumbai/Delhi", 
                    "Asia/Bangkok": "Bangkok",
                    "Asia/Shanghai": "Shanghai/Beijing",
                    "Asia/Tokyo": "Tokyo",
                    "Australia/Sydney": "Sydney",
                    "Pacific/Auckland": "Auckland"
                }
                timezone_display = timezone_options.get(session['data']['timezone'], session['data']['timezone'])
            except:
                pass
                
            embed.add_field(
                name="📅 Daily Check-ins",
                value=f"Every day at **{time_str}** ({timezone_display}) in {post_ch.mention}\nPeople can react with emojis to show how they're feeling!",
                inline=False
            )
            embed.add_field(
                name="💬 Support Hub",
                value=f"{support_ch.mention}\nFor deeper conversations and peer support",
                inline=False
            )
            embed.add_field(
                name="🫣 Anonymous Venting",
                value=f"{vent_ch.mention}\nSafe space for anonymous feelings (with mod oversight)",
                inline=False
            )
            embed.add_field(
                name="🔔 Daily Ping Style",
                value=f"**{session['data']['ping']}** - {'Everyone gets notified!' if session['data']['ping'] == '@everyone' else 'Only online members get notified!' if session['data']['ping'] == '@here' else 'Silent mode - no pings!'}",
                inline=False
            )
            embed.set_footer(text="Thanks for setting up mental health support for your community! 💙")
            
            await session['message'].edit(embed=embed)
            
            await setup_vent_channel(vent_ch, str(guild.id))
            
            guild_id_str = str(guild.id)
            user_id_str = str(user.id)
            del setup_sessions[guild_id_str][user_id_str]
            if not setup_sessions[guild_id_str]:
                del setup_sessions[guild_id_str]
            
    except Exception as e:
        print(f"Error in setup wizard step {step}: {e}")
        embed = discord.Embed(
            title="❌ Setup Error", 
            description=f"Something went wrong at step {step}. Please try the `!setup` command again.",
            color=0xff0000
        )
        await channel.send(embed=embed, delete_after=10)
        
        guild_id = str(guild.id)
        user_id = str(user.id)
        if guild_id in setup_sessions and user_id in setup_sessions[guild_id]:
            del setup_sessions[guild_id][user_id]
            if not setup_sessions[guild_id]:
                del setup_sessions[guild_id]

@bot.command(name='help')
async def help_command(ctx):
    """Show setup guidance and bot overview for admins"""
    embed = discord.Embed(
        title="🚀 Getting Started - Mental Health Support Bot",
        description="Hi! I'm here to help you set up a safe mental health support system for your Discord server.",
        color=0x7289da
    )
    
    embed.add_field(
        name="📝 How to Get Started",
        value=(
            "**Step 1:** Use `!setup` command to begin configuration\n"
            "**Step 2:** I'll ask you to choose 3 channels:\n"
            "   • Daily check-in channel (where I post mood tracking)\n"
            "   • Support channel (for discussions)\n"
            "   • Vent channel (for anonymous messages)\n"
            "**Step 3:** Pick ping settings, timezone, and daily check-in time\n"
            "**Step 4:** Done! I'll automatically start posting daily check-ins"
        ),
        inline=False
    )
    
    embed.add_field(
        name="💖 What This Bot Does",
        value=(
            "• Posts daily mental health check-ins with mood emojis\n"
            "• Provides anonymous venting system for users to share struggles\n"
            "• Creates supportive community spaces\n"
            "• Keeps anonymous messages secure with admin oversight"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚡ Quick Setup",
        value="Just type `!setup` and follow the prompts - it takes about 2 minutes!",
        inline=False
    )
    
    embed.set_footer(text="Created by N O O D L E    (xnoodlexx) • Need commands? Use !commands")
    
    await ctx.send(embed=embed)

@bot.command(name='commands')
async def commands_list(ctx):
    """Show all available commands and what each one does"""
    embed = discord.Embed(
        title="📋 Bot Commands List",
        description="All available commands and their functions:",
        color=0x00ff7f
    )
    
    embed.add_field(
        name="⚙️ Setup Commands",
        value=(
            "`!setup` - Configure the bot for your server (channels, times, etc.)\n"
            "`!settings` - View your current server settings\n"
            "`!force` - Test daily check-in immediately"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📊 Admin Commands",
        value=(
            "`!generate_code` - Create access code to view anonymous logs\n"
            "`!view_logs <code>` - View anonymous message logs with access code\n"
            "`!stats` - See usage statistics for your server"
        ),
        inline=False
    )
    
    embed.add_field(
        name="ℹ️ Help Commands",
        value=(
            "`!help` - Get setup instructions for new admins\n"
            "`!commands` - Show this list of commands\n"
            "`!ping` - Test if bot is responding"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🫣 For Users",
        value=(
            "Users can click **🫣 Vent Anonymously** buttons to send anonymous messages.\n"
            "These buttons appear in daily check-ins and vent channels."
        ),
        inline=False
    )
    
    embed.set_footer(text="Admin commands require 'Manage Server' permission • Created by N O O D L E    (xnoodlexx)")
    
    await ctx.send(embed=embed)

@bot.command(name='setup')
async def setup_command(ctx):
    """Start the setup wizard"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You need administrator permissions to run the setup wizard.")
        return
    
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    
    # Initialize setup session
    if guild_id not in setup_sessions:
        setup_sessions[guild_id] = {}
    
    # Check if user already has a session
    if user_id in setup_sessions[guild_id]:
        await ctx.send("❌ You already have a setup session running. Please complete it first.")
        return
    
    # Start setup wizard
    embed = discord.Embed(
        title="🧙‍♂️ Mental Health Bot Setup Wizard",
        description="**Welcome to the most wholesome setup you'll ever do!** 💖\n\nI'm here to help you create a supportive space for your community. We'll set up daily check-ins, anonymous venting, and support channels.\n\n*This will take about 2 minutes and will make your server 1000% more awesome.*\n\n**Ready? Please mention the channel where I should post daily check-ins:**",
        color=0x7289da
    )
    embed.set_footer(text="Example: #general or general")
    
    setup_message = await ctx.send(embed=embed)
    
    # Store session data - start directly at step 2
    setup_sessions[guild_id][user_id] = {
        'step': 2,
        'message': setup_message,
        'data': {}
    }

@bot.command(name='force')
@commands.has_permissions(manage_guild=True)
async def force_checkin(ctx):
    """Force a daily check-in post immediately"""
    guild_id = str(ctx.guild.id)
    
    if guild_id not in server_settings:
        await ctx.send("❌ **Server not configured!**\n\nPlease run `!setup` first to configure the bot.")
        return
    
    try:
        await post_daily_checkin(guild_id)
        await ctx.send("✅ **Daily check-in posted successfully!**")
    except Exception as e:
        await ctx.send(f"❌ **Error posting daily check-in:** {str(e)}")
        print(f"Force checkin error for guild {guild_id}: {e}")

@bot.command(name='settings')
@commands.has_permissions(manage_guild=True)
async def view_settings(ctx):
    """View current server settings"""
    guild_id = str(ctx.guild.id)
    
    if guild_id not in server_settings:
        await ctx.send("❌ **Server not configured!**\n\nPlease run `!setup` first to configure the bot.")
        return
    
    settings = server_settings[guild_id]
    
    embed = discord.Embed(
        title="⚙️ Current Server Settings",
        color=0x7289da
    )
    
    # Get channel objects for mentions
    post_channel = ctx.guild.get_channel(int(settings['post_channel']))
    support_channel = ctx.guild.get_channel(int(settings['support_channel']))
    vent_channel = ctx.guild.get_channel(int(settings['vent_channel']))
    
    embed.add_field(
        name="📅 Daily Check-in Channel",
        value=post_channel.mention if post_channel else "❌ Channel not found",
        inline=True
    )
    
    embed.add_field(
        name="💬 Support Channel",
        value=support_channel.mention if support_channel else "❌ Channel not found",
        inline=True
    )
    
    embed.add_field(
        name="🫣 Vent Channel",
        value=vent_channel.mention if vent_channel else "❌ Channel not found",
        inline=True
    )
    
    embed.add_field(
        name="🔔 Ping Setting",
        value=settings['ping'],
        inline=True
    )
    
    embed.add_field(
        name="⏰ Check-in Time",
        value=f"{settings['time']} {settings['timezone']}",
        inline=True
    )
    
    embed.add_field(
        name="🔄 Reconfigure",
        value="Use `!setup` to change these settings",
        inline=True
    )
    
    await ctx.send(embed=embed)

@bot.command(name='generate_code')
@commands.has_permissions(manage_guild=True)
async def generate_code_command(ctx):
    """Generate an access code for viewing logs"""
    guild_id = str(ctx.guild.id)
    code = generate_access_code(guild_id)
    
    await ctx.author.send(
        f"🔐 **Access Code Generated**\n\n"
        f"Your one-time access code: `{code}`\n\n"
        f"Use `!view_logs {code}` to view anonymous message logs.\n"
        f"⚠️ This code can only be used once and will expire after use."
    )
    
    await ctx.send("✅ Access code sent to your DMs!")

@bot.command(name='view_logs')
@commands.has_permissions(manage_guild=True)
async def view_logs_command(ctx, code: str = None):
    """View anonymous message logs with access code"""
    if not code:
        await ctx.send("❌ Please provide an access code: `!view_logs <code>`")
        return
    
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    
    if not use_access_code(guild_id, code, user_id):
        await ctx.send("❌ Invalid or already used access code.")
        return
    
    if guild_id not in anon_logs or not anon_logs[guild_id]:
        await ctx.send("📝 No anonymous messages logged for this server.")
        return
    
    logs = anon_logs[guild_id]
    
    # Create embed with recent logs
    embed = discord.Embed(
        title="📋 Anonymous Message Logs",
        description=f"Showing {len(logs)} anonymous messages",
        color=0xff9900
    )
    
    for i, log in enumerate(logs[-10:]):  # Show last 10 logs
        try:
            decoded_content = base64.b64decode(log['encoded_content']).decode()
            decoded_username = base64.b64decode(log['encoded_username']).decode()
            
            embed.add_field(
                name=f"Message {i+1} - {log['timestamp'][:16]}",
                value=f"**User:** {decoded_username} (ID: {log['user_id']})\n**Content:** {decoded_content[:100]}{'...' if len(decoded_content) > 100 else ''}",
                inline=False
            )
        except Exception as e:
            embed.add_field(
                name=f"Message {i+1} - {log['timestamp'][:16]}",
                value="❌ Error decoding message",
                inline=False
            )
    
    if len(logs) > 10:
        embed.set_footer(text=f"Showing last 10 of {len(logs)} total messages")
    
    await ctx.author.send(embed=embed)
    await ctx.send("📨 Log details sent to your DMs!")

@bot.command(name='stats')
@commands.has_permissions(manage_guild=True)
async def stats_command(ctx):
    """Show bot usage statistics"""
    guild_id = str(ctx.guild.id)
    
    embed = discord.Embed(
        title="📊 Bot Statistics",
        color=0x00ff7f
    )
    
    # Anonymous messages count
    anon_count = len(anon_logs.get(guild_id, []))
    embed.add_field(
        name="🫣 Anonymous Messages",
        value=str(anon_count),
        inline=True
    )
    
    # Access codes generated
    access_count = len(access_codes.get(guild_id, {}))
    embed.add_field(
        name="🔐 Access Codes Generated",
        value=str(access_count),
        inline=True
    )
    
    # Moderator accesses
    mod_access_count = len(moderator_access.get(guild_id, []))
    embed.add_field(
        name="👮 Log Accesses",
        value=str(mod_access_count),
        inline=True
    )
    
    # Configuration status
    configured = "✅ Yes" if guild_id in server_settings else "❌ No"
    embed.add_field(
        name="⚙️ Bot Configured",
        value=configured,
        inline=True
    )
    
    # Last check-in
    last_checkin = last_messages.get(guild_id, {}).get('last_checkin_date', 'Never')
    embed.add_field(
        name="📅 Last Check-in",
        value=last_checkin,
        inline=True
    )
    
    await ctx.send(embed=embed)

@bot.command(name='ping')
async def ping_command(ctx):
    """Check bot responsiveness"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: {latency}ms")

# Error handlers
@setup_command.error
@force_checkin.error
@view_settings.error
@generate_code_command.error
@view_logs_command.error
@stats_command.error
async def permission_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need **Manage Server** permissions to use this command.")

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    else:
        print(f"Command error: {error}")
        await ctx.send("❌ An error occurred while processing your command.")

# Run the bot
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN environment variable not found!")
        exit(1)
    bot.run(token)