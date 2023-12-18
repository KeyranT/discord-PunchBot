
#version 0.5.03

import discord
from discord.ext import commands
import datetime
import json
import os

from __setting__ import TOKKENSERVER, TOKKENTEST, MESSAGEINFO



intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
punch_ins = {}

# Load user data from JSON file
user_data_file = "user_data.json"
if os.path.exists(user_data_file):
    with open(user_data_file, "r") as f:
        user_data = json.load(f)
else:
    user_data = {}


def datetime_converter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()


@bot.command(name='info')
async def infos(ctx):
    info_embed = discord.Embed(
        title='Punch Bot',
        description=MESSAGEINFO
        )
    
    message = await ctx.send(embed=info_embed)
    await message.add_reaction('🥊')  # Punch In reaction


@bot.command(name='stats')
async def punch_stats(ctx):
    user_id = str(ctx.author.id)
    user_name = str(ctx.author.name)
    if user_id in user_data:
        punch_in_time = user_data[user_id]["punch_in_time"]
        current_time = datetime.datetime.now()
        time_difference = current_time - punch_in_time

        hours, remainder = divmod(time_difference.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        # Convert le cumulatif en heures et minutes
        cumulative_hours, cumulative_remainder = divmod(user_data[user_id]["cumulative"], 3600)
        cumulative_minutes, _ = divmod(cumulative_remainder, 60)

        # Create a list of punch entries
        punch_entries = []
        for punch_num, punch_data in user_data[user_id]["punch"].items():
            if len(punch_data) >= 2:
                punch_entries.append(f'Punch {punch_num}: {punch_data[0]} - {punch_data[1]}')
            else:
                punch_entries.append(f'Punch {punch_num}: {punch_data[0]}')

        # Join punch entries into a string
        punch_entries_str = '\n'.join(punch_entries)

        punch_out_embed = discord.Embed(
            title=f'{user_name}\'s Punch Stats',
            description=f'Punchs:\n{punch_entries_str}\n\nCumulatif: {int(cumulative_hours)}h {int(cumulative_minutes)}m'
        )

        await ctx.send(embed=punch_out_embed)
    else:
        await ctx.send(f'{ctx.author.name} n\'est pas encore Puncher.')


@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id != bot.user.id and payload.emoji.name == '🥊':
        user_id = str(payload.user_id)
        user_name = str(payload.member.name)

        await punch_in(user_id,user_name)


@bot.event
async def on_raw_reaction_remove(payload):
    if payload.user_id != bot.user.id and payload.emoji.name == '🥊':
        user_id = str(payload.user_id)
        user = await bot.fetch_user(user_id)
        user_name = user.name if user else "Unknown User"

        await punch_out(user_id,user_name)


async def punch_in(user_id, user_name):
    current_time = datetime.datetime.now()
    punch_ins[user_id] = {'punch_in_time': current_time}

    # Save punch_in data to user_data
    if user_id not in user_data:
        user_data[user_id] = {"name": user_name, "id": user_id, "punch": {}, "cumulative": 0}

    user_data[user_id]["punch_in_time"] = current_time  # Assurez-vous que punch_in_time est de type datetime

    punch_num = len(user_data[user_id]["punch"]) + 1
    user_data[user_id]["punch"][punch_num] = [str(current_time)]
    user_data[user_id]["cumulative"] += 1

    # Save user_data to JSON file

    with open(user_data_file, "w") as f:
        json.dump(user_data, f, default=datetime_converter, indent=2)

    punch_category = discord.utils.get(guild.categories, name='punch')
    punch_in_channel = discord.utils.get(punch_category.text_channels, name='punch-in')

    punch_in_embed = discord.Embed(
        title=f'{user_name} a punché in!',
        description=f'Heure d\'entrée: {current_time}'
    )

    await punch_in_channel.send(embed=punch_in_embed)


async def punch_out(user_id, user_name):
    if user_id in punch_ins:
        current_time = datetime.datetime.now()
        punch_in_time = punch_ins[user_id]['punch_in_time']
        time_difference = current_time - punch_in_time

        hours, remainder = divmod(time_difference.seconds, 3600)
        minutes = remainder // 60

        # Save punch_out data to user_data
        if user_id not in user_data:
            user_data[user_id] = {"name": user_name, "id": user_id, "punch": {}, "cumulative": 0}

        punch_num = len(user_data[user_id]["punch"]) + 1
        user_data[user_id]["punch"][punch_num] = [str(current_time), f"{hours}h {minutes}m"]

        # Update cumulative time
        user_data[user_id]["cumulative"] += time_difference.total_seconds()

        # Save user_data to JSON file
      
        with open(user_data_file, "w") as f:
            json.dump(user_data, f, default=datetime_converter, indent=2)

        punch_category = discord.utils.get(guild.categories, name='punch')
        punch_out_channel = discord.utils.get(punch_category.text_channels, name='punch-out')

        punch_out_embed = discord.Embed(
            title='Heures enregistrées',
            description=f'Utilisateur: {user_name}\nPunch In: {punch_in_time}\nPunch Out: {current_time}\nTemps de punch: {hours}:{minutes}'
        )

        await punch_out_channel.send(embed=punch_out_embed)

        # Clear punch_in data
        del punch_ins[user_id]


@bot.command(name='punchout')
async def manual_punch_out(ctx):
    user_id = str(ctx.author.id)
    await punch_out(user_id)


@bot.event
async def on_message(message):
    if message.content == '!punch in':
        user_id = str(message.author.id)
        await punch_in(user_id)

    if message.content == '!punch out':
        user_id = str(message.author.id)
        await punch_out(user_id)

    await bot.process_commands(message)


# Ajoute cette fonction au début de ton script
async def check_pending_punch_ins():
    for user_id, punch_data in punch_ins.items():
        user_name = punch_data.get('user_name', 'Unknown User')
        await punch_out(user_id, user_name)

# Modifie la fonction on_ready pour appeler la fonction check_pending_punch_ins
@bot.event
async def on_ready():
    global guild
    guild = bot.guilds[0]
    punch_category = discord.utils.get(guild.categories, name='punch')

    if punch_category is None:
        punch_category = await guild.create_category('punch')

    punch_in_channel = discord.utils.get(punch_category.text_channels, name='punch-in')
    if punch_in_channel is None:
        punch_in_channel = await punch_category.create_text_channel('punch-in')

    punch_out_channel = discord.utils.get(punch_category.text_channels, name='punch-out')
    if punch_out_channel is None:
        punch_out_channel = await punch_category.create_text_channel('punch-out')

    punch_here_channel = discord.utils.get(punch_category.text_channels, name='punch')
    if punch_here_channel is None:
        punch_here_channel = await punch_category.create_text_channel('punch')

    stats_channel = discord.utils.get(punch_category.text_channels, name='stats')
    if stats_channel is None:
        stats_channel = await punch_category.create_text_channel('stats')

    # Appelle la fonction check_pending_punch_ins au démarrage
    await check_pending_punch_ins()

    print('Bot is ready')


bot.run(TOKKENTEST)

#506
