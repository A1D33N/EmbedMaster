import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
import signal
import sys
from datetime import datetime

# ========== CONFIG ==========
BOT_NICKNAME = "EmbedMaster ✨"
LOG_CHANNELS_FILE = "log_channels.json"
PERMISSION_ROLE = None  # Role name required to run commands, or None to use Manage Messages perm
BOT_VERSION = "v1.2.0"
BOT_OWNER_ID = None  # Put your Discord user ID here (int) to get a DM on startup, or None to disable
# ============================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
start_time = datetime.utcnow()

def load_log_channels():
    if not os.path.isfile(LOG_CHANNELS_FILE):
        return {}
    with open(LOG_CHANNELS_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_log_channels(data):
    with open(LOG_CHANNELS_FILE, "w") as f:
        json.dump(data, f, indent=4)

log_channels = load_log_channels()

def has_manage_messages_or_admin(interaction: discord.Interaction):
    if PERMISSION_ROLE:
        role = discord.utils.find(lambda r: r.name == PERMISSION_ROLE, interaction.user.roles)
        return role is not None
    perms = interaction.user.guild_permissions
    return perms.manage_messages or perms.administrator

async def send_log(guild: discord.Guild, embed: discord.Embed):
    channel_id = log_channels.get(str(guild.id))
    if channel_id:
        channel = guild.get_channel(channel_id)
        if channel:
            try:
                await channel.send(embed=embed)
            except:
                pass

def format_timestamp(dt: datetime):
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

def uptime():
    delta = datetime.utcnow() - start_time
    days, seconds = delta.days, delta.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)

@bot.event
async def on_ready():
    print(f"{bot.user} is online and ready! Serving {len(bot.guilds)} guild(s).")

    for guild in bot.guilds:
        me = guild.me
        try:
            await me.edit(nick=BOT_NICKNAME)
            print(f"✅ Nickname set in '{guild.name}'")
        except Exception as e:
            print(f"❌ Couldn’t set nickname in '{guild.name}': {e}")

    try:
        synced = await bot.tree.sync()
        print(f"🔃 Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"⚠️ Sync error: {e}")

    embed = discord.Embed(
        title="🤖 Bot Started",
        description=f"{bot.user} is now online and ready to embed!",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Uptime started at {format_timestamp(start_time)}")
    for guild in bot.guilds:
        await send_log(guild, embed)

    if BOT_OWNER_ID:
        try:
            owner = await bot.fetch_user(BOT_OWNER_ID)
            await owner.send(f"✅ **{bot.user}** started successfully! Serving {len(bot.guilds)} servers.")
        except:
            pass

@bot.event
async def on_guild_join(guild: discord.Guild):
    me = guild.me
    try:
        await me.edit(nick=BOT_NICKNAME)
    except:
        pass

def handle_exit(*args):
    asyncio.create_task(shutdown())

async def shutdown():
    embed = discord.Embed(
        title="🤖 Bot Shutting Down",
        description=f"{bot.user} is going offline.",
        color=discord.Color.red(),
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Shutdown at {format_timestamp(datetime.utcnow())}")
    for guild in bot.guilds:
        await send_log(guild, embed)
    await bot.close()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

# ========== Commands ==========

@bot.tree.command(name="sendembed", description="Send a custom embed to a channel")
@app_commands.describe(
    channel="Target channel",
    title="Embed title",
    message="Embed content/message",
    hex_color="Hex color code like #FF0000 (optional)"
)
async def sendembed(interaction: discord.Interaction, channel: discord.TextChannel, title: str, message: str, hex_color: str = "#2F3136"):
    if not has_manage_messages_or_admin(interaction):
        return await interaction.response.send_message("❌ You lack permission to use this command.", ephemeral=True)
    try:
        color = discord.Color(int(hex_color.strip("#"), 16))
    except:
        color = discord.Color.default()
    embed = discord.Embed(title=title, description=message, color=color)
    embed.set_footer(text=f"Sent by {interaction.user}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    try:
        await channel.send(embed=embed)
        await interaction.response.send_message(f"✅ Embed sent to {channel.mention}", ephemeral=True)
    except Exception as e:
        return await interaction.response.send_message(f"❌ Failed to send embed: {e}", ephemeral=True)
    log_embed = discord.Embed(title="📤 Embed Sent", color=discord.Color.blue(), timestamp=datetime.utcnow())
    log_embed.add_field(name="User", value=f"{interaction.user} (`{interaction.user.id}`)", inline=False)
    log_embed.add_field(name="Channel", value=f"{channel.mention} (`{channel.id}`)", inline=False)
    snippet = message if len(message) < 200 else message[:197] + "..."
    log_embed.add_field(name="Message Snippet", value=snippet, inline=False)
    await send_log(interaction.guild, log_embed)

@bot.tree.command(name="embedpreview", description="Preview an embed privately")
@app_commands.describe(
    title="Embed title",
    message="Embed content/message",
    hex_color="Hex color code like #FF0000 (optional)"
)
async def embedpreview(interaction: discord.Interaction, title: str, message: str, hex_color: str = "#2F3136"):
    if not has_manage_messages_or_admin(interaction):
        return await interaction.response.send_message("❌ You lack permission to use this command.", ephemeral=True)
    try:
        color = discord.Color(int(hex_color.strip("#"), 16))
    except:
        color = discord.Color.default()
    embed = discord.Embed(title=title, description=message, color=color)
    embed.set_footer(text=f"Previewed by {interaction.user}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="sendraw", description="Send a plain message to a channel")
@app_commands.describe(
    channel="Target channel",
    message="Message content"
)
async def sendraw(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    if not has_manage_messages_or_admin(interaction):
        return await interaction.response.send_message("❌ You lack permission to use this command.", ephemeral=True)
    try:
        await channel.send(message)
        await interaction.response.send_message(f"✅ Message sent to {channel.mention}", ephemeral=True)
    except Exception as e:
        return await interaction.response.send_message(f"❌ Failed to send message: {e}", ephemeral=True)
    log_embed = discord.Embed(title="📤 Raw Message Sent", color=discord.Color.orange(), timestamp=datetime.utcnow())
    log_embed.add_field(name="User", value=f"{interaction.user} (`{interaction.user.id}`)", inline=False)
    log_embed.add_field(name="Channel", value=f"{channel.mention} (`{channel.id}`)", inline=False)
    snippet = message if len(message) < 200 else message[:197] + "..."
    log_embed.add_field(name="Message Snippet", value=snippet, inline=False)
    await send_log(interaction.guild, log_embed)

@bot.tree.command(name="setnickname", description="Change bot nickname in this server")
@app_commands.describe(nickname="New nickname for the bot")
async def setnickname(interaction: discord.Interaction, nickname: str):
    if not has_manage_messages_or_admin(interaction):
        return await interaction.response.send_message("❌ You lack permission to use this command.", ephemeral=True)
    me = interaction.guild.me
    try:
        await me.edit(nick=nickname)
        await interaction.response.send_message(f"✅ Nickname changed to: {nickname}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to change nickname: {e}", ephemeral=True)

@bot.tree.command(name="setlogchannel", description="Set channel for bot logs")
@app_commands.describe(channel="Channel to receive logs")
async def setlogchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not has_manage_messages_or_admin(interaction):
        return await interaction.response.send_message("❌ You lack permission to use this command.", ephemeral=True)
    log_channels[str(interaction.guild.id)] = channel.id
    save_log_channels(log_channels)
    await interaction.response.send_message(f"✅ Log channel set to {channel.mention}", ephemeral=True)

@bot.tree.command(name="viewlogchannel", description="Show current log channel")
async def viewlogchannel(interaction: discord.Interaction):
    channel_id = log_channels.get(str(interaction.guild.id))
    if channel_id:
        channel = interaction.guild.get_channel(channel_id)
        if channel:
            return await interaction.response.send_message(f"📢 Current log channel: {channel.mention}", ephemeral=True)
    await interaction.response.send_message("❌ No log channel set.", ephemeral=True)

@bot.tree.command(name="clearlogchannel", description="Clear the log channel setting")
async def clearlogchannel(interaction: discord.Interaction):
    if not has_manage_messages_or_admin(interaction):
        return await interaction.response.send_message("❌ You lack permission to use this command.", ephemeral=True)
    if str(interaction.guild.id) in log_channels:
        log_channels.pop(str(interaction.guild.id))
        save_log_channels(log_channels)
        await interaction.response.send_message("✅ Log channel setting cleared.", ephemeral=True)
    else:
        await interaction.response.send_message("ℹ️ No log channel was set.", ephemeral=True)

@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    latency_ms = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: {latency_ms}ms", ephemeral=True)

@bot.tree.command(name="botinfo", description="Show bot info and uptime")
async def botinfo(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 Bot Information", color=discord.Color.blurple())
    embed.add_field(name="Bot Name", value=bot.user.name, inline=True)
    embed.add_field(name="Version", value=BOT_VERSION, inline=True)
    embed.add_field(name="Uptime", value=uptime(), inline=True)
    embed.add_field(name="Servers", value=str(len(bot.guilds)), inline=True)
    embed.set_footer(text="EmbedMaster at your service!")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="help", description="Detailed usage guide")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📚 EmbedMaster Help Guide",
        description=(
            "Welcome to **EmbedMaster** — the bot that makes sending clean and colorful embeds a breeze!\n\n"
            "**Commands:**\n"
            "• `/sendembed` - Send a custom embed to any channel.\n"
            "• `/embedpreview` - Preview your embed privately before sending.\n"
            "• `/sendraw` - Send a plain text message.\n"
            "• `/setnickname` - Change the bot’s nickname in your server.\n"
            "• `/setlogchannel` - Choose a channel to receive logs of bot actions.\n"
            "• `/viewlogchannel` - See the currently set log channel.\n"
            "• `/clearlogchannel` - Remove the log channel setting.\n"
            "• `/ping` - Check bot latency.\n"
            "• `/botinfo` - View uptime, version, and server count.\n\n"
            "**Usage Tips:**\n"
            "• Use hex colors like `#FF0000` for vibrant embeds.\n"
            "• You must have **Manage Messages** permission to use most commands.\n"
            "• Logs include info on embed/raw messages sent and bot startup/shutdown.\n\n"
            "**Need help?** Contact your server admin or the bot owner."
        ),
        color=discord.Color.blurple()
    )
    embed.set_footer(text="EmbedMaster | Clean embeds, easy messaging")
    await interaction.response.send_message(embed=embed, ephemeral=True)

bot.run("YOUR_BOT_TOKEN_HERE")