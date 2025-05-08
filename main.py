import os
import time
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import discord
from discord.ext import commands

# Load environment variables
load_dotenv()

# Flask keep-alive setup
def keep_alive():
    app = Flask(__name__)

    @app.route('/')
    def home():
        return "I'm alive!"

    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# === CONFIGURATION ===
ID_KANAŁU_SEARCH = 1367975025990307881     # #🔎search-club🔎
ID_KANAŁU_FREE_AGENTS = 1258017564185989226  # #🌝free-agents🌝
ID_KANAŁU_AUTOROLE = 1367984711988940922
ID_KANAŁU_REGISTRATION = 1367982248841842790
REQUIRED_ROLE_NAME = "⟪🎮⟫ PLAYER"

ROLE_MAP = {
    "🧤": "⟪🧤⟫ SEARCH GK",
    "🧱": "⟪🧱⟫ SEARCH CB",
    "👟": "⟪👟⟫ SEARCH CM",
    "⚽": "⟪⚽⟫ SEARCH ST"
}

user_message_map = {}
emoji_cooldowns = {}  # (user_id, emoji): timestamp
COOLDOWN_SECONDS = 2 * 60 * 60  # 2 hours

@bot.command()
async def setup_message(ctx):
    if ctx.channel.id != ID_KANAŁU_SEARCH:
        return

    msg_text = (
        "Good to hear you're looking for a club. Several teams are still looking for players.\n"
        "**What position you prefer to play? (you can choose multiple positions)**\n"
        "---------------------------------------------------------------------------------------------------------\n"
        "⌊🧤⌉ - If you're a GK\n"
        "---------------------------------------------------------------------------------------------------------\n"
        "⌊🧱⌉ - If you're a CB\n"
        "---------------------------------------------------------------------------------------------------------\n"
        "⌊👟⌉ - If you're a CM\n"
        "---------------------------------------------------------------------------------------------------------\n"
        "⌊⚽⌉ - If you're a ST\n"
        "---------------------------------------------------------------------------------------------------------\n"
        f"**Please delete your reactions after you find a club as this will remove your application from the <#{ID_KANAŁU_FREE_AGENTS}>**\n"
        f"**IMPORTANT: First you must have a {REQUIRED_ROLE_NAME} role to find a club. You can get it in <#{ID_KANAŁU_AUTOROLE}>**"
    )

    message = await ctx.send(msg_text)

    for emoji in ROLE_MAP.keys():
        await message.add_reaction(emoji)

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    if payload.channel_id != ID_KANAŁU_SEARCH:
        return

    emoji = payload.emoji.name
    if emoji not in ROLE_MAP:
        return

    guild = bot.get_guild(payload.guild_id)
    user = guild.get_member(payload.user_id)
    if user is None:
        return

    required_role = discord.utils.get(guild.roles, name=REQUIRED_ROLE_NAME)
    if required_role not in user.roles:
        return

    now = time.time()
    cooldown_key = (payload.user_id, emoji)
    last_used = emoji_cooldowns.get(cooldown_key, 0)

    if now - last_used < COOLDOWN_SECONDS:
        remaining = int((COOLDOWN_SECONDS - (now - last_used)) // 60)
        try:
            await user.send(f"""
⏳ You can only apply for **{emoji}** once every 2 hours. Please wait {remaining} more minutes.
--------------------------------------------------------------------------------------------------------
""")
        except discord.Forbidden:
            pass
        return

    role_name = ROLE_MAP[emoji]
    role = discord.utils.get(guild.roles, name=role_name)
    free_agents_channel = guild.get_channel(ID_KANAŁU_FREE_AGENTS)

    if role:
        msg = await free_agents_channel.send(
            f"{user.mention} looking for a club {role.mention}\n"
            "--------------------------------------------------------------------------------------------------------"
        )
        user_message_map[(payload.user_id, emoji)] = msg.id
        emoji_cooldowns[cooldown_key] = now

        player_count = sum(1 for member in guild.members if role in member.roles)

        try:
            await user.send(
                f"Good! {player_count} teams are looking for players like you.\n\n"
                "Wait a few hours/days and we will find the perfect club for you.\n\n"
                f"If the number of clubs that need you is 0, there are probably no more free spots in the teams.\n"
                f"You can create your team in the <#{ID_KANAŁU_REGISTRATION}> and we will help you find players.\n"
                "--------------------------------------------------------------------------------------------------------"
            )
        except discord.Forbidden:
            pass
    else:
        await free_agents_channel.send(f"{user.mention} looking for a club (role `{role_name}` not found!)")

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.channel_id != ID_KANAŁU_SEARCH:
        return

    emoji = payload.emoji.name
    key = (payload.user_id, emoji)
    if key not in user_message_map:
        return

    message_id = user_message_map[key]
    guild = bot.get_guild(payload.guild_id)
    free_agents_channel = guild.get_channel(ID_KANAŁU_FREE_AGENTS)

    try:
        msg = await free_agents_channel.fetch_message(message_id)
        await msg.delete()
        del user_message_map[key]
    except discord.NotFound:
        pass

# Start keep-alive server and bot
if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("TOKEN"))
